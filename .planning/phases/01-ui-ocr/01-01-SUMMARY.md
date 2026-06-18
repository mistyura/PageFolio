---
phase: 01-ui-ocr
plan: 01
subsystem: ui
tags: [tkinter, ocr, ocr_dialog, readonly-widgets, settings-sync]

# Dependency graph
requires: []
provides:
  - OCRDialog の数値パラメータ（scale/timeout/max_tokens/temperature）と model_combo を読み取り専用化
  - LLM 設定適用後に OCR 画面の読み取り専用表示を全プロバイダで即時同期する _sync_param_vars_from_settings ヘルパー
affects: [01-02（スライダー配置）, OCR パラメータ UI を参照する後続フェーズ]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "tk.Spinbox の読み取り専用化（state=readonly + fg=TEXT_SUB）を url_var Entry の既存パターンへ横展開"
    - "provider 分岐外の共通箇所から Tk 変数を settings 値へ同期する小メソッド切り出し（テスト容易化）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py
    - tests/test_provider_ui.py
    - tests/test_ocr.py

key-decisions:
  - "数値同期を独立メソッド _sync_param_vars_from_settings に切り出し Tk 非生成で検証可能にした（Claude's Discretion 採用）"
  - "model_combo の『モデル取得』ボタンも state=disabled にし編集導線を完全撤去（一元化意図に整合）"

patterns-established:
  - "読み取り専用 Spinbox: state=readonly + fg=C[TEXT_SUB]（readonlybackground は Spinbox 非対応のため bg=BG_CARD のまま）"
  - "ライブ即時反映: _apply_llm_settings の provider if/elif 分岐の外で全プロバイダ共通同期を実行（D-03）"

requirements-completed: [V16-UI-01]

# Metrics
duration: 約25分
completed: 2026-06-18
status: complete
---

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
