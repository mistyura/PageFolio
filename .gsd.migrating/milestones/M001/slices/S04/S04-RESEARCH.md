# S04: 複数ページ操作と保守 — Research

**Date:** 2026-05-04

## Summary

S04 は「複数選択ページの D&D 一括移動」と「複数選択ページの一括トリミング」の 2 機能を実装するスライス。いずれも `selected_pages`（set）とそれを使う既存 API (`_get_targets()`, `selected_pages.clear()`) を組み合わせれば素直に実装できる。難度は中程度で、S03 で確立した Undo 差分パターンの自然な拡張として実装できる。

**一括移動** は `doc.select(new_order)` を使うのが最も安全。`move_page()` を繰り返すと index ずれが発生するが、`select()` に新ページ順の int リストを渡すだけでドキュメントを一括再順序できる。Undo は `new_order` の逆順列を保存して `doc.select(inverse)` で復元する。

**一括トリミング** は既存の `_crop_page()` をほぼそのまま流用し、ループを追加するだけ。ただし選択ページが `current_page` と異なるサイズを持つ可能性があるため、cropbox 座標を current_page の mediabox に対する相対値（0-1）に正規化してから各ページの mediabox に掛け直すことが必要。

## Recommendation

- **一括移動**: `doc.select(new_order)` で実装。`new_order` = selected pages を dest に挿入した全ページ順序リスト。Undo op = `"bulk_move"`, data = `new_order`; restore = 逆順列で再 select。
- **一括トリミング**: `_crop_page()` を拡張して `_get_targets()` 由来の全ページに適用。相対座標正規化あり。Undo op = `"bulk_crop"`, data = `[(page_i, (x0,y0,x1,y1)), ...]`（旧 cropbox リスト）。
- 両 op は `_save_undo()` / `_restore_state()` に新 elif 分岐を追加するだけ（S03 の diff ディスパッチャパターンに完全準拠）。

## Implementation Landscape

### Key Files

- `pagefolio/dnd.py` — `_dnd_drop()` を拡張して `src in selected_pages` のとき一括移動ルートに分岐。`_dnd_start_ghost()` に N ページ表示用分岐を追加（`selected_pages` が複数のとき）。
- `pagefolio/file_ops.py` — `_save_undo()` に `elif op == "bulk_move"` / `"bulk_crop"` 追加。`_restore_state()` に逆順列 select と一括 cropbox 復元を追加。
- `pagefolio/page_ops.py` — `_crop_page()` を `_get_targets()` ループで複数対応に拡張。相対座標変換ロジックを追加。
- `pagefolio/constants.py` — `LANG["ja"]` / `LANG["en"]` に `status_bulk_moved`, `status_bulk_cropped` を追加。`"sec_crop"` ラベル更新は任意。
- `tests/test_pdf_ops.py` — `bulk_move` の select 逆順列ラウンドトリップ・`bulk_crop` のマルチページ cropbox ラウンドトリップ各 1 テスト追加。

### Concrete Algorithms

#### 一括移動: new_order 構築

```python
n = len(self.doc)
sorted_sel = sorted(self.selected_pages)
non_selected = [p for p in range(n) if p not in self.selected_pages]
# dest はサムネイルの視覚的挿入位置（0 .. n）
sel_before_dest = sum(1 for p in self.selected_pages if p < dest)
adj_dest = dest - sel_before_dest          # non_selected リスト上の挿入位置
new_order = non_selected[:adj_dest] + sorted_sel + non_selected[adj_dest:]
self.doc.select(new_order)
self._save_undo("bulk_move", new_order=new_order)
```

#### 一括移動: Undo (restore)

```python
elif op == "bulk_move":
    new_order = state["data"]
    inverse = [0] * len(new_order)
    for i, v in enumerate(new_order):
        inverse[v] = i
    self.doc.select(inverse)
```

#### 一括トリミング: 相対座標変換

