---
phase: 02-ocr-openai-chatgpt
plan: 03
subsystem: ocr
tags: [openai, chatgpt, catalog, tkinter, llm-config, model-fetch, lang, pytest, ast]

requires:
  - phase: 02-ocr-openai-chatgpt (02-01)
    provides: "catalog.py（ProviderMeta + PROVIDERS 8件）・OpenAIProvider の暫定 list_models・02-CAPABILITY-MATRIX.md"
  - phase: 02-ocr-openai-chatgpt (02-02)
    provides: "ocr_dialog.py/batch_ocr.py の catalog 移行（D-03 段階移行 5/6）と OpenAI の送信先確認・コスト確認・vision未確認注記の安全境界"
provides:
  - "OpenAIProvider.list_models() の本実装（GET /v1/models + filter_selectable_models + order_models_for_display + 0件/失敗時フォールバック）"
  - "sections.py の _base_providers/_base_fallback_providers の catalog 化（D-03 段階移行 6/6・完走）"
  - "LLM設定ダイアログの openai_section_frame（モデル欄・未確認モデル注記・APIキー欄・マスクトグル・環境変数注記・モデル更新ボタン）"
  - "dialog.py の openai 分岐・_on_openai_model_change（is_reasoning_model 単一判定源）・_apply のセッションキー同期"
  - "model_fetch.py の _refresh_openai_models（D-08 観測同一性を回帰固定）"
affects: [02-04-openai-settings-ui]

actuals:
  tokens: 15900
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "filter_selectable_models/order_models_for_display: Tk・ネットワーク非依存の純関数として openai_provider.py に切り出し、list_models() 内でのみ呼び出す"
    - "AST ベースの純度・構造アサーション（ast.parse で self 引数の有無・urllib/tkinter 参照・I/O呼び出しの有無・正規表現/集合リテラルの有無を検査。部分文字列検査は使わない）"
    - "D-08 の『同一経路』を『観測可能な結末の同一性』として実装: _on_error の combobox values と list_models() の0件合流の戻り値が値として完全一致し、_set_lm_status の LANG キーも一致する"

key-files:
  created:
    - .planning/phases/02-ocr-openai-chatgpt/02-03-SUMMARY.md
  modified:
    - pagefolio/ocr_providers/openai_provider.py
    - pagefolio/dialogs/llm_config/sections.py
    - pagefolio/dialogs/llm_config/dialog.py
    - pagefolio/dialogs/llm_config/model_fetch.py
    - pagefolio/lang.py
    - tests/test_ocr_providers.py
    - tests/test_provider_ui.py

key-decisions:
  - "_EXCLUDED_MODEL_MARKERS から単独の 'image' を除外し、画像生成モデルは 'gpt-image' という限定的なマーカーで落とす設計を踏襲（レビュー MEDIUM 02-03-3・将来の vision モデル過剰除外を回避）"
  - "order_models_for_display は VERIFIED_VISION_MODELS の宣言順を先頭に据え、Combobox の先頭・既定選択値が常に画像入力確認済みモデルになるようにした（レビュー HIGH 02-03-1）"
  - "_refresh_openai_models の _on_error フォールバック値は order_models_for_display(OpenAIProvider.RECOMMENDED_MODELS) とし、list_models() が api_key 未設定/0件合流時に返す list(RECOMMENDED_MODELS) と値として完全一致することをテストで固定（D-08 観測同一性・レビュー MEDIUM-11）"
  - "_on_openai_model_change は is_reasoning_model のみを判定源とし、effort_frame は openai では常に非表示（OpenAI 専用の reasoning effort 欄は 02-04 の責務）"

patterns-established:
  - "モデル一覧のフィルタ・並び替えロジックを Provider クラスから独立した純関数として module level に置き、AST 検査で純度を回帰固定するパターン（今後の新規プロバイダのモデル一覧処理にも適用可能）"

requirements-completed: [V190-CAT-01, V190-OAI-01, V190-OAI-02, V190-OAI-03]

