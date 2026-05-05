---
id: S03
parent: M001
milestone: M001
provides:
  - ["Undo スタック差分方式（op キー付き辞書）", "_restore_state() の新旧フォーマット両対応ディスパッチャ", "差分フォーマット検証 pytest テスト（TestUndoRedoLogic 3 件）"]
requires:
  []
affects:
  - ["S04"]
key_files:
  - ["pagefolio/file_ops.py", "pagefolio/page_ops.py", "pagefolio/dnd.py", "tests/test_pdf_ops.py"]
key_decisions:
  - ["_save_undo(op, **kwargs) 差分形式シグネチャ: op 別に最小データのみ保存", "_restore_state() が pdf_bytes キーの有無でフォーマット自動判別するディスパッチャ方式を採用", "Redo スタックは後方互換のため全体バイト方式を維持", "fitz.Rect は Python タプルとして保存（C 側オブジェクトの寿命管理のため）", "delete op は昇順ソート後に単ページ fitz.open() + insert_pdf + tobytes() + close() で抽出", "insert op は [insert_at, 0] のミュータブルリストで保存し後払い書き込みを可能にする", "_dnd_drop() の _save_undo() は doc.move_page() 実行後かつ actual_dest 確定後に呼ぶ", "_rotate_selected() では targets 取得を _save_undo() より前に行い回転前の値を保存する"]
patterns_established:
  - ["Undo 差分ディスパッチャパターン: _restore_state() が pdf_bytes キーの有無で新旧フォーマットを自動判別", "ミュータブルリストによる後払いフィールド更新: _save_undo() が [insert_at, 0] を保存し呼び出し元がループ後に [1] を更新", "fitz C オブジェクトのタプル変換: fitz.Rect はスタック保存前に (x0,y0,x1,y1) タプルに変換し restore 時に再構築"]
observability_surfaces:
  - none
drill_down_paths:
  []
duration: ""
verification_result: passed
completed_at: 2026-05-04T04:51:41.550Z
blocker_discovered: false
---

# S03: Undo 差分化

**Undo スタックを操作タイプ別差分方式に切り替え、大規模 PDF でのメモリ使用量を削減しつつ Redo との後方互換を維持**

## What Happened

## S03: Undo 差分化 — 実施内容

S03 では Undo スタックを「全体バイトコピー方式」から「操作タイプ別差分方式」に切り替えた。全 6 タスクを順次完了し、ruff リント・pytest 109 件 PASSED でスライスを完了した。

### T01: _save_undo() シグネチャ変更（file_ops.py）

`_save_undo(self)` を `_save_undo(self, op, **kwargs)` に書き換えた。共通ベースとして `{"op": op, "current_page": ..., "selected_pages": ...}` を構築し、op に応じて `state["data"]` を設定する：

- **rotate**: 対象ページの回転前 rotation 値リスト
- **crop**: fitz.Rect をタプル `(x0, y0, x1, y1)` に変換（C 側オブジェクトの寿命管理を回避）
- **delete**: 昇順ソート後に各ページを `fitz.open() + insert_pdf() + tobytes() + close()` でバイト列抽出
- **move**: `(src, actual_dest)` ペア
- **duplicate**: `pno`
- **insert**: `[insert_at, 0]` のミュータブルリスト（呼び出し元が後払いで num_inserted を書き込む）
- **merge**: `len(self.doc)`（現在のページ数）

スタック上限チェックと `_redo_stack.clear()` は既存ロジックを維持した。

### T02: _restore_state() ディスパッチャ化（file_ops.py）

`_restore_state()` を `"pdf_bytes"` キーの有無で自動判別するディスパッチャに書き換えた。

