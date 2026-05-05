---
id: T02
parent: S03
milestone: M001
key_files:
  - pagefolio/file_ops.py
key_decisions:
  - _restore_state() は pdf_bytes キーの有無でフォーマットを自動判別するディスパッチャ方式を採用
  - Redo スタックへのプッシュは引き続き全体バイト形式を維持し後方互換を保つ
  - delete undo の再挿入は state['data'] が昇順ソート済みのためそのまま昇順 insert_pdf
  - insert undo は state['data'][1] に格納されたページ数分だけ delete_page を繰り返す
duration: 
verification_result: passed
completed_at: 2026-05-04T04:43:25.284Z
blocker_discovered: false
---

# T02: file_ops.py の _restore_state() を差分/全体バイト両対応ディスパッチャに書き換え

**file_ops.py の _restore_state() を差分/全体バイト両対応ディスパッチャに書き換え**

## What Happened

T01 で新シグネチャになった `_save_undo()` が生成する差分フォーマット（`"op"` キー付き）と、`_undo()` / `_redo()` が Redo スタックに積む旧フォーマット（`"pdf_bytes"` キー付き）の両方を処理できるよう `_restore_state()` をディスパッチャに書き換えた。

`"pdf_bytes"` キーが存在する場合は既存ロジック（`doc.close()` + `fitz.open(stream=...)` ）を実行する。それ以外は `state["op"]` の値で分岐し、各操作の逆変換を適用する：
- rotate: `set_rotation(old_rot)` で各ページの回転を戻す
- crop: タプルから `fitz.Rect` を再構築して `set_cropbox()` で戻す
- delete: 昇順ソート済みの (page_i, page_bytes) ペアを順に `fitz.open(stream=page_bytes) + insert_pdf(start_at=page_i) + close()` で再挿入
- move: `doc.move_page(actual_dest, src)` で元位置に戻す（PyMuPDF の move_page(from_, to_) 仕様通り）
- duplicate: `doc.delete_page(pno + 1)` で複製ページを除去
- insert: `state["data"] = [insert_at, num]` のリストを unpack し、`num` 回 `delete_page(insert_at)` で挿入済みページを除去
- merge: ページ数が `old_count` を超える間 `delete_page(old_count)` で結合分を除去

共通後処理（`current_page` クランプ、`selected_pages` 復元、キャッシュ無効化、世代カウンタ更新、`_refresh_all()`）は両分岐の外に配置した。`_undo()` / `_redo()` の Redo/Undo スタックへのプッシュロジックは変更せず、全体バイト形式のまま維持した。

## Verification

python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')" → exit 0, 出力 OK。ruff check および ruff format --check もすべてパス。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "import ast; ast.parse(open('pagefolio/file_ops.py', encoding='utf-8').read()); print('OK')"` | 0 | ✅ pass | 200ms |
| 2 | `ruff check pagefolio/file_ops.py && ruff format pagefolio/file_ops.py --check` | 0 | ✅ pass | 500ms |

## Deviations

なし

## Known Issues

None.

## Files Created/Modified

- `pagefolio/file_ops.py`
