---
id: S01
parent: M002
milestone: M002
provides:
  - OCRDialog の数値パラメータ（scale/timeout/max_tokens/temperature）と model_combo を読み取り専用化
  - LLM 設定適用後に OCR 画面の読み取り専用表示を全プロバイダで即時同期する _sync_param_vars_from_settings ヘルパー
  - サムネイルスライダー専用の全幅独立行 zoom_frame（sel_frame の直後・canvas_frame の前）
  - v1.6.0 へ更新された APP_VERSION / README バッジ / 開発履歴.md エントリ
requires: []
affects: []
key_files: []
key_decisions:
  - 数値同期を独立メソッド _sync_param_vars_from_settings に切り出し Tk 非生成で検証可能にした（Claude's Discretion 採用）
  - model_combo の『モデル取得』ボタンも state=disabled にし編集導線を完全撤去（一元化意図に整合）
patterns_established:
  - 読み取り専用 Spinbox: state=readonly + fg=C[TEXT_SUB]（readonlybackground は Spinbox 非対応のため bg=BG_CARD のまま）
  - ライブ即時反映: _apply_llm_settings の provider if/elif 分岐の外で全プロバイダ共通同期を実行（D-03）
observability_surfaces: []
drill_down_paths: []
duration: 約25分
verification_result: passed
completed_at: 2026-06-18
blocker_discovered: false
---
# S01: Ui Ocr

**# Phase 1 Plan 01: OCR パラメータ一元化（読み取り専用化＋ライブ同期）Summary**

## What Happened

# Phase 1 Plan 01: OCR パラメータ一元化（読み取り専用化＋ライブ同期）Summary

**OCRDialog の数値パラメータ 4 Spinbox と model_combo を読み取り専用化し、LLM 設定の適用結果を全プロバイダ共通箇所で即時同期して OCR パラメータの二重入力（V16-UI-01）を解消した**

## Performance

- **Duration:** 約25分
- **Started:** 2026-06-18
- **Completed:** 2026-06-18
- **Tasks:** 2（いずれも TDD）
- **Files modified:** 3

## Accomplishments
- scale / timeout / max_tokens / temperature の 4 `tk.Spinbox` を `state="readonly"` + `fg=C["TEXT_SUB"]` でグレーアウト読み取り専用化（現在値は読めるが編集不可）
- `model_combo`（ttk.Combobox）と「モデル取得」ボタンを `state="disabled"` にし編集導線を LLMConfigDialog へ一元化
- `_sync_param_vars_from_settings` を新設し、`_apply_llm_settings` の provider 分岐外（全プロバイダ共通箇所）から呼ぶことで claude/gemini/lmstudio/off/tesseract いずれでも読み取り専用表示を `app.settings` 値へ即時同期（D-03）
- 実行時オプション（preset_var / force_ocr_var / api_key_var）は D-06 に従い編集可能のまま維持。`_SENSITIVE_KEYS` 非永続化ガードに非接触

## Task Commits

各タスクをアトミックにコミット（TDD は RED→GREEN で複数コミット）:

1. **Task 1: 数値パラメータと model_combo の読み取り専用化** - `6ac3c94` (feat)
2. **Task 2: 数値同期ヘルパーの回帰テスト（RED）** - `e0f22f9` (test)
3. **Task 2: 全プロバイダ共通のライブ同期実装（GREEN）** - `dbc406e` (feat)

## Files Created/Modified
- `pagefolio/ocr_dialog.py` - 4 Spinbox を readonly+グレーアウト、model_combo/取得ボタンを disabled、`_sync_param_vars_from_settings` 追加と `_apply_llm_settings` 共通箇所からの呼び出し
- `tests/test_provider_ui.py` - `_sync_param_vars_from_settings` を Tk 非生成で検証する 3 テスト（settings 値同期・既定値フォールバック・クラウド provider 時同期）
- `tests/test_ocr.py` - 既存 `TestOcrDialogLlmConfig._make_fake` に param var スタブと同期ヘルパーを追加（共通箇所への新規呼び出しに対応）

