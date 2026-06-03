---
phase: 01-undo-redo
reviewed: 2026-06-03T01:57:42Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - pagefolio/app.py
  - pagefolio/constants.py
  - pagefolio/file_ops.py
  - pagefolio/page_ops.py
  - tests/test_pdf_ops.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# フェーズ 01: コードレビュー報告書

**レビュー日時:** 2026-06-03T01:57:42Z
**深度:** standard
**レビュー対象ファイル数:** 5
**ステータス:** issues_found

## サマリー

Undo/Redo を「doc.tobytes() 全体シリアライズ」から「op 別の対称デルタ方式」へ作り替えたフェーズ。両スタックの `deque(maxlen)` 化は適切で、`_save_undo` / `_apply_inverse` / `_restore_state` の三段構成も概ね一貫している。しかし重点確認を依頼された逆デルタ構築のうち、**`move` op の「末尾へのドラッグ移動」(`dest >= n`) の undo がページ順序を破壊する**重大バグを発見した。さらに **`merge_resize` の `select_pages` 共有参照** と **`_do_insert` の例外時 undo スタック不整合** が実害を伴う。テストは往復を網羅しているように見えるが、`move` の末尾ドロップ経路（`move_page(src, -1)`）を一度も通しておらず、最も壊れやすい経路がテストの盲点になっている。

レビューはアドバーサリアル姿勢で実施し、各 op の往復対称性をコード上で追跡したうえで PyMuPDF の実挙動を実機検証して確認した。

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `move` op の末尾ドロップ undo がページ順序を破壊する

**File:** `pagefolio/file_ops.py:128-143` および `:252-267`、`pagefolio/dnd.py:118-126`

**Issue:**
`_dnd_drop` は末尾へのドロップ時に `move_page(src, -1)`（末尾へ移動）を呼び、`actual_dest = n - 1` を保存する。しかし `_restore_state(move)` / `_apply_inverse(move)` の順列再構成は `move_page(src, actual_dest)` を前提にしている。`move_page(src, n-1)` と `move_page(src, -1)` は **異なる結果** になるため、保存した `actual_dest = n-1` から再構成した順列は実際の doc 状態と一致せず、undo（および対称な redo）でページ順序が崩れる。

実機検証（n=3, src=0 を末尾へドラッグ）:

```
実際の doc 順序  move_page(0, -1):  [P1, P2, P0]
再構成された順序 (actual_dest=2): [P1, P0, P2]   ← 不一致
```

`_restore_state` の `move` 分岐は次の順列を計算する:

```python
order = list(range(n))
item = order.pop(src)
if src < actual_dest:
    order.insert(actual_dest - 1, item)   # actual_dest=n-1 → insert(n-2) で末尾にならない
else:
    order.insert(actual_dest, item)
```

`actual_dest = n - 1` のとき `insert(n-2, item)` となり、item が末尾の1つ手前に入る。実際の doc は item が末尾にある。この食い違いから逆順列も誤り、undo 後にページ順が変わる（データ破損相当）。

既存の `test_move_roundtrip`（`tests/test_pdf_ops.py:831`）は `move_page(0, 2)` を直接呼ぶため `[P1,P0,P2]` の経路しか通らず、実アプリが使う `move_page(src, -1)` の経路を一度も検証していない。よってバグがテストをすり抜けている。

**Fix:**
末尾ドロップでも一般経路と同じ `actual_dest` で `move_page` を呼び、保存値と実 doc 状態を必ず一致させる。`dnd.py` 側を修正するのが最小:

```python
# pagefolio/dnd.py _dnd_drop
if dest >= n:
    actual_dest = n - 1
    self.doc.move_page(src, actual_dest)   # -1 ではなく actual_dest を使う
else:
    actual_dest = dest if dest < src else dest - 1
    self.doc.move_page(src, actual_dest)
```

注意: `move_page(src, n-1)` と `move_page(src, -1)` は挙動が異なるため、上記のように `actual_dest`（=n-1）で呼ぶと「末尾の1つ手前」になり末尾移動にならない。意図が「末尾へ移動」なら、保存側を実挙動に合わせて修正する必要がある。すなわち再構成ロジックを `move_page(src, -1)` 相当（`order.append(item)`）に変えるか、`actual_dest` を「末尾移動」を表すセンチネルとして扱い、`_restore_state` 側で `src < actual_dest` 分岐の `insert(actual_dest - 1)` を末尾ケースのみ `order.append(item)` に分けること。いずれにせよ **保存値・再構成・実 doc 操作の三者を一致させ、`move_page(src, -1)` の末尾ドロップを通すテストを追加** すること。

### CR-02: `_do_insert` で例外発生時に undo スタックが壊れた state を残す

