# S03: Undo 差分化 — Research

**Date:** 2026-05-04

## Summary

現行の Undo/Redo 実装は `_save_undo()` が毎回 `self.doc.tobytes()` で PDF 全体をシリアライズし、スタックに積む「全体コピー方式」。`MAX_UNDO = 20`・操作ごとに 2回 `tobytes()` が発生するケースもあり（`_undo()` / `_redo()` でも現在 doc を反対スタックに push する）、大規模 PDF ではスタック合計が doc_size × 40 以上になりうる。

操作タイプを分析すると、実際にバイト列を必要とする操作は「削除（delete）」のみで、他の操作はメタデータや整数インデックスだけで逆操作を表現できる。差分方式に切り替えることで、典型的なユースケース（回転・トリミング・移動）のスタックエントリはほぼゼロになる。

Redo スタックは「ユーザーが Undo した後にのみ生成される」性質上、数が少なく現在の全体バイト方式を維持してもリスクは低い。ただし `_restore_state()` がフォーマット混在を透過的に処理できるよう、`"pdf_bytes"` キーの有無で旧来形式と差分形式を区別するフォールバック機構を設ける。

## Recommendation

**操作タイプ別差分方式**で Undo スタックを差分化し、Redo スタックは全体バイト方式を維持する。`_save_undo()` のシグネチャに `op` 引数を追加し、`_restore_state()` をディスパッチャに昇格させる。

この方式の根拠：
- 差分方式だけで大規模 PDF での主要操作（回転・トリミング・移動・削除単独ページ）はほぼメモリゼロ
- Redo スタックは過渡的に存在するだけで上限も MAX_UNDO と同じ — 全体バイトのままで許容範囲
- 実装変更は `file_ops.py`・`page_ops.py`・`dnd.py` の限定範囲、後方互換フォールバックで移行リスク最小

## Implementation Landscape

### Key Files

- `pagefolio/file_ops.py` — `_save_undo()` / `_undo()` / `_redo()` / `_restore_state()` の全4メソッドを変更。最多変更ファイル
- `pagefolio/page_ops.py` — `_save_undo()` 呼び出し6箇所に `op` 引数を追加。`_rotate_selected()`・`_delete_selected()`・`_duplicate_page()`・`_crop_page()`・`_do_insert()`・`_do_merge()`
- `pagefolio/dnd.py` — `_save_undo()` 呼び出し1箇所（`_on_drop()`）に `op="move"` + `src`/`dest` 引数を追加
- `pagefolio/app.py` — 変更不要（`MAX_UNDO = 30` への引き上げはオプション）
- `tests/test_pdf_ops.py` — `TestUndoRedoLogic` クラスの2テストを差分方式ロジック検証に更新

### 差分フォーマット定義

```python
# 操作タイプ → undo delta の内容
{
  "rotate":    {"op": "rotate",    "data": [(page_i, old_rotation), ...]},
  "crop":      {"op": "crop",      "data": (page_i, (x0, y0, x1, y1))},
  "delete":    {"op": "delete",    "data": [(page_i, single_page_bytes), ...]},
  "move":      {"op": "move",      "data": (src, actual_dest)},
  "duplicate": {"op": "duplicate", "data": pno},         # undo = delete(pno+1)
  "insert":    {"op": "insert",    "data": (insert_at, num_inserted)},
  "merge":     {"op": "merge",     "data": old_page_count},
}
# 共通: + "current_page": int, "selected_pages": set
```

### 新 `_save_undo()` シグネチャ（`file_ops.py`）

