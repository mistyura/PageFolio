---
phase: 03-v1-5-0
verified: 2026-07-05T07:01:18Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: ページ操作磨き込み + v1.5.0 回帰テスト Verification Report

**Phase Goal:** ユーザーは画像（ロゴ）を透かしとして追加でき、黒塗り/モザイク・回転/トリミングが棚卸しで確定した改善により使いやすくなる。v1.5.0 新機能（同じページ操作面）の回帰テストが整備される。
**Verified:** 2026-07-05T07:01:18Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths（ROADMAP Success Criteria）

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ユーザーは画像ファイル（ロゴ等）を透かしとしてページに追加でき、Undo で元に戻せる | ✓ VERIFIED | `pagefolio/page_ops.py:257 _add_watermark_image` / `:300 _watermark_image_rect` が存在・`ui_builder.py:560` でボタン結線・`tests/test_page_polish.py::TestImageWatermark::test_png_watermark_embeds_image_and_undo_removes_it` / `test_jpeg_watermark_embeds_image` が `page.get_images()` の非空→undo後空を実際に検証（symbol存在だけでなく状態遷移をテスト）。破損画像は `test_corrupted_image_shows_error_without_crash` で保護を確認 |
| 2 | 黒塗り/モザイクについて棚卸しで確定した改善項目（D-05〜D-08）が反映され、改善前より操作しやすい | ✓ VERIFIED | `redact_ops.py` で確認: D-05連続適用（`_apply_page_edit` 内に `_redact_mode_off()` 呼び出しなし・`test_redact_mode_persist_after_apply` が適用後 `redact_mode is True` を確認）、D-06粒度スライダー（`ui_builder.py:639-650` のスライダー+`_on_mosaic_block_release` 永続化・`test_apply_mosaic_uses_mosaic_block_setting` で settings 経由の値伝搬を確認）、D-07複数矩形一括+単一undo（`test_multi_rect_apply_single_undo_restores_all` が実際に2矩形のテキストが個別削除されundo で復元されることをget_textで検証、`test_multi_rect_apply_calls_save_undo_once` が `_save_undo` 単一呼び出しを確認）、D-08回転座標統合（`test_redact_derotate_position_matches_rotated_page` が回転90ページで`_derotate_rect`経由の座標一致を数値検証） |
| 3 | 回転/トリミングについて棚卸しで確定した改善項目（D-08〜D-11）が反映される | ✓ VERIFIED | `page_ops.py:354 _derotate_rect`（1定義のみ・grep確認）が `_crop_page` 単一/bulk分岐から呼ばれる。D-09矢印微調整（`_nudge_crop_rect:467`・`ui_builder.py:355-369` キーバインド・`TestCropPolish`で移動/リサイズ数値を検証）。D-10 mm指定トリミング（`compute_margin_crop_rect:94`・`_crop_by_margin:633`・`ui_builder.py:609-610` ボタン結線・`TestMarginCrop`で純関数+適用+undoを検証）。D-11 crop_info mm表示（`_format_crop_info:80`・`TestFormatCropInfo`で数値検証）。回転0/90/180/270の`TestDerotateRect`4テストが全てpass |
| 4 | v1.5.0新機能（白紙挿入・テキスト透かし・ページ番号・TOC保持・D&D指定位置挿入・ショートカット動的読込）の回帰テストがpytestに整備されグリーン | ✓ VERIFIED | `tests/test_v150_regression.py`（新規）に `TestDndDestIndex`（`compute_dnd_dest_index`純関数を境界値含め直接検証）・`TestShortcutMerge`（`merge_shortcuts`/`shift_variant_keysym`検証）・`TestTocPreservation`（削除/結合/範囲分割/全ページ分割の4パターンをFakeAppで`doc.get_toc()`検証）が存在。`tests/test_pdf_ops.py::TestContentOpsUndoFix` の白紙挿入/透かし/ページ番号roundtripテストへ内容検証（サイズ一致・get_text抽出）が追記済み。`pytest` フルスイート実行で **833件全て pass**（本検証者が実機で再実行し確認） |