**File:** `pagefolio/page_ops.py:332-360`

**Issue:**
`_do_insert` は最初に `self._save_undo("insert", insert_at=insert_at)` を呼び、`state["data"] = [insert_at, 0]`（num=0 のプレースホルダ）を積む。その後 `try` ブロック内で実挿入を行い、成功時のみ `self._undo_stack[-1]["data"][1] = total` で num を書き戻す。

挿入途中（例: 2 つ目のファイルが破損 PDF）で例外が出ると、`except` で `messagebox.showerror` を表示して終了するが、**undo スタックには `num=0` のままの不完全な insert state が残り**、かつ実際には一部のページがすでに挿入済みになっている。この状態で undo すると `_restore_state(insert)` は `for _ in range(0): delete_page(...)` となり **1 ページも削除せず**、挿入済みページが取り残される（データ不整合）。

**Fix:**
例外時は積んだ state を巻き戻す。`except` 節でスタック末尾を取り除くか、`_save_undo` を成功確定後に移動する:

```python
def _do_insert(self, ordered_paths, insert_at):
    self._save_undo("insert", insert_at=insert_at)
    try:
        total = 0
        pos = insert_at
        for path in ordered_paths:
            src = self._open_path_as_pdf(path)
            self.doc.insert_pdf(src, start_at=pos)
            pos += len(src)
            total += len(src)
            src.close()
        self._undo_stack[-1]["data"][1] = total
        ...
    except Exception as e:
        # 積んだ不完全な undo state を破棄（実挿入も部分的なため要整合確認）
        if self._undo_stack and self._undo_stack[-1]["op"] == "insert":
            self._undo_stack.pop()
        messagebox.showerror(self._t("err_title"), str(e))
```

理想的には実挿入も一括ロールバックすべきだが、最低限 undo スタックに `num=0` の壊れた state を残さないこと。

## Warnings

### WR-01: `move`/`insert`/`merge` で `_save_undo` がデータ変更後に呼ばれ、規約「操作前に保存」と矛盾

**File:** `pagefolio/dnd.py:110-126`、`pagefolio/page_ops.py:469-470`

**Issue:**
`_dnd_drop` の `bulk_move` は `self.doc.select(new_order)`（line 110）を実行した **後** に `_save_undo("bulk_move", ...)` を呼ぶ。`move` 経路も `move_page` 実行後に `_save_undo` を呼ぶ。`bulk_move`/`move` は引数のみから逆操作を再構成できるため現状は動作するが、他の op（rotate/crop/delete は操作前に保存）と保存タイミングが不統一で、将来「現在の doc 状態を参照する保存」を足したときにバグを生む温床になる。`_do_merge` は逆に `_save_undo("merge")` を挿入前に呼んでおり old_count を正しく取れているが、この不統一は意図が読み取りにくい。

**Fix:** すべての op で「変更前に `_save_undo`」へ統一する。`bulk_move`/`move` は `new_order`/`src,actual_dest` を先に確定してから `_save_undo` → 実操作の順にする。

### WR-02: `merge_resize` の逆デルタが `selected_pages` を更新せず、復元後の選択が不整合

**File:** `pagefolio/file_ops.py:336-337`、`pagefolio/page_ops.py:452`

**Issue:**
`_do_merge_resize` は実行後 `self.selected_pages = {insert_at}` に設定するが、`_save_undo("merge_resize", ...)` は実行 **前** に呼ばれるため、state に保存される `selected_pages` は結合前の複数選択（例 `{0,1}`）。undo すると `_restore_state` 末尾で `self.selected_pages = state["selected_pages"]`（結合前選択）に戻り妥当。しかし redo（`merge_resize_undo` → 再結合）後は `state["selected_pages"]` が「結合前の複数選択」のままで、`_do_merge_resize` 本来の `{insert_at}` にならない。結合ページ1枚しかないのに複数インデックスが選択状態になり、その後の操作（削除等）で範囲外インデックス参照のリスクがある。

**Fix:** `merge_resize` の逆デルタ生成時に、redo 後の選択を `{insert_at}` に正規化する。`_apply_inverse`/`_restore_state` の `merge_resize_undo` 適用後に `selected_pages` を `{d["insert_at"]}` へ上書きする処理を加える。

### WR-03: `_restore_state` の最終行で `selected_pages` を防御コピーせず共有参照を代入

**File:** `pagefolio/file_ops.py:337`