## Decisions Made
- 数値同期を独立した小メソッド `_sync_param_vars_from_settings` に切り出し（PLAN の Claude's Discretion を採用）。Tk ウィジェット生成なしで回帰テスト可能になり、`_refresh_provider_dependent_ui` を no-op 化する既存テスト設計とも整合。
- 既定値フォールバックは llm_config 側のクランプ既定値と整合（ocr_scale=1.5 / ocr_timeout=120 / ocr_max_tokens=-1 / ocr_temperature=0.1）。
- 数値同期処理ではログに値を出力しない（T-01-01 情報露出回避）。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 既存 test_ocr.py の fake スタブを新規共通呼び出しに追従**
- **Found during:** Task 2（GREEN 実装後の full pytest）
- **Issue:** `_apply_llm_settings` の共通箇所に `_sync_param_vars_from_settings()` 呼び出しを追加したことで、`TestOcrDialogLlmConfig._make_fake` が生成する SimpleNamespace スタブに当該メソッドと数値 var が無く `AttributeError` で 4 テストが失敗した。
- **Fix:** `_make_fake` に scale_var/timeout_var/max_tokens_var/temperature_var の set 記録スタブと、未束縛 `OCRDialog._sync_param_vars_from_settings` を呼ぶラムダ、ローカル import を追加。既存の url_var/model_var・`_refresh_provider_dependent_ui` no-op と同一パターンに揃えた。
- **Files modified:** tests/test_ocr.py
- **Verification:** `python -m pytest -q` で全 493 件成功、`ruff check .` クリーン。
- **Committed in:** `dbc406e`（Task 2 GREEN コミットに含む）

---

**Total deviations:** 1 auto-fixed（1 blocking / Rule 3）
**Impact on plan:** 自分の変更が惹起したテスト基盤の追従修正であり、本番ロジックの変更なし。スコープ逸脱なし。

## Issues Encountered
- 初回コミット時に RED テストの docstring が E501（90>88）でブロック。docstring を短縮し再フォーマットして解消。

## User Setup Required
None - 外部サービス設定不要（完全ローカルな Tkinter UI リファクタ）。

## Next Phase Readiness
- V16-UI-01 充足。OCR パラメータの真実は `app.settings`（＝LLMConfig 適用結果）へ一本化済み。
- 01-02（サムネイルスライダー配置 / V16-UI-02）は本プランと独立に着手可能。
- 手動 UI 確認（OCR 画面でのグレーアウト表示・LLM 設定変更後の即時反映）は実行者裁量で未実施。回帰ロジックは自動テストで担保済み。

## Self-Check: PASSED
- FOUND: pagefolio/ocr_dialog.py
- FOUND: tests/test_provider_ui.py
- FOUND: tests/test_ocr.py
- FOUND commit: 6ac3c94 / e0f22f9 / dbc406e
- pytest: 493 passed / ruff check .: clean

---
*Phase: 01-ui-ocr*
*Completed: 2026-06-18*

# Phase 01 Plan 02: サムネイルスライダー配置改善・v1.6.0 バージョン同期 Summary

サムネイルサイズ変更スライダーを `sel_frame`（全選択/解除ボタンと同一行・`side="right"`）から、ボタン行直後の新設全幅独立行 `zoom_frame` へ移設し、左ペイン縮小時の幅競合を解消（V16-UI-02・D-07〜D-09）。あわせて `APP_VERSION` を v1.6.0 へ更新し README バッジ・開発履歴.md を同期。挙動（範囲・変数・コールバック）は不変、`viewer.py` / `settings.py` は未変更。

## Tasks Completed