**Score:** 4/4 truths verified（0 present-behavior-unverified）

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/page_ops.py::_add_watermark_image` | メソッド | ✓ VERIFIED | page_ops.py:257 に存在・`_save_undo("page_edit", ...)` をループ外1回のみ呼ぶ |
| `pagefolio/page_ops.py::_watermark_image_rect` | 静的メソッド | ✓ VERIFIED | page_ops.py:300・中央配置/幅50%/縦長クランプをテストで検証 |
| `pagefolio/lang.py::btn_watermark_image` | ja/en キー | ✓ VERIFIED | 両言語に存在（lang.py:101, 700） |
| `tests/test_page_polish.py` | 新規テストファイル | ✓ VERIFIED | 存在・53テスト・11クラス（TestImageWatermarkRect/TestImageWatermark/TestImageWatermarkLang/TestDerotateRect/TestFormatCropInfo/TestRedactPolish/TestCropPolish/TestMarginCrop 等） |
| `pagefolio/dnd.py::compute_dnd_dest_index` | 純関数 | ✓ VERIFIED | 存在・`_dnd_dest_index`が委譲（薄いラッパー化） |
| `pagefolio/app.py::merge_shortcuts` / `shift_variant_keysym` | 純関数 | ✓ VERIFIED | 存在・`__init__`のショートカットループが委譲 |
| `tests/test_v150_regression.py` | 新規回帰テストファイル | ✓ VERIFIED | 存在・TestDndDestIndex/TestShortcutMerge/TestTocPreservation の3クラス |
| `pagefolio/page_ops.py::_derotate_rect` | 静的ヘルパー（D-08） | ✓ VERIFIED | 1定義のみ（`grep -c` = 1）・`_crop_page`（単一/bulk）と`_apply_page_edit`（redact_ops.py）の両方から呼ばれる共通ヘルパーとして確立 |
| `pagefolio/page_ops.py::_nudge_crop_rect` / `_crop_by_margin` | メソッド | ✓ VERIFIED | 存在・UIボタン/キーバインド結線済み |
| `pagefolio/constants.py::PT_PER_MM` | 定数 | ✓ VERIFIED | `72/25.4`・page_ops.py がimport して使用 |
| `pagefolio/redact_ops.py::_mosaic_page(block=...)` | 引数化 | ✓ VERIFIED | 既定`MOSAIC_BLOCK`維持・`_apply_mosaic`がsettings値を解決して渡す |
| `pagefolio/redact_ops.py::_clear_redact_rects` / `_on_mosaic_block_release` | メソッド | ✓ VERIFIED | 存在・UIボタン/スライダーから結線 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `_add_watermark_image` | `_save_undo("page_edit")` | 適用ループ外1回呼び出し | ✓ WIRED | grep確認・undo往復テストで実証 |
| ui_builder.py 透かしボタン | `_add_watermark_image` | command結線 | ✓ WIRED | ui_builder.py:560付近 |
| `_dnd_dest_index` | `compute_dnd_dest_index` | 委譲 | ✓ WIRED | 抽出後もフルスイート回帰なし（805件当時グリーン、現833件グリーン） |
| app.py `__init__` ショートカットループ | `merge_shortcuts`/`shift_variant_keysym` | 委譲 | ✓ WIRED | 同上 |
| `_canvas_rect_to_pdf` → `_derotate_rect` → mediabox相対化 | crop / redact 両経路 | 1本道 | ✓ WIRED | `page_ops.py::_crop_page`（単一/bulk）と`redact_ops.py::_apply_page_edit`の両方で同一順序を確認 |
| `_crop_drag_move`/`_nudge_crop_rect` | `_format_crop_info` | mm表示 | ✓ WIRED | `_redraw_crop_overlay`経由で共用 |
| preview_canvas 矢印キー | `_nudge_crop_rect` | キーバインド | ✓ WIRED | ui_builder.py:355-369 |
| mosaic_block_var/scale | `_on_mosaic_block_release` → settings永続化 → `_apply_mosaic`のblock引数 | スライダー→設定→適用 | ✓ WIRED | ui_builder.py:639-650・redact_ops.py:85-92・250-261 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| フルテストスイート実行（検証者が実機再実行） | `python -m pytest -q` | `833 passed in 33.47s` | ✓ PASS |
| Lint | `ruff check .` | `All checks passed!` | ✓ PASS |
| Format | `ruff format --check .` | `56 files already formatted` | ✓ PASS |
| `_derotate_rect` 定義数 | `grep -c 'def _derotate_rect' pagefolio/page_ops.py` | `1` | ✓ PASS |
| `_add_watermark_image` の `_save_undo` 呼び出し回数 | 目視確認（page_ops.py:257-299） | ループ外1回のみ | ✓ PASS |
| `_apply_page_edit` の `_save_undo` 呼び出し回数 | 目視確認（redact_ops.py:94-189） | ループ外1回のみ | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| V171-PAGE-01 | 03-01 | 画像透かし追加（v1.5.0テキストのみ制限解除） | ✓ SATISFIED | `_add_watermark_image`実装・undo往復テスト・破損画像保護テスト全pass。REQUIREMENTS.md Traceability上も Complete |
| V171-PAGE-02 | 03-04 | 黒塗り/モザイクの使い勝手改善（D-05〜D-08） | ✓ SATISFIED | 連続適用・粒度スライダー・複数矩形一括+単一undo・回転座標対応が全てテストで実証 |
| V171-PAGE-03 | 03-03 | 回転/トリミング操作性改善（D-08〜D-11） | ✓ SATISFIED | derotateヘルパー・矢印微調整・mm指定トリミング・crop_info mm表示が全てテストで実証 |
| V171-TEST-01 | 03-02 | v1.5.0新機能6種の回帰テスト整備 | ✓ SATISFIED | `test_v150_regression.py`新規（TOC/D&D/ショートカット）+既存3テストへ内容検証追加。フルスイート833件グリーン |

REQUIREMENTS.md との突合: Phase 3 に割り当てられた4要件（V171-PAGE-01/02/03, V171-TEST-01）すべてが各PLANの`requirements`フィールドで宣言され、SUMMARYのcoverageで裏付けられている。孤立要件（PLANに現れずREQUIREMENTS.mdだけに存在するPhase 3宛要件）なし。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| CLAUDE.md | 283 | 既知の制限節が「v1.7.1 Phase 3・D-08で解消」と記述する一方、`pagefolio/constants.py`の`APP_VERSION`は`"v1.7.0"`のまま、`開発履歴.md`最新エントリもv1.7.0で停止、README.mdバッジもv1.7.0のまま（未更新） | ⚠️ Warning | CLAUDE.md自身の「変更時のチェックリスト」（バージョン番号更新・開発履歴追記）が本フェーズで未実施。ドキュメント内でv1.7.0/v1.7.1表記が混在する内部矛盾（03-REVIEW.mdで既指摘）。**機能的なゴール達成には影響しない**が、次フェーズ開始前の解消を推奨 |
| pagefolio/page_ops.py | `_crop_drag_end`→`_crop_drag_move` | redactモードでドラッグなしクリック（Press→即Release）が0サイズ矩形`(x,y,x,y)`を`_redact_rects`へ暗黙蓄積する（`if self.crop_rect:`が非Noneの退化タプルを真と評価） | ℹ️ Info | 適用時`_page_rect_from_rel`が幅/高さ1pt未満でNoneを返しスキップされるため実害なし（03-REVIEW.mdで既指摘・実質バグではなく将来のUIカウンタ表示時の温床） |
| tests/test_pdf_ops.py, test_page_polish.py, test_v150_regression.py | 各ファイル | `_make_app`/FakeApp定義が3ファイルで重複（意図的コピー流用・03-02-SUMMARY.mdで明記） | ℹ️ Info | 保守コスト増の可能性（03-REVIEW.mdで既指摘）。機能・テスト結果には影響なし |

上記はいずれも既に `03-REVIEW.md`（0 Critical / 3 Warning / 4 Info）で捕捉済みであり、TBD/FIXME/XXX等の未解決debtマーカーは検出されなかった（`grep`で本フェーズ変更ファイルにヒットなし）。

### Human Verification Required

なし。本フェーズの`must_haves`はいずれもロジック側で数値・状態遷移を直接検証するユニットテストが存在し（画像埋め込み有無・undo後のテキスト復元・矩形座標の変換結果・undo呼び出し回数等）、「symbol存在のみ」で済ませている項目はない。

各PLANの`<verify><human-check>`（プレビューでの視覚的な位置・半透明表示・矢印キー操作感）はPLAN.md上でend-of-phase human-verify対象として明記されており、`03-VALIDATION.md`のManual-Only表にも記録済み。これらは「見た目」の確認であり、ロジック自体（座標変換・undo・状態遷移）は既にユニットテストで検証済みのため、goal-backward verificationの必須項目としては未確定要素を残さない。ユーザー自身がアプリを起動して目視確認する運用対象として引き続き認識すること。

### Gaps Summary

なし。ROADMAP.md記載の成功基準4項目はすべて✓VERIFIEDであり、フルテストスイート833件・ruff check/format共にクリーン。REQUIREMENTS.mdのPhase 3宛4要件も全てSATISFIED。孤立要件・未解決debtマーカー・アーティファクトの欠落/stub/未結線は検出されなかった。ドキュメント整合性（CLAUDE.md/開発履歴.md/README.mdのバージョン表記不一致）は機能面のゴール達成を妨げないWarningとして記録した。

---

_Verified: 2026-07-05T07:01:18Z_
_Verifier: Claude (gsd-verifier)_