**Issue:**
`self.selected_pages = state["selected_pages"]` は state 内の `set` オブジェクトを **そのまま** `self.selected_pages` に束縛する。以降アプリ側で `self.selected_pages.clear()` 等の破壊的変更を行うと、（pop 済みとはいえ）同一 set を指す redo 側 inverse デルタや、まだスタックに残る他 state の set を意図せず汚染する経路が生まれうる。`_save_undo`/`_apply_inverse` は `set(...)` でコピーしているのに、ここだけ参照渡しで非対称。

**Fix:** `self.selected_pages = set(state["selected_pages"])` とコピーして代入する。`current_page` は int なので問題ない。

### WR-04: 範囲外インデックスへの set_cropbox/アクセスがクランプされず例外フォールバックなし

**File:** `pagefolio/file_ops.py:236-240`, `:332-334`

**Issue:**
`_restore_state(rotate/crop/bulk_crop)` は `state["data"]` に保存された `page_i` を `self.doc[page_i]` で直接参照する。回転/クロップ後に別操作で総ページ数が減ると（通常はスタックがクリアされない混在操作の連続）、保存済み `page_i` が現在の doc 範囲外になり `IndexError` でクラッシュする可能性がある。op 間でページ数を変える操作（delete/insert/merge_resize）が挟まると undo の順序前提が崩れるケースは設計上排除されていない。

**Fix:** 少なくとも `_restore_state` 冒頭で `page_i` の範囲チェックを行い、範囲外なら当該 op をスキップしてログ出力する。または undo は厳密に LIFO で総ページ数の整合が保たれる前提を明文化・検証する。

### WR-05: `insert_redo` 分岐がコメントと実装で乖離（再挿入後に削除しない）

**File:** `pagefolio/file_ops.py:287-292`

**Issue:**
`_restore_state` の `insert_redo` 分岐のコメントは「再挿入後にそのページを削除（insert の再実行相当）」と書いてあるが、実装は `insert_pdf` で **挿入するだけ** で削除していない。コメントが実装と矛盾し、保守者を誤誘導する。実際の redo 連鎖（`insert` → undo=`insert_undo` → redo=`insert_redo`）では「再挿入」が正しい挙動なので動作自体は正だが、コメントが誤り。`insert`/`insert_undo`/`insert_redo` の 3 状態遷移は冗長で、`insert_undo`(=bytes 削除復元) と `insert_redo`(=bytes 再挿入) の 2 状態で十分なはず。

**Fix:** 誤コメントを実装に合わせて修正し、可能なら状態機械を簡素化する。最低限コメント修正は必須。

## Info

### IN-01: insert 系の往復で 3 op (`insert`/`insert_undo`/`insert_redo`) と冗長な状態遷移

**File:** `pagefolio/file_ops.py:171-197`, `:277-292`

**Issue:** `insert` の逆は `insert_undo`(bytes キャプチャ削除)、その逆は `insert_redo`(bytes 再挿入)、さらにその逆は再び `insert_undo`。`insert_redo` と `insert_undo` だけで完結する 2 状態に畳めるはずで、`insert` 初回 op を含め 3 種に分かれているのは可読性を下げている。

**Fix:** `insert`/`merge` の初回 op を最初の undo 時点で `*_undo`/`*_redo` の 2 状態系へ正規化し、分岐数を削減する。

### IN-02: `_save_undo` の巨大 if/elif 連鎖（13 分岐）はディスパッチ表化が望ましい

**File:** `pagefolio/file_ops.py:23-63`, `:83-225`

**Issue:** `_save_undo` / `_apply_inverse` / `_restore_state` がいずれも op 名による長大な if/elif 連鎖で、3 箇所に op ロジックが分散している。op を追加するたび 3 関数を同期修正する必要があり、片方の更新漏れがバグ源になる（CR-01/WR-05 もこの分散が遠因）。

**Fix:** op ごとに `capture`/`invert`/`apply` の 3 関数を持つハンドラ dict（またはクラス）へ集約し、各 op の往復ロジックを 1 箇所にまとめる。

### IN-03: テストが実アプリの呼び出し経路を再現せず往復ロジックを直接検証している箇所がある

**File:** `tests/test_pdf_ops.py:831-855`（move）, `:885-908`（merge）ほか

**Issue:** `test_move_roundtrip` は `_dnd_drop` を介さず `move_page(0, 2)` を直接呼ぶため、実アプリが末尾ドロップで使う `move_page(src, -1)` 経路を検証できていない（CR-01 の盲点）。同様に多くの op テストが UI ハンドラを経由せず最小ロジックのみ検証しており、保存タイミングや引数変換のバグを取りこぼす。

**Fix:** 少なくとも `move` は末尾ドロップ（`dest >= n`）と中間ドロップの両方を、実際の保存値（`actual_dest`）から `_restore_state` へ渡す形で往復検証する。

---

_Reviewed: 2026-06-03T01:57:42Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