coverage:
  - id: D1
    description: "OpenAIProvider.list_models() が GET /v1/models 実取得→除外フィルタ→確認済み優先の並び替え→0件/失敗時の静的フォールバックの全経路を持つ"
    requirement: "V190-OAI-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestOpenAIProviderListModels"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestOpenAIFilterSelectableModels"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestOpenAIOrderModelsForDisplay"
        status: pass
    human_judgment: false
  - id: D2
    description: "filter_selectable_models/order_models_for_display が Tk・ネットワーク非依存の純関数であることを AST 検査で固定"
    requirement: "V190-OAI-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestOpenAIFilterIsPure"
        status: pass
    human_judgment: false
  - id: D3
    description: "sections.py の _base_providers/_base_fallback_providers が catalog.provider_names()/fallback_candidate_names() 由来になり、D-03 の6参照面移行が完走"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestLLMConfigProviderValues::test_provider_combo_values_include_openai_via_catalog"
        status: pass
    human_judgment: false
  - id: D4
    description: "openai_section_frame が新設され、モデル欄・未確認モデル注記・APIキー欄・マスクトグル・環境変数注記・モデル更新ボタンを持つ"
    requirement: "V190-OAI-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestLLMConfigProviderValues::test_openai_section_frame_exists_in_source"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOnProviderChangeOpenai"
        status: pass
    human_judgment: false
  - id: D5
    description: "OpenAI 選択時のプロバイダ往復（openai→claude→gemini→openai）で各フレームの表示状態が正しく復元される"
    requirement: "V190-OAI-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestProviderRoundTripFrameState"
        status: pass
    human_judgment: false
  - id: D6
    description: "推論系モデルで temperature_frame が隠れ非推論系で表示される。判定は is_reasoning_model 単一判定源のみ"
    requirement: "V190-OAI-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOnOpenaiModelChange"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOnOpenaiModelChangeStructure"
        status: pass
    human_judgment: false
  - id: D7
    description: "openai_api_key_var の値がセッションのみに保持され、settings/llm_settings へ流入しない"
    requirement: "V190-OAI-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiSessionKeySlot"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApiKeyNotInSettings::test_openai_key_not_in_llm_settings"
        status: pass
    human_judgment: false
  - id: D8
    description: "モデル一覧取得失敗時と0件合流時が同一の combobox values・LANG ステータスキーへ合流する（D-08 の観測可能な結末の同一性）"
    requirement: "V190-OAI-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestRefreshOpenaiModels::test_on_error_matches_zero_result_fallback_of_list_models"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestRefreshOpenaiModels::test_on_success_and_on_error_never_touch_openai_model_var"
        status: pass
    human_judgment: false

duration: 19min
completed: 2026-08-11
status: complete
---

# Phase 2 Plan 3: OpenAI モデル一覧取得・LLM設定UI統合 Summary

**OpenAIProvider.list_models() を実API取得+ヒューリスティックフィルタ+確認済み優先並び替えの本実装にし、LLM設定ダイアログへ openai を選択可能なプロバイダとして完全統合した（catalog移行6/6完走）**

## Performance

- **Duration:** 19min（git commit ログ基準・4d56881 → 57c0c45）
- **Started:** 2026-08-11T12:33:42+09:00
- **Completed:** 2026-08-11T12:52:12+09:00
- **Tasks:** 3 / 3
- **Files modified:** 7（openai_provider.py・sections.py・dialog.py・model_fetch.py・lang.py・test_ocr_providers.py・test_provider_ui.py）

## Accomplishments

- `OpenAIProvider.list_models()` を `GET /v1/models` 実取得 → `filter_selectable_models`（D-07・純関数）→ `order_models_for_display`（レビュー HIGH 02-03-1・確認済みモデル優先）→ 0件/失敗時は `RECOMMENDED_MODELS` へ合流（D-08）、の全経路を持つ本実装へ差し替え
- `_EXCLUDED_MODEL_MARKERS` に単独の `image` を含めず、画像生成モデルは `gpt-image` という限定的なマーカーで除外（レビュー MEDIUM 02-03-3 の回帰固定）
- `sections.py` の `_base_providers`/`_base_fallback_providers` リテラルを `catalog.provider_names()`/`catalog.fallback_candidate_names()` へ置換し、D-03 が求める catalog 移行の6参照面すべてを完走（02-01: 1面・02-02: 5面・02-03: 2面のうち残り2面をクローズ）
- LLM設定ダイアログに `openai_section_frame` を新設（モデル欄・未確認モデル注記ラベル・APIキー欄・マスクトグル・環境変数注記・モデル更新ボタン）。Claude セクションを雛形に既存規約（テーマ辞書・`self._font`）を踏襲
- `dialog.py` の `_on_provider_change` に openai 分岐を追加し、他の全分岐（claude/gemini/tesseract/else の4箇所）に `openai_section_frame.pack_forget()` を追加漏れなく配線
- `_on_openai_model_change` を新設。`is_reasoning_model`（D-13・単一判定源）のみで temperature/effort 欄の表示を切替え、UI側に独自のモデル名判定を持たせない
- `model_fetch.py` に `_refresh_openai_models` を新設。取得失敗時と0件合流時が完全に同一の combobox values・LANG ステータスキーへ合流することを回帰テストで固定（D-08 の「観測可能な結末の同一性」・レビュー MEDIUM-11）
- lang.py ja/en へ `llm_openai_model_unverified_note`・`llm_fetching_openai_models`・`llm_env_key_unset_static_openai` を各参照タスクと同一コミットで追加
- 回帰テスト60件超を新規追加。AST ベースの構造アサーション（純関数性・正規表現/集合リテラル非依存・threading 非起動）で実装詳細に強く結合しない検証を実現
- フルテストスイート 1333 passed / 0 failed（単発実行で環境要因の Tcl/Tk フレーキーが2件発生したが、単体実行では常に green と確認。STATE.md 既知課題・Phase 3 V190-QA-01 で引き取り済み）