```python
# _crop_page() 内で座標変換後、以下に変更
targets = self._get_targets()
cur_mb = self.doc[self.current_page].mediabox
# PDF 座標系での crop rect（current_page の mediabox 起点）
x0_pdf = (sx - img_offset) / scale
y0_pdf = (sy - img_offset) / scale
x1_pdf = (ex - img_offset) / scale
y1_pdf = (ey - img_offset) / scale
# current_page の mediabox 幅/高さに対する相対比率
rel = (x0_pdf / cur_mb.width, y0_pdf / cur_mb.height,
       x1_pdf / cur_mb.width, y1_pdf / cur_mb.height)

crop_data = []
for i in targets:
    page = self.doc[i]
    mb = page.mediabox
    crop_data.append((i, (mb.x0 + cb.x0, ...)))   # 旧 cropbox

self._save_undo("bulk_crop", crop_data=crop_data)

for i in targets:
    page = self.doc[i]
    mb = page.mediabox
    new_rect = fitz.Rect(
        mb.x0 + rel[0] * mb.width,  mb.y0 + rel[1] * mb.height,
        mb.x0 + rel[2] * mb.width,  mb.y0 + rel[3] * mb.height,
    )
    # clamp + set_cropbox（既存ロジック流用）
```

### Build Order

1. **T01 `file_ops.py`**: `_save_undo()` + `_restore_state()` に `bulk_move` / `bulk_crop` 追加 — 他タスクのブロッカー。
2. **T02 `dnd.py`**: `_dnd_drop()` 一括移動分岐 + ゴースト N ページ表示。
3. **T03 `page_ops.py`**: `_crop_page()` 一括トリミング拡張。
4. **T04 `constants.py`**: LANG キー追加。
5. **T05 `tests/test_pdf_ops.py`**: `TestBulkMoveLogic` / `TestBulkCropLogic` テスト追加。
6. **T06**: `ruff check . && ruff format .` + `pytest` 全件確認。

### Verification Approach

```
pytest tests/test_pdf_ops.py -v --tb=short   # 新テスト含む全件 PASSED
ruff check . && ruff format --check .        # リントクリーン
```

手動確認（GUI）:
- Ctrl+クリックでページ 1・3 を複数選択 → ページ 1 のサムネイルをドラッグ → ページ 5 の位置にドロップ → 両ページが移動
- Ctrl+Z で元の順序に戻る
- 複数選択状態でトリミング範囲指定 → 「トリミング」クリック → 選択全ページに同一比率のトリミング適用
- Ctrl+Z でトリミング前の cropbox に戻る

## Common Pitfalls

- **`doc.select()` は空リスト不可** — `new_order` が非空であることを assert or 早期 return で保護。
- **`doc.select()` は重複インデックスを許すとページ複製が起きる** — `sorted_sel` と `non_selected` の和集合が permutation であることを保証（selected_pages ⊂ range(n) なら自動的に満たす）。
- **`doc.select()` 後は既存 page オブジェクトが無効** — select 後にページ参照を再取得すること。
- **`current_page` / `selected_pages` の更新** — 一括移動後、`current_page` を `new_order.index(src)` で更新し `selected_pages.clear()` する（単一移動と同様）。
- **`_save_undo("bulk_move")` の呼び出し位置** — S03 と同じく `doc.select()` 実行後に呼ぶ（`new_order` は事前計算済みなので問題なし）。
- **単ページ D&D 時に `selected_pages` が空でない場合** — ドラッグ元 (`src`) が `selected_pages` に含まれないときは一括移動しない（既存の単ページ動作）。`selected_pages.clear()` も行わない（選択状態維持）。
- **一括トリミング確認ダイアログ** — 複数ページ選択時は適用前に `messagebox.askyesno` で確認を取ることを推奨（誤操作防止）。

## Open Risks

- **`doc.select()` を使った bulk_move では S03 の差分方式より Undo データが軽い**（new_order は整数リストのみ）が、fitz の内部処理として select はページ全体のコピーを行う可能性がある。ページ数が非常に多い場合（1000 ページ超）はパフォーマンス計測推奨。
- **異なる mediabox サイズのページ混在** — 相対座標変換で一般的なケースには対応できるが、極端に縦横比が違うページへの適用はトリミング後のサイズが意図と異なる可能性。ユーザーへの警告は不要だが注意点として記録。

## Sources

- S03-SUMMARY.md の `key_decisions` + `patterns_established` — Undo 差分パターン、fitz.Rect タプル保存、_save_undo の呼び出しタイミング。
- PyMuPDF ドキュメント（既知）: `Document.select(liste)` はページインデックスのリストで新ページ順を設定し、リスト外のページは削除される。順列の場合は並べ替えのみ。
