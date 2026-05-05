# S03: Undo 差分化

**Goal:** Undo スタックを「全体バイトコピー方式」から「操作タイプ別差分方式」に切り替え、大規模 PDF での Undo メモリ使用量を削減する。Redo スタックは後方互換性のため全体バイト方式を維持し、`_restore_state()` が両フォーマットを自動判別して処理する。
**Demo:** 大規模 PDF で複数操作後の Undo が動作し、メモリ使用量が全体コピー方式より削減される

## Must-Haves

- `_save_undo(op, **kwargs)` が rotate/crop/delete/move/duplicate/insert/merge の各操作タイプ別に最小データのみを保存する
- `_restore_state(state)` が差分フォーマット（op キー）と旧フォーマット（pdf_bytes キー）の両方を処理できる
- `page_ops.py` の 6 箇所・`dnd.py` の 1 箇所の `_save_undo()` 呼び出しが新シグネチャに更新されている
- `ruff check . && ruff format --check .` エラーゼロ
- `pytest --tb=short -q` で 108 件以上 PASSED（リグレッションなし）

## Proof Level

- This slice proves: contract — pytest でロジックを直接検証。GUI 手動確認（メモリ削減の体感）は UAT フェーズ。

## Integration Closure

Upstream: S02 で確立した `_invalidate_thumb_cache()` → gen カウンターインクリメント順序を踏襲。`_restore_state()` 内でも同順序を維持する。新たな外部依存なし。S04（複数ページ一括操作）は本スライス完了後に着手可能。

## Verification

- Run the task and slice verification checks for this slice.

## Tasks

- [x] **T01: file_ops.py の _save_undo() を差分形式シグネチャに書き換え** `est:45m`
  現行の `_save_undo(self)` は常に `self.doc.tobytes()` で全体バイトを保存する。これを `_save_undo(self, op, **kwargs)` に書き換え、操作タイプ別に最小データのみを保存するよう変更する。
  - Files: `pagefolio/file_ops.py`
  - Verify: python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"

- [x] **T02: file_ops.py の _restore_state() を差分/全体バイト両対応ディスパッチャに書き換え** `est:45m`
  T01 で新シグネチャになった `_save_undo()` が生成する差分フォーマット（`"op"` キー付き）と、`_undo()` / `_redo()` が Redo スタックに積む旧フォーマット（`"pdf_bytes"` キー付き）の両方を処理できるよう `_restore_state()` をディスパッチャに書き換える。
  - Files: `pagefolio/file_ops.py`
  - Verify: python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"

- [x] **T03: page_ops.py の _save_undo() 呼び出し6箇所を新シグネチャに更新** `est:30m`
  T01/T02 で `_save_undo(op, **kwargs)` に変更されたため、`page_ops.py` 内の既存6箇所の `self._save_undo()` 呼び出しを新シグネチャに更新する。
  - Files: `pagefolio/page_ops.py`
  - Verify: python -c "import ast; ast.parse(open('pagefolio/page_ops.py', encoding='utf-8').read()); print('OK')"

- [x] **T04: dnd.py の _save_undo() 呼び出しを actual_dest 計算後に移動して新シグネチャに更新** `est:20m`
  `dnd.py` の `_dnd_drop()` メソッドにある `self._save_undo()` 呼び出しを新シグネチャ `_save_undo("move", src=src, actual_dest=actual_dest)` に更新する。
  - Files: `pagefolio/dnd.py`
  - Verify: python -c "import ast; ast.parse(open('pagefolio/dnd.py', encoding='utf-8').read()); print('OK')"

- [x] **T05: test_pdf_ops.py の TestUndoRedoLogic を差分ロジック検証テストに書き換え** `est:30m`
  既存の `TestUndoRedoLogic` クラスは「全体バイトコピー方式」を前提としたテストになっている。差分フォーマットの正しさを直接 fitz API で検証するテストに書き換える。
  - Files: `tests/test_pdf_ops.py`
  - Verify: pytest tests/test_pdf_ops.py::TestUndoRedoLogic -v --tb=short

- [x] **T06: ruff + pytest で全件確認（リグレッションなし・108件以上 PASSED）** `est:15m`
  T01〜T05 のすべての変更後、リント・フォーマット・テストの全チェックを実行して S03 の完成を確認する。エラーがあれば修正する。
  - Files: `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/dnd.py`, `tests/test_pdf_ops.py`
  - Verify: ruff check . && ruff format --check . && pytest --tb=short -q

## Files Likely Touched

- pagefolio/file_ops.py
- pagefolio/page_ops.py
- pagefolio/dnd.py
- tests/test_pdf_ops.py