## Task Commits

1. **Task 1: OpenAI モデル一覧取得・除外フィルタ純関数・確認済み優先の並び替え** - `4d56881` (feat)
2. **Task 2: LLM 設定ダイアログの OpenAI セクション新設とプロバイダ一覧の catalog 化** - `15da2d0` (feat)
3. **Task 3: dialog.py の openai 分岐・セッションキー同期と非同期モデル取得の配線** - `57c0c45` (feat)

**Plan metadata:** （本コミットの直後に別途記録）

## Files Created/Modified

- `pagefolio/ocr_providers/openai_provider.py` - `filter_selectable_models`/`order_models_for_display` 新設、`list_models()` を本実装化
- `pagefolio/dialogs/llm_config/sections.py` - `_base_providers`/`_base_fallback_providers` の catalog 化、`openai_section_frame` 新設
- `pagefolio/dialogs/llm_config/dialog.py` - `_on_provider_change` の openai 分岐、`_on_openai_model_change` 新設、`_apply` のセッションキー同期・openai_model 収集
- `pagefolio/dialogs/llm_config/model_fetch.py` - `_refresh_openai_models` 新設
- `pagefolio/lang.py` - ja/en へ OpenAI 関連3キーを追加
- `tests/test_ocr_providers.py` - モデル一覧取得・フィルタ・並び替えの回帰テスト4クラス23テスト
- `tests/test_provider_ui.py` - openai セクション・往復・モデル変更・モデル取得配線の回帰テスト8クラス

## Decisions Made

- **`_EXCLUDED_MODEL_MARKERS` から単独 `image` を除外:** レビュー MEDIUM 02-03-3 の指摘どおり、将来 ID に `image` を含む vision 対応チャットモデルが出た場合の過剰除外を避けるため、画像生成モデルは `gpt-image` という限定的なマーカーで落とす設計に確定した
- **`order_models_for_display` の並び替え仕様:** `VERIFIED_VISION_MODELS`（02-01 の能力マトリクス由来）を宣言順で先頭に据え、重複は先勝ちで1回のみ出す実装とした。Combobox の先頭・値未設定時の既定選択値が常に画像入力確認済みモデルになる
- **D-08 の観測同一性の実装方針:** `_on_error` のフォールバック値を `order_models_for_display(OpenAIProvider.RECOMMENDED_MODELS)` とし、`list_models()` が api_key 未設定または0件合流時に返す `list(RECOMMENDED_MODELS)` と値として完全一致することを `TestRefreshOpenaiModels` で固定した。両者は構造的に等しくなる（`RECOMMENDED_MODELS` 自体が全件確認済みのため並び替えても順序不変）
- **AST ベースの構造アサーション方式:** レビュー LOW-17 の方針どおり、`inspect.getsource` の部分文字列検査ではなく `ast.parse` による構文木検査を全面採用した（純関数性・is_reasoning_model 呼び出しの存在・正規表現/集合リテラル/threading 参照の非存在）

## Deviations from Plan

None - plan executed exactly as written（3タスクとも計画どおりの実装で完了。checkpoint・auth gate の発生なし）。

## Issues Encountered

- フルテストスイート `pytest -q`（単一プロセス）初回実行時、`tests/test_shortcuts_dialog.py` の2テストが Tk インタプリタ生成失敗（`_tkinter.TclError`: `ttk/treeview.tcl` 読み込み不可）で ERROR になった。STATE.md に記録済みの既知環境フレーキー（Tcl/Tk リソース消耗系）と同種で、単体実行（`pytest tests/test_shortcuts_dialog.py`）では 12/12 green、フルスイート再実行でも 1333 passed / 0 failed と確認済み。本プランのコード変更とは無関係と判断し、コード変更は行わずここに記録した（Phase 3 V190-QA-01 で引き取り予定）

## User Setup Required

None - 本プランは既存コードの拡張とテスト追加のみで、外部サービス設定・APIキー入力を必要としない（実 API 呼び出しはすべてテスト内でモック化）。

## Next Phase Readiness

- V190-CAT-01（catalog 一元化・D-03 の6参照面移行）が完走し、V190-OAI-01/02/03（プロバイダ選択・セッションAPIキー・モデル一覧取得）が本プランで実装完了
- 「ユーザーが OpenAI を選び、キーを入れ、モデルを選び、OCR を実行して確認ダイアログを経て結果を得る」という主経路が通る状態になった（02-02 の安全境界の上に本プランの選択可能化が乗った）
- 02-04（OpenAI 固有設定 UI: reasoning effort・detail・organization/project ID の各欄・human-verify）が着手可能。`_on_openai_model_change` は 02-04 で reasoning effort 欄の表示条件をこの同じ関数へ追加する設計になっている

## Self-Check: PASSED

All created/modified files and commit hashes verified to exist on disk / in git history.

---
*Phase: 02-ocr-openai-chatgpt*
*Completed: 2026-08-11*