- `"pdf_bytes"` キーあり → 既存ロジック（Redo スタック由来の全体バイト方式）
- `"op"` キーあり → op 別の逆変換を適用：
  - rotate: `set_rotation(old_rot)`
  - crop: タプルから `fitz.Rect` を再構築して `set_cropbox()`
  - delete: 昇順の `(page_i, page_bytes)` を順に `insert_pdf(start_at=page_i)` で再挿入
  - move: `doc.move_page(actual_dest, src)` で元位置に戻す
  - duplicate: `doc.delete_page(pno + 1)` で複製ページを除去
  - insert: `num` 回 `delete_page(insert_at)` で挿入済みページを除去
  - merge: ページ数が `old_count` を超える間 `delete_page(old_count)` で結合分を除去

共通後処理（`current_page` クランプ、`selected_pages` 復元、キャッシュ無効化、世代カウンタ更新、`_refresh_all()`）は両分岐の外に配置した。Redo スタックへのプッシュロジックは変更せず全体バイト形式を維持した。

### T03: page_ops.py の 6 箇所を新シグネチャに更新

1. `_rotate_selected(deg)` — `targets` 取得を `_save_undo()` の前に移動し、回転前の rotation 値を正しく保存
2. `_delete_selected()` — `self._save_undo("delete", targets=targets)` に変更
3. `_duplicate_page()` — `self._save_undo("duplicate", pno=pno)` に変更
4. `_crop_page()` — `self._save_undo("crop", page_i=self.current_page)` に変更
5. `_do_insert()` — `self._save_undo("insert", insert_at=insert_at)` に変更し、ループ後に `self._undo_stack[-1]["data"][1] = total` で後払い書き込み
6. `_do_merge()` — `self._save_undo("merge")` に変更（ページ数は _save_undo 内で取得）

### T04: dnd.py の _dnd_drop() を actual_dest 確定後に呼び出し変更

`self._save_undo()` の位置を actual_dest 計算ブロックの直後（`doc.move_page()` 実行後）に移動し、新シグネチャ `self._save_undo("move", src=src, actual_dest=actual_dest)` に更新した。

### T05: TestUndoRedoLogic を差分フォーマット検証テストに書き換え

全体バイト方式前提の旧 2 テストを削除し、差分フォーマットを直接検証する 3 テストに置き換えた：

1. `test_rotate_delta_roundtrip` — rotate 差分の保存と `set_rotation()` による復元を検証
2. `test_delete_delta_roundtrip` — delete 差分の保存と `insert_pdf()` による再挿入を検証
3. `test_fallback_pdf_bytes_format` — Redo スタック由来の旧フォーマットが `fitz.open(stream=...)` で復元できることを確認

### T06: 全件確認

ruff check / ruff format --check / pytest --tb=short -q を実行し、リントクリーン・109 件 PASSED を確認した。

## Verification

- `ruff check .` → All checks passed（20 ファイル）
- `ruff format --check .` → 20 files already formatted
- `pytest --tb=short -q` → 109 passed in 1.03s（リグレッションなし、スライス要件の 108 件以上を満たす）
- `pytest tests/test_pdf_ops.py::TestUndoRedoLogic -v --tb=short` → 3 テスト全パス（T05 確認）
- 各ファイルの構文チェック（python -c "import ast; ast.parse(...); print('OK')"）→ 全ファイル OK

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

なし（全タスクがプランと完全一致して完了。T05 の docstring を ruff 行長制限に合わせて短縮したが機能・ロジックの変更なし）

## Known Limitations

- Redo スタックは全体バイト方式のまま（メモリ削減は Undo 側のみ）。Redo の差分化は今後の改善候補
- GUI 操作経由での Undo/Redo 統合テストは未実施（UAT フェーズで手動確認推奨）
- 大規模 PDF でのメモリ削減効果は未計測（プロファイラによる定量確認が必要）
- merge op の Undo は複数ファイル結合後の逆操作のため、実際の動作確認は GUI 手動確認が必要

## Follow-ups

- S04（複数ページ操作）では bulk delete/move の Undo 差分形式を新たに定義する必要がある（S03 の差分パターンを踏襲すること）
- Redo スタックの差分化は将来の改善候補として残す

## Files Created/Modified

None.
