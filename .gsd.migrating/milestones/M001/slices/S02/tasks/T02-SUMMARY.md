---
id: T02
parent: S02
milestone: M001
key_files:
  - pagefolio/viewer.py
key_decisions:
  - worker() 内で fitz.Document 専用インスタンスを finally で必ず close() し、PyMuPDF の並行アクセス非対応に対処した
  - filepath=None（未保存結合 doc）の場合は doc.tobytes() をメインスレッドで実行してから Thread を起動し、スレッド内での self.doc アクセスを完全に排除した
  - _apply() で self.preview_canvas.delete('all') を再度呼び出してプレースホルダーを消去してから画像を描画する設計にした
duration: 
verification_result: passed
completed_at: 2026-05-04T04:16:58.174Z
blocker_discovered: false
---

# T02: viewer.py の _show_preview() をバックグラウンドスレッドパターンに改修し、get_pixmap() をメインスレッドから分離

**viewer.py の _show_preview() をバックグラウンドスレッドパターンに改修し、get_pixmap() をメインスレッドから分離**

## What Happened

viewer.py の _show_preview() を daemon スレッドパターンに全面書き換えした。\n\n主な変更点:\n1. `import threading` / `import logging` / `logger = logging.getLogger(__name__)` を追加\n2. `_show_preview()` の doc あり分岐を以下の流れに再構成:\n   - `_preview_gen` インクリメントして `gen` をローカル変数にコピー\n   - `page_idx`, `zoom`, `filepath` をローカル変数にコピー（スレッド境界を越えない）\n   - `filepath` が None の場合のみ `doc_bytes = self.doc.tobytes()` をメインスレッドで実行\n   - ローディングプレースホルダー（\"...\"）を即時描画\n   - `worker()` 関数: 専用 `fitz.open()` インスタンスを `try/finally` で開閉、`page.get_pixmap()` 実行後 `bytes(pix.samples)` のみスレッド境界を越えて返す。例外は `logger.debug` に出力\n   - `_apply(samples, w, h)` 関数: `root.after(0, ...)` でメインスレッドにコールバック。`_preview_gen != gen` の stale チェックで古い結果を破棄。`ImageTk.PhotoImage` をメインスレッドで生成し `preview_img_ref` に保持（GC防止）。既存の shadow rect・border rect・create_image・scrollregion 設定を再現\n   - `threading.Thread(target=worker, daemon=True).start()` でスレッド起動\n\nruff check/format パス。pytest 108件全通過。

## Verification

grep -c 'threading|_preview_gen|daemon=True' pagefolio/viewer.py → 5（threading import, threading.Thread×1, _preview_gen×2, daemon=True×1）\npytest → 108 passed in 1.46s

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'threading\|_preview_gen\|daemon=True' pagefolio/viewer.py` | 0 | ✅ pass — 5 matches | 150ms |
| 2 | `ruff check . && ruff format .` | 0 | ✅ pass — All checks passed, 1 file reformatted | 2000ms |
| 3 | `pytest --tb=short -q` | 0 | ✅ pass — 108 passed in 1.46s | 1460ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `pagefolio/viewer.py`