```python
def _save_undo(self, op, **kwargs):
    if not self.doc:
        return
    state = {"op": op,
             "current_page": self.current_page,
             "selected_pages": set(self.selected_pages)}

    if op == "rotate":
        state["data"] = [(i, self.doc[i].rotation) for i in kwargs["targets"]]
    elif op == "crop":
        page_i = kwargs["page_i"]
        cb = self.doc[page_i].cropbox
        state["data"] = (page_i, (cb.x0, cb.y0, cb.x1, cb.y1))
    elif op == "delete":
        targets = sorted(kwargs["targets"])
        data = []
        for i in targets:
            tmp = fitz.open()
            tmp.insert_pdf(self.doc, from_page=i, to_page=i)
            data.append((i, tmp.tobytes()))
            tmp.close()
        state["data"] = data
    elif op == "move":
        state["data"] = (kwargs["src"], kwargs["actual_dest"])
    elif op == "duplicate":
        state["data"] = kwargs["pno"]
    elif op == "insert":
        state["data"] = [kwargs["insert_at"], 0]  # [1] をあとで上書き
    elif op == "merge":
        state["data"] = len(self.doc)

    self._undo_stack.append(state)
    if len(self._undo_stack) > self.MAX_UNDO:
        self._undo_stack.pop(0)
    self._redo_stack.clear()
```

### `_undo()` / `_redo()` の変更点

- `_undo()`: Redo スタックへのプッシュは従来通り `doc.tobytes()` 全体バイト（変更なし）。Undo スタックから pop して新 `_restore_state()` へ委譲
- `_redo()`: Undo スタックへのプッシュは **全体バイト形式**（後方互換型）で push。`_restore_state()` がフォーマット自動検出して処理

### 新 `_restore_state()` ディスパッチャ（`file_ops.py`）

```python
def _restore_state(self, state):
    if "pdf_bytes" in state:
        # 旧来形式（Redo スタック由来）またはフォールバック
        if self.doc:
            self.doc.close()
        self.doc = fitz.open(stream=state["pdf_bytes"], filetype="pdf")
    else:
        op = state["op"]
        if op == "rotate":
            for page_i, old_rot in state["data"]:
                self.doc[page_i].set_rotation(old_rot)
        elif op == "crop":
            page_i, (x0, y0, x1, y1) = state["data"]
            self.doc[page_i].set_cropbox(fitz.Rect(x0, y0, x1, y1))
        elif op == "delete":
            for page_i, page_bytes in state["data"]:  # 昇順 → insert 位置がずれない
                tmp = fitz.open(stream=page_bytes, filetype="pdf")
                self.doc.insert_pdf(tmp, start_at=page_i)
                tmp.close()
        elif op == "move":
            src, actual_dest = state["data"]
            self.doc.move_page(actual_dest, src)
        elif op == "duplicate":
            self.doc.delete_page(state["data"] + 1)
        elif op == "insert":
            insert_at, num = state["data"]
            for _ in range(num):
                self.doc.delete_page(insert_at)
        elif op == "merge":
            old_count = state["data"]
            while len(self.doc) > old_count:
                self.doc.delete_page(old_count)

    self.current_page = min(state["current_page"], max(0, len(self.doc) - 1))
    self.selected_pages = state["selected_pages"]
    self._invalidate_thumb_cache()
    self._preview_gen += 1
    self._thumb_gen += 1
    self._refresh_all()
```

### 呼び出し側の変更（`page_ops.py` / `dnd.py`）

| メソッド | 変更前 | 変更後 |
|---------|--------|--------|
| `_rotate_selected(deg)` | `self._save_undo()` | `self._save_undo("rotate", targets=targets)` ※ targets 取得後・回転前 |
| `_delete_selected()` | `self._save_undo()` | `self._save_undo("delete", targets=targets)` ※ delete 前 |
| `_duplicate_page()` | `self._save_undo()` | `self._save_undo("duplicate", pno=pno)` |
| `_crop_page()` | `self._save_undo()` | `self._save_undo("crop", page_i=self.current_page)` |
| `_do_insert(ordered_paths, insert_at)` | `self._save_undo()` | `self._save_undo("insert", insert_at=insert_at)` → ループ後 `self._undo_stack[-1]["data"][1] = total` |
| `_do_merge(ordered_paths)` | `self._save_undo()` | `self._save_undo("merge")` |
| `dnd._on_drop()` | `self._save_undo()` | `self._save_undo("move", src=src, actual_dest=actual_dest)` ※ actual_dest はロジック計算後に渡す |

**注意**: `_rotate_selected()` では `targets = self._get_targets()` が `_save_undo` より前に呼ばれている必要がある（現在は後）。コード順序の入れ替えが必要。

