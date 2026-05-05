---
id: T04
parent: S02
milestone: M001
key_files:
  - pagefolio/file_ops.py
key_decisions:
  - _restore_state() と _do_open_merged() は gen インクリメントが既に追加済みだったが順序が誤り（_invalidate_thumb_cache より前）だったため移動した
  - _open_pdf_path() のみ完全未追加だったため新規挿入した
duration: 
verification_result: passed
completed_at: 2026-05-04T04:26:07.874Z
blocker_discovered: false
---

# T04: file_ops.py の3箇所（_open_pdf_path / _do_open_merged / _restore_state）で _invalidate_thumb_cache() 直後に _preview_gen と _thumb_gen をインクリメント

**file_ops.py の3箇所（_open_pdf_path / _do_open_merged / _restore_state）で _invalidate_thumb_cache() 直後に _preview_gen と _thumb_gen をインクリメント**

## What Happened

file_ops.py を確認すると、_restore_state() と _do_open_merged() には既に gen インクリメントが追加されていたが、タスクプランの「_invalidate_thumb_cache() の直後」という順序に反して前に置かれていた。_open_pdf_path() は gen インクリメントが完全に未追加の状態だった。\n\n対応：\n1. _restore_state()（line 74–77）: gen インクリメント2行を _invalidate_thumb_cache() の後に移動\n2. _do_open_merged()（line 124–127）: 同様に移動\n3. _open_pdf_path()（line 148–151）: _invalidate_thumb_cache() 直後に _preview_gen += 1 と _thumb_gen += 1 の2行を新規追加\n\nすべての箇所で `_invalidate_thumb_cache() → _preview_gen += 1 → _thumb_gen += 1 → _refresh_all()` の順序を統一。これにより、ドキュメント入替時に前の doc に対して発行されたバックグラウンドレンダリングが stale チェック（gen 値比較）によって確実に棄却される。

## Verification

grep -c '_preview_gen\|_thumb_gen' pagefolio/file_ops.py → 6（3箇所×2変数）。ruff check . && ruff format . → all passed, 20 files unchanged。pytest → 108 passed in 1.21s。

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c '_preview_gen\|_thumb_gen' pagefolio/file_ops.py` | 0 | ✅ pass | 50ms |
| 2 | `ruff check . && ruff format .` | 0 | ✅ pass | 3200ms |
| 3 | `pytest --tb=short -q` | 0 | ✅ pass | 1210ms |

## Deviations

_restore_state() と _do_open_merged() については「追加」ではなく「順序修正（移動）」となった。前タスクの作業で gen インクリメントは挿入済みだったが _invalidate_thumb_cache() の前に置かれていた。機能的には順序を問わないが、タスクプランの仕様通りに修正した。

## Known Issues

none

## Files Created/Modified

- `pagefolio/file_ops.py`