| Task | 名称 | Commit | 主な変更 |
|------|------|--------|----------|
| 1 | サムネイルスライダーを独立全幅行へ移設 | `457f858` | pagefolio/ui_builder.py（zoom_frame 新設・親と pack 引数のみ変更） |
| 2 | APP_VERSION 更新・README バッジ・開発履歴.md 同期 | `dc120c6` | pagefolio/constants.py / README.md / 開発履歴.md |

## Implementation Details

### Task 1: スライダーの独立全幅行への移設

`_build_thumb_panel`（pagefolio/ui_builder.py）内で、`thumb_zoom_var` / `thumb_zoom_scale` の生成とバインドを `sel_frame` 内 `side="right", fill="x", expand=True` から、`sel_frame` の直後・`canvas_frame` の前に新設した `zoom_frame`（`tk.Frame(parent, bg=C["BG_PANEL"])` + `pack(fill="x", padx=6, pady=(0, 4))`）へ移設。スライダーの `pack` を `side="right"` 指定なしの `pack(fill="x", expand=True, padx=2)` にして全幅配置。

不変条件（D-09）はすべて維持: `from_=0.5` / `to=2.5` / `variable=self.thumb_zoom_var` / `orient="horizontal"`、`<ButtonRelease-1>` → `self._on_thumb_zoom_release`、初期値 `self.settings.get("thumb_zoom", 1.0)`。`select_all` / `deselect` ボタン 2 つは `sel_frame` にそのまま残置。

### Task 2: バージョン同期

- `pagefolio/constants.py`: `APP_VERSION` を `"v1.5.0"` → `"v1.6.0"`。
- `README.md`: バージョンバッジを v1.6.0 へ同期（v1.5.0 残存なし）。
- `開発履歴.md`: 索引テーブル行・詳細セクション・「最終更新」行に v1.6.0 Phase 1 エントリを追記。本フェーズ 2 プラン分（V16-UI-01 読み取り専用化 + V16-UI-02 スライダー移設）を 1 エントリにまとめて記載。
- `pyproject.toml` は未編集（CLAUDE.md 禁止事項遵守）。

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `python -c "...ast.parse(ui_builder.py)..."` 構文検証通過。
- `pagefolio/viewer.py` / `pagefolio/settings.py` が本プラン全体（8694c72..HEAD）で git diff 未変更（0 件）。
- `grep 'APP_VERSION = "v1.6.0"' pagefolio/constants.py` 一致、README / 開発履歴.md に v1.6.0 反映、README に v1.5.0 残存なし。
- `pyproject.toml` 未変更（git diff 0 件）。
- `ruff check .` 全通過 / `ruff format --check .` 39 ファイル整形済み。
- `pytest` 493 件全通過。

acceptance_criteria（プラン）はすべて充足:
- zoom_frame が独立 `tk.Frame` として生成され `pack(fill="x", ...)` で全幅配置。
- `thumb_zoom_scale.pack(...)` に `side="right"` を含まない。
- 範囲/変数/orient/バインド不変。
- zoom_frame の pack が canvas_frame の pack より前。
- viewer.py / settings.py 未変更。

## Known Stubs

なし。スタブ・プレースホルダの導入なし（既存ウィジェットの親フレームと pack 引数の変更、および定数/ドキュメントのテキスト更新のみ）。

## Notes for Next Phase

- 手動確認（実行者裁量・未実施）: アプリ起動 → 左ペインを縮小し、スライダーが独立行で全幅・潰れず操作可能、サイズ変更が従来どおり反映されることを目視確認。
- Phase 1（V16-UI-01 + V16-UI-02）は本プランで完了。次は Phase 2（大量ページのページネーション表示・V16-UI-03、高リスク隔離）。

## Self-Check: PASSED

- FOUND: .planning/phases/01-ui-ocr/01-02-SUMMARY.md / pagefolio/ui_builder.py / pagefolio/constants.py / README.md / 開発履歴.md
- FOUND commit: 457f858（Task 1）/ dc120c6（Task 2）
