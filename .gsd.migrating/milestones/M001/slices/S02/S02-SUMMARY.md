---
id: S02
parent: M001
milestone: M001
provides:
  - ["_preview_gen / _thumb_gen 世代カウンターによるバックグラウンドレンダリング基盤", "_show_preview() のデーモンスレッドパターン実装", "_build_thumbnails() の after_idle() プログレッシブローディング実装", "ドキュメント入替時の gen カウンター統一インクリメント"]
requires:
  []
affects:
  - ["S03"]
key_files:
  - ["pagefolio/app.py", "pagefolio/viewer.py", "pagefolio/file_ops.py"]
key_decisions:
  - ["PyMuPDF は並行アクセス非対応のため、バックグラウンドスレッドでは専用 fitz.open() インスタンスを try/finally で管理", "filepath=None（未保存結合 doc）は tobytes() をメインスレッドで実行してからスレッドを起動し、スレッド内で self.doc に一切アクセスしない", "_apply() で preview_canvas.delete('all') を再度呼び出してプレースホルダーを消去してから画像を描画", "_add_thumb() は後方互換メソッドとして残存し、内部で _add_thumb_placeholder() を呼ぶ形に変更", "gen カウンターは _invalidate_thumb_cache() の直後にインクリメントする順序を統一"]
patterns_established:
  - ["世代カウンターパターン: _preview_gen / _thumb_gen をインクリメントしてローカル gen にコピー → after(0,...) でコールバック → gen != self._preview_gen なら stale 破棄", "after_idle() プログレッシブローディング: 全プレースホルダー即時作成 → after_idle(render_next(0)) → after(0, render_next(i+1)) の連鎖", "ワーカースレッドの例外は logger.debug で記録し無声失敗を防ぐ"]
observability_surfaces:
  - ["logger.debug で _preview_gen / _thumb_gen の世代番号を出力 → どの世代が発火・キャンセルされたかをログ追跡可能", "stale チェック（gen 値不一致）は logger.debug でスキップ理由を記録", "ワーカースレッド内の例外を except Exception → logger.debug に出力（無声失敗を排除）"]
drill_down_paths:
  []
duration: ""
verification_result: passed
completed_at: 2026-05-04T04:30:25.662Z
blocker_discovered: false
---

# S02: バックグラウンドレンダリング

**プレビューとサムネイル生成をメインスレッドから分離し、大規模 PDF でのページ切替・ズーム変更時の UI フリーズを解消**

## What Happened

## S02 実施内容

5タスクを順序通りに実施し、バックグラウンドレンダリング基盤を完成させた。

**T01 — 世代カウンター追加 (app.py)**
`PDFEditorApp.__init__` に `self._preview_gen = 0` と `self._thumb_gen = 0` を追加。`_rebuild_ui()` でも両変数をインクリメントし、UI 再構築前に発行されたレンダリング結果が新ウィジェットに誤適用されないよう対処した。

**T02 — _show_preview() バックグラウンドスレッド化 (viewer.py)**
`_show_preview()` を daemon スレッドパターンに全面書き換え。`page.get_pixmap()` をワーカースレッドで実行し、`after(0, _apply)` でメインスレッドに結果を返す。PyMuPDF の並行アクセス非対応に対処するため、スレッド内では専用 `fitz.open()` インスタンスを `try/finally` で管理。未保存結合 doc（filepath=None）は `doc.tobytes()` をメインスレッドで実行してからスレッドを起動する方式を採用。`_preview_gen` による stale チェックで古い世代の結果を破棄する。

**T03 — _build_thumbnails() プログレッシブローディング化 (viewer.py)**
`_add_thumb_placeholder()` と `_add_thumb()` に分割し、全ページのプレースホルダー Label を即時作成後、`after_idle()` → `after(0,...)` の連鎖で1枚ずつ逐次レンダリング。`_thumb_gen` による stale チェックでドキュメント切替時に古いレンダリングを打ち切る。`_add_thumb()` は後方互換メソッドとして残存。

**T04 — gen カウンターインクリメント位置の統一 (file_ops.py)**
`_open_pdf_path()`・`_do_open_merged()`・`_restore_state()` の3箇所で `_invalidate_thumb_cache()` の直後に `_preview_gen += 1` と `_thumb_gen += 1` を挿入（一部は既存コードの順序誤りを修正）。これによりドキュメント入替時に前 doc のレンダリングが確実に棄却される。

**T05 — 最終検証**
全変更後に `ruff check . && ruff format --check .` と `pytest --tb=short -q` を実行。エラー・警告ゼロ、108件全 PASSED を確認。追加修正は不要だった。

## Verification

- `ruff check . && ruff format --check .` → All checks passed! 20 files already formatted
- `pytest --tb=short -q` → 108 passed in 1.10s（リグレッションなし）
- `grep -c '_preview_gen\|_thumb_gen' pagefolio/app.py` → 4（__init__ 初期化 2 + _rebuild_ui インクリメント 2）
- `grep -c '_preview_gen\|_thumb_gen' pagefolio/file_ops.py` → 6（3箇所 × 2変数）
- `grep -c 'threading\|_preview_gen\|daemon=True' pagefolio/viewer.py` → 5
- `grep -c '_add_thumb_placeholder\|after_idle\|render_next' pagefolio/viewer.py` → 6

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

T04 において、_restore_state() と _do_open_merged() では gen インクリメントが既に追加されていたが _invalidate_thumb_cache() より前に配置されていた。「追加」ではなく「順序修正（移動）」となった。機能的には順序を問わないが、プラン仕様通りに統一した。

## Known Limitations

- 実際の非同期挙動（UI フリーズ解消）はヘッドレス環境では確認不可。GUI 手動確認は UAT フェーズで実施が必要
- サムネイルのレンダリング中にドキュメントを切り替えた場合、プレースホルダーが残留する期間（stale チェック後の早期リターン）がわずかに発生するが、次の _refresh_all() 呼び出しで解消される
- PyMuPDF の GIL 動作に依存しているため、将来的に PyPy や no-GIL Python への移行時は再検討が必要

## Follow-ups

- S03（Undo 差分化）は本スライスの gen カウンターを引き継がず独立して実装可能
- 手動 UAT でページ切替・ズーム変更時の応答性を大規模 PDF で検証すること
- _show_preview() のローディングプレースホルダー（"..."）のデザインを将来的にスピナーやグレーアウト表示に改善できる

## Files Created/Modified

- `pagefolio/app.py` — _preview_gen / _thumb_gen 世代カウンター追加（__init__ + _rebuild_ui）
- `pagefolio/viewer.py` — _show_preview() バックグラウンドスレッド化、_build_thumbnails() プログレッシブローディング化、_add_thumb_placeholder() 追加
- `pagefolio/file_ops.py` — _open_pdf_path / _do_open_merged / _restore_state の3箇所で gen カウンターインクリメント追加・順序統一
