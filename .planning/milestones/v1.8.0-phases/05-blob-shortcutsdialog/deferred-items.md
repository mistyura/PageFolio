# Deferred Items — Phase 05 (blob-shortcutsdialog)

## [05-03 Task 2] insert→undo→redo→undo で挿入ページが重複するバグ（pagefolio/file_ops.py）

**発見日:** 2026-07-16（05-03-PLAN.md Task 2 の D-14② 回帰テスト設計中に発見）
**状態:** Out of scope（05-03 は `pagefolio/undo_store.py`・`tests/test_undo_stress.py` のみが対象。`file_ops.py` は未改造の宣言どおり）

### 症状

`_save_undo("insert", insert_at=X)` → 実挿入 → `_undo()` → `_redo()` → `_undo()`（2回目）の順で
呼ぶと、2回目の `_undo()` 後にページが復元されるどころか **挿入ページが重複してもう1枚増える**
（3ページ→挿入4ページ→undo3ページ→redo4ページ→undo(2回目)で **5ページ** になる。本来は3ページに
戻るべき）。

再現コード（`_make_stress_app` 相当のフェイクアプリで確認済み）:

```python
app._save_undo("insert", insert_at=1)
app.doc.insert_pdf(src, start_at=1)  # 1ページ挿入
app._undo_stack[-1]["data"][1] = 1
app._undo()   # -> 3ページ（正しい）
app._redo()   # -> 4ページ（正しい）
app._undo()   # -> 5ページ（バグ: 3ページに戻るべき）
```

### 原因（推定）

`pagefolio/file_ops.py` の `_restore_state()` 内 `elif op == "insert_redo":` ブロックが
ページを **再挿入**（`doc.insert_pdf`）している。しかし `op="delete"`/`"delete_redo"` の対称パターン
（forward op の逆＝挿入、その逆＝削除、を交互に繰り返す）に倣うなら、`insert_redo` の restore は
**削除**（`doc.delete_page`）であるべき。現状は `insert`（削除）→`insert_undo`（挿入）→`insert_redo`
（挿入 ← ここが本来は削除であるべき）という非対称な実装になっている。

Blob の release() 呼び出し回数自体は正しく1回ずつ（二重解放は発生しない）ため、
V180-ROBUST-01（Blob リーク検出）の観点では問題なし。純粋にページ内容の往復整合性バグ
（BUG-01 とは別の、"2回目の undo" でのみ顕在化する新規発見）。

### 05-03 での対応

D-14② の回帰テストは、この既知課題を踏まえて計画書が明示的に許可する代替案
「delete+undo+redo+undo」を採用した（`tests/test_undo_stress.py::TestBlobLeakDetection::test_double_release_chain_delete_undo_redo_undo`）。
delete/delete_redo は対称実装のため本バグの影響を受けず、D-14② の目的（Blob の
double-release 非発生の検証）を安全に満たせる。

### 推奨される次のアクション

`pagefolio/file_ops.py._restore_state()` の `elif op == "insert_redo":` ブロックを、
`elif op == "insert":` の削除パターン（`for _ in range(num): self.doc.delete_page(insert_at)`
相当・page_i の降順削除に一般化）へ修正し、`tests/test_pdf_ops.py` に
「insert→undo→redo→undo（4手）」の往復正当性テストを追加することを次フェーズ以降で検討する。