**注意**: `_do_insert()` の `insert` では `data` をリスト `[insert_at, 0]` にして、挿入ループ完了後に `self._undo_stack[-1]["data"][1] = total` で num_inserted を書き込む。

**注意**: `dnd._on_drop()` での move では `actual_dest` は `self._save_undo` 呼び出し後に計算されている。`_save_undo` 呼び出しを actual_dest 計算後に移動するか、呼び出し前に仮で push して後で更新する。前者（呼び出しを後ろに移動）が安全。

### Build Order

1. **T01: `file_ops.py` の差分 `_save_undo()` 実装** — 新シグネチャ・op別データ抽出・旧フォールバック維持
2. **T02: `file_ops.py` の `_restore_state()` ディスパッチャ実装** — op 別復元ロジック・`pdf_bytes` キー自動検出
3. **T03: `page_ops.py` の呼び出し側を更新** — 6箇所のコール変更 + `_rotate_selected` 順序修正 + `_do_insert` post-update
4. **T04: `dnd.py` の呼び出し側を更新** — `_on_drop()` の呼び出し位置と引数変更
5. **T05: `tests/test_pdf_ops.py` の TestUndoRedoLogic 更新** — 差分ロジック検証テストに書き換え
6. **T06: ruff + pytest で検証** — 108件 PASSED を確認

### Verification Approach

```bash
ruff check . && ruff format --check .  # リントエラーゼロ
pytest --tb=short -q                    # 108件（以上）PASSED

# 機能確認（手動 or pytest で mock 検証）
# 1. 回転 → Undo → Undo後のrotation == 元の値
# 2. 削除 → Undo → ページ数が復元される
# 3. Undo → Redo のサイクルが正常動作
# 4. MAX_UNDO 超過でスタック先頭が破棄される
```

## Common Pitfalls

- **`_rotate_selected()` での targets 取得順序** — 現在 `_save_undo()` → `targets = self._get_targets()` の順だが、差分方式では targets を `_save_undo` に渡す必要があるため `targets = self._get_targets()` → `self._save_undo("rotate", targets=targets)` に順序変更が必要
- **`_do_insert()` の num_inserted 後払い** — `_save_undo("insert", insert_at=X)` 時点では挿入後の件数不明。`state["data"]` をミュータブルリストにして後から書き込む
- **`dnd._on_drop()` の actual_dest 計算タイミング** — 現在 `_save_undo()` の後で actual_dest が決まる。`_save_undo` 呼び出しを actual_dest 計算後に移動すること
- **delete undo 時のインデックスずれ** — 複数ページ削除の undo で再挿入する際、昇順で挿入しないとインデックスがずれる。`state["data"]` は昇順 sort 済みで保存し、同順で insert_pdf する
- **`fitz.Rect` の保存** — `cropbox` は fitz.Rect オブジェクト（C 側寿命管理）。タプル `(x0, y0, x1, y1)` として保存し、復元時に `fitz.Rect(...)` で再構築する
- **`move_page` の逆操作** — `doc.move_page(src, dest)` で src→dest に移動した場合、undo は `doc.move_page(actual_dest, src)` で元の位置に戻す。dnd.py の `actual_dest` 計算ロジックを確認して合わせること

## Open Risks

- **`move_page` 逆操作の正確性** — PyMuPDF の `move_page(from_, to_)` では `to_` が "新しい位置" の意味で、削除後の挿入先か挿入前位置かが仕様上あいまい。実装前に動作テストで確認が必要
- **`_undo_stack[-1]` への post-update** — `_do_insert()` での後払いは、insert → その他処理 → スタック更新の間に例外が発生するとスタックが壊れる。try/except で保護すること

## Sources

- PyMuPDF ドキュメント: `Document.move_page()` の挙動は S02 実装時に確認済み（スレッドセーフ考慮事項と同様に GIL 依存）
- S02 Summary: gen カウンターの順序（`_invalidate_thumb_cache()` 直後にインクリメント）は本スライスでも踏襲すること
