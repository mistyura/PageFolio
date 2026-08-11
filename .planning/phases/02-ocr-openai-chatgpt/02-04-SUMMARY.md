---
phase: 02-ocr-openai-chatgpt
plan: 04
subsystem: ocr
tags: [openai, chatgpt, llm-config, tkinter, fallback, http-headers, input-validation, pytest, ast, docs]

requires:
  - phase: 02-ocr-openai-chatgpt (02-02)
    provides: "ocr_dialog.py/batch_ocr.py の catalog 移行と OpenAI の送信先確認・コスト確認の安全境界"
  - phase: 02-ocr-openai-chatgpt (02-03)
    provides: "openai_section_frame・_on_openai_model_change（is_reasoning_model 単一判定源）・セッション限定キー配線"
provides:
  - "OpenAI 固有パラメータ4欄（detail・reasoning effort・organization・project ID）の UI・入力検証・永続化"
  - "EFFORT_VALUES_BY_MODEL / effort_values_for_model / _sanitize_header_value（openai_provider.py の多層防御）"
  - "_validate_openai_id（印字可能ASCII・128文字以内・不正時は明示エラーで Apply 中断）"
  - "OpenAI をフォールバック候補として使えることの回帰テストと docs/OCR-PROVIDERS.md・docs/CONFIGURATION.md への追記"
  - "ocr_dialog.py の openai プロバイダ再生成分岐（_apply_llm_settings・_on_run）の欠落修正（実機不具合の是正）"
  - "実 API キーによる実機確認3件（設定UI・単発/バッチOCR・フォールバック発動）の記録"
affects: [02-VALIDATION.md, phase-3-qa-release-gate]

actuals:
  tokens: 21858
  tasks: 5
  commits: 3

tech-stack:
  added: []
  patterns:
    - "モデル依存の判断（値域・reasoning対応可否）を openai_provider.py 1箇所へ集約する設計をパラメータ4欄へも継続（D-13 と同型）"
    - "入力境界（_validate_openai_id）とヘッダ組み立て境界（_sanitize_header_value）の2層防御で、手編集された settings.json 由来の制御文字混入値でも安全側に倒す"
    - "プロバイダ固有の再生成分岐は provider ごとに明示 elif を並べる既存パターン（claude/gemini/runpod）へ揃える。汎用 else 分岐へのフォールスルーは『APIキー不要なプロバイダ』を暗黙の前提にしており新プロバイダ追加時に必ず確認する"

key-files:
  created:
    - .planning/phases/02-ocr-openai-chatgpt/02-04-SUMMARY.md
  modified:
    - pagefolio/dialogs/llm_config/sections.py
    - pagefolio/dialogs/llm_config/dialog.py
    - pagefolio/ocr_providers/openai_provider.py
    - pagefolio/ocr_dialog.py
    - pagefolio/lang.py
    - docs/OCR-PROVIDERS.md
    - docs/CONFIGURATION.md
    - tests/test_provider_ui.py
    - tests/test_ocr_providers.py
    - tests/test_ocr_fallback.py

key-decisions:
  - "Task 1 着手時、作業ツリーに EFFORT_VALUES_BY_MODEL/effort_values_for_model/_sanitize_header_value/_apply_gen_params の多層防御/_build_payload の detail クランプが事前実装されていた。02-CAPABILITY-MATRIX.md の allowed_effort_values 列と完全一致することを検証したうえで Task 1 のコミットへそのまま引き継いだ（再実装せず検証のみ）"
  - "organization/project の許可文字は英数字限定ではなく HTTP ヘッダ値として安全な印字可能 ASCII（\\x21〜\\x7E）・長さ1〜128とし、不正時は _validate_openai_id が (False, '') を返して messagebox.showerror で Apply を中断する。入力欄の値は消さない（レビュー MEDIUM-12 / 02-04-4）"
  - "reasoning effort は readonly Combobox + effort_values_for_model() 由来の候補のみとし、Claude の effort_frame/ocr_effort/_EFFORT_VALUES は一切流用しない（D-15）。プロバイダ側 _apply_gen_params にも許容集合外の値を送らない最終ガードを追加（レビュー HIGH 02-04-1）"
  - "フォールバック実機手順は実コード照合の結果、HTTP 401（無効キー）は RuntimeError になり fatal にならないため発火しないと判明。手順を『到達不能URLによる ConnectionError』へ変更した（レビュー HIGH 02-04-2）。ocr_fallback.py（次候補選択の純ロジック層）はプロバイダ名非依存のまま無変更"
  - "Task 3B の実機確認で発見した実バグ（下記参照）を 36e7cc2 で修正。原因は ocr_dialog.py の2つのプロバイダ再生成 if/elif チェーンに openai 専用分岐が無く、APIキー不要前提の汎用 else へフォールスルーしていたこと"

patterns-established:
  - "新規プロバイダ追加時は catalog 化された参照面（一覧・表示名・送信先ホスト等）だけでなく、プロバイダ再生成のような『同じ処理が2箇所に手書きで存在する』分岐にも新プロバイダの明示 elif が必要かを個別に確認する（catalog 一元化が届いていない残存箇所の存在を示す実例）"

requirements-completed: [V190-OAI-07, V190-OAI-08, V190-OAI-09, V190-OAI-10]

coverage:
  - id: D1
    description: "OpenAI セクションに detail（既定 high・low/high/auto）・reasoning effort（推論系モデルのみ表示・readonly・能力マトリクス由来の候補値のみ）・organization/project（空なら非付与・印字可能ASCII検証）の4欄が追加され、pagefolio_settings.json へ永続化され build_provider 経由で OpenAIProvider に届く"
    requirement: "V190-OAI-08"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiDetailPersistence"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiReasoningEffortWidget"
        status: pass
    human_judgment: false
  - id: D2
    description: "reasoning effort は is_reasoning_model が真のモデル選択時のみ表示され、候補は effort_values_for_model() 由来の readonly Combobox。値域未記録モデルでは無効化され reasoning_effort を送らない。プロバイダ側 _apply_gen_params も許容集合外の値を送らない最終ガードを持つ"
    requirement: "V190-OAI-09"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiReasoningEffortWidget"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiReasoningEffortIsNotClaudeEffort"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestOpenAIEffortValueGuard"
        status: pass
      - kind: manual_procedural
        ref: "02-04-PLAN.md Task 3A 手順6/7（実機・ユーザー承認）"
        status: pass
    human_judgment: false
  - id: D3
    description: "organization/project は任意入力で空なら OpenAI-Organization/OpenAI-Project ヘッダが一切付与されない。不正な値（空白・制御文字・129文字以上・非ASCII）は _validate_openai_id が拒否し、Apply が明示エラーダイアログで中断してユーザー入力を保持する"
    requirement: "V190-OAI-10"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiIdValidation"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiApplyAbortsOnInvalidId"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenAiHeadersOmittedWhenEmpty"
        status: pass
      - kind: manual_procedural
        ref: "02-04-PLAN.md Task 3A 手順9（実機・ユーザー承認）"
        status: pass
    human_judgment: false
  - id: D4
    description: "OpenAI をフォールバック候補一覧に追加でき、フォールバック発動時に OpenAI の表示名と api.openai.com を明示した確認ダイアログが再提示される。ocr_fallback.py は無変更のまま openai に対応し、どの例外種別が実際にフォールバックを発火させるかが回帰テストで固定されている"
    requirement: "V190-OAI-07"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py（next_fallback_candidate/next_summary_candidate の openai ケース）"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackToOpenai"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackTriggerKinds"
        status: pass
      - kind: manual_procedural
        ref: "02-04-PLAN.md Task 3C 手順1〜8（実機・ユーザー承認）"
        status: pass
    human_judgment: true
    rationale: "一次プロバイダの実致命的失敗（ConnectionError）を実環境で誘発し、確認ダイアログの実描画と『はい/いいえ』後の実際の送信先切替を確認する必要があるため。自動テストは純関数・確認本文の文字列・拒否時挙動・発火例外種別の固定までに留まる"
  - id: D5
    description: "OpenAI で単発OCR・バッチOCRを実行する前の送信先確認ダイアログの実描画・「いいえ」での中止・単価突き合わせ・未確認モデル注記が実機で確認されている"
    verification:
      - kind: manual_procedural
        ref: "02-04-PLAN.md Task 3B 手順1〜8（実機・ユーザー承認。手順2は初回不合格 → 36e7cc2 で修正後に再検証し合格）"
        status: pass
    human_judgment: true
    rationale: "Tkinter モーダルダイアログの実描画と実 API 応答、および公式価格ページとの目視突き合わせが必要なため"

duration: 約68分（4a74439 13:54 → 36e7cc2 15:01、実機確認の待ち時間を含む）
completed: 2026-08-11
status: complete
---

# Phase 2 Plan 4: OpenAI 固有パラメータ・フォールバック・ドキュメント Summary

**OpenAI の detail/reasoning effort/organization/project の4欄と読み取り専用フォールバック配線を実装し、実機確認で発見したAPIキー未送信バグ（`ocr_dialog.py`のプロバイダ再生成分岐の欠落）を修正して V190-OAI-07〜10 を完了させた**

## Performance

- **Duration:** 約68分（コミット `4a74439`〜`36e7cc2`、うち大半は3件の実機確認の待ち時間）
- **Started:** 2026-08-11T13:54:36+09:00
- **Completed:** 2026-08-11T15:01:42+09:00
- **Tasks:** 5 / 5（自動実装2件 + human-verify 3件）
- **Files modified:** 11（実装7・テスト3・ドキュメント2 ※ dialog.py はテスト重複カウントなし）

## Accomplishments

- OpenAI セクションへ detail（既定 `high`）・reasoning effort（推論系モデル選択時のみ表示の readonly Combobox）・organization / project ID（任意入力・空なら非付与）の4欄を新設し、`pagefolio_settings.json` への永続化と `build_provider` 経由での `OpenAIProvider` への配線を完了
- `openai_provider.py` に `EFFORT_VALUES_BY_MODEL` / `effort_values_for_model()` / `_sanitize_header_value()` を実装。`_apply_gen_params` は「is_reasoning_model かつ reasoning_effort が真値かつ effort_values_for_model の許容集合内」の3条件を満たすときだけ `reasoning_effort` を payload に入れる多層防御を持つ（レビュー HIGH 02-04-1 解消）
- `dialog.py` に `_validate_openai_id(value) -> (ok, cleaned)` を新設。印字可能 ASCII（`\x21`〜`\x7E`）・長さ1〜128以外は `(False, "")` を返し、`_apply` は不正時に `messagebox.showerror` を出して Apply を中断する（ユーザー入力を破棄しない・レビュー MEDIUM-12/02-04-4 解消）
- OpenAI をフォールバック候補として設定でき、発動時の確認ダイアログ本文に `OpenAI (ChatGPT)` と `api.openai.com` の両方が含まれることを固定。`ocr_fallback.py`（次候補選択の純ロジック層）は無変更のまま openai に対応
- 実コード照合により「一次プロバイダの無効な API キーによる HTTP 401 は `RuntimeError` になり fatal にならず、フォールバックは発火しない」ことを確認し、`TestFallbackTriggerKinds` で `ConnectionError`/`TimeoutError`/サーキットブレーカーのみが `_propose_fallback` に到達することを機械固定（レビュー HIGH 02-04-2 解消）
- `docs/OCR-PROVIDERS.md` に `### OpenAIProvider` 節（必要な設定・推奨モデル・コンストラクタ・モデル別パラメータ制御・並列度・モデル一覧取得）、`docs/CONFIGURATION.md` に `### OpenAI プロバイダ設定` 節・`OPENAI_API_KEY` の機密情報記載・設定ファイルサンプルを追記
- Task 3B の実機確認で「OpenAI の API キーを設定して OCR を実行すると HTTP 401（キー未送信）になる」実バグを発見。`ocr_dialog.py` の `_apply_llm_settings` / `_on_run` の2つのプロバイダ再生成分岐に openai 専用 `elif` が無く、汎用 `else`（API キー不要前提）へ落ちて `build_provider` が `api_key` なしで呼ばれていたことが原因。claude/gemini/runpod と同型の `elif` を追加し `36e7cc2` で修正。ユーザーが再検証し合格
- 実 API キーによる実機確認3件（Task 3A: 設定UI・モデル一覧・キー非永続化／Task 3B: 単発・バッチOCR・確認ダイアログ・単価突き合わせ／Task 3C: フォールバック発動時の送信先再確認）をすべてユーザーが実施し承認済み

## Task Commits

1. **Task 1: OpenAI 固有パラメータ4欄の UI・入力検証・永続化** - `4a74439` (feat)
2. **Task 2: OpenAI をフォールバック候補として使えることの実配線確認とドキュメント追記** - `5bfb40d` (test)
3. **Task 3A: 実機確認 (1/3) — 設定 UI・モデル一覧・API キーの非永続化** - checkpoint:human-verify、コード変更なし。ユーザーが手順1〜11を実施し ✓ 承認（合格）
4. **Task 3B: 実機確認 (2/3) — 単発 OCR・バッチ OCR・確認ダイアログ・単価突き合わせ** - checkpoint:human-verify、初回不合格 → 継続タスクでの回帰修正 `36e7cc2` (fix) → 再検証で ✓ 承認（合格）
5. **Task 3C: 実機確認 (3/3) — フォールバック発動時の送信先再確認** - checkpoint:human-verify、コード変更なし。ユーザーが手順1〜8を実施し ✓ 承認（合格）

**Plan metadata:** （本コミットの直後に別途記録）

## Files Created/Modified

- `pagefolio/dialogs/llm_config/sections.py` - detail/reasoning effort/organization/project の4欄のウィジェット新設（`openai_detail_var`/`openai_effort_frame`/`openai_org_var`/`openai_project_var`）
- `pagefolio/dialogs/llm_config/dialog.py` - `_OPENAI_DETAIL_VALUES`/`_OPENAI_ID_MAX_LEN`/`_validate_openai_id`、`_on_openai_model_change` の reasoning effort 表示制御拡張、`_apply` への4キー収集と不正時中断
- `pagefolio/ocr_providers/openai_provider.py` - `EFFORT_VALUES_BY_MODEL`/`effort_values_for_model`/`_sanitize_header_value`、`_apply_gen_params` の多層防御、`_headers()` の制御文字防止
- `pagefolio/ocr_dialog.py` - `_apply_llm_settings`/`_on_run` へ openai 専用 `elif` を追加（Task 3B 回帰修正・`36e7cc2`）
- `pagefolio/lang.py` - ja/en へ8件の新規 LANG キー（detail/effort/org/project のラベル・ヒント・エラー文言）
- `docs/OCR-PROVIDERS.md` - `### OpenAIProvider` 節新設、プロバイダ一覧表への1行追加
- `docs/CONFIGURATION.md` - `### OpenAI プロバイダ設定` 節新設、`OPENAI_API_KEY` の機密情報記載・環境変数例・設定ファイルサンプル・フォールバック候補一覧への追記
- `tests/test_provider_ui.py` - detail/effort/org/project の UI・検証・永続化テスト、フォールバック確認ダイアログテスト、Task 3B 回帰修正の2テスト（`36e7cc2`）
- `tests/test_ocr_providers.py` - `TestOpenAIEffortValueGuard`（プロバイダ側多層防御の回帰）
- `tests/test_ocr_fallback.py` - `next_fallback_candidate`/`next_summary_candidate` の openai ケース

## Decisions Made

- **Task 1 の事前実装の扱い:** Task 1 着手時点で作業ツリーに `EFFORT_VALUES_BY_MODEL`/`effort_values_for_model`/`_sanitize_header_value`/`_apply_gen_params` の多層防御/`_build_payload` の detail クランプがすでに実装されていた。これを再実装せず、`02-CAPABILITY-MATRIX.md` の `allowed_effort_values` 列と完全一致することを検証したうえで Task 1 のコミットへそのまま引き継いだ
- **organization/project の許可文字境界:** 英数字限定ではなく HTTP ヘッダ値として安全な印字可能 ASCII（`\x21`〜`\x7E`）・長さ1〜128とした。将来 OpenAI が `.` や `:` を含む ID を採用しても弾かない設計（レビュー MEDIUM 02-04-4）
- **不正入力の扱い:** `_validate_openai_id` は不正値を黙って空文字化せず `(False, "")` を返し、`_apply` は `messagebox.showerror` で中断してユーザー入力を保持する（レビュー MEDIUM-12）
- **reasoning effort の非流用:** Claude の `effort_frame`/`ocr_effort`/`_EFFORT_VALUES` を一切流用せず、OpenAI 専用のウィジェットと専用 settings キー `openai_reasoning_effort` で実装した（D-15）
- **フォールバック実機手順の変更:** 実コード照合の結果、無効な API キーによる HTTP 401 はフォールバックを発火させないと判明したため、手順を「LM Studio の到達不能 URL による ConnectionError」へ変更した（レビュー HIGH 02-04-2）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] OCR 実行時に OpenAI の API キーが送信されない不具合を修正**
- **Found during:** Task 3B（human-verify・ユーザー実機報告）
- **Issue:** LLM 設定画面で OpenAI の API キーを設定して OCR 読取を実行すると `HTTP 401: "You didn't provide an API key. ..."` が返った。根本原因は `pagefolio/ocr_dialog.py` の2つのプロバイダ再生成 if/elif チェーン（`_apply_llm_settings` と `_on_run`）に `elif name == "openai":` が無く、末尾の汎用 `else` 分岐（tesseract/プラグイン専用・API キー不要前提）へ落ちていたこと。そこでは `build_provider(s, plugin_manager=...)` が `api_key` 引数なしで呼ばれるため `OpenAIProvider.api_key` が `""` になり `Bearer ` が空のまま送信されていた。claude/gemini/runpod は当初から両方に専用分岐があり無事だった。OpenAI は `ocr.py`（`_start_ocr`）と `dialogs/batch_ocr.py`（`_build_provider_once`）には正しく配線されていたが、`ocr_dialog.py` の2分岐だけ取りこぼしていた。readiness チェック `_check_cloud_api_key` は catalog 汎用実装で正しく通るため、「検証は通るのに実行時だけキーが空になる」食い違いが生じていた
- **Fix:** 両分岐に claude/gemini と同型の `elif name == "openai":` を追加し、`_resolve_api_key("openai", session_keys)` → `build_provider(..., api_key=api_key, ...)` を配線
- **Files modified:** `pagefolio/ocr_dialog.py`, `tests/test_provider_ui.py`
- **Verification:** 追加した回帰テスト（`TestOnRunOpenAiApiKeyWiringRegression::test_on_run_passes_resolved_session_key_to_build_provider`、`TestApplyLlmSettingsOpenAiApiKeyWiringRegression::test_apply_llm_settings_passes_resolved_session_key_to_build_provider`）は修正前に両方 RED であることを確認したうえで GREEN 化。修正後、ユーザーが Task 3B 手順1〜8を再実施し合格
- **Committed in:** `36e7cc2`

---

**Total deviations:** 1 auto-fixed（Rule 1・実機で発見した実バグ）
**Impact on plan:** OpenAI プロバイダの主経路（単発OCR実行）が機能しない致命的な回帰であり、Task 3B の human-verify がなければ本番相当の実 API 呼び出しでのみ顕在化していた。修正必須。スコープクリープなし（ocr_dialog.py の既存パターンへの1行差分の追随）。

## Issues Encountered

None（上記デビエーション欄に記載の回帰修正を除く）。

## User Setup Required

None - 本プランは Task 3A/3B/3C の実機確認に既存の `OPENAI_API_KEY`（環境変数またはセッション限定キー欄）を使用済み。新規の外部サービス設定は発生していない。

## Manual-Only Verification 実施結果（02-VALIDATION.md 対応）

### Task 3A: 設定 UI・モデル一覧・API キーの非永続化 → ✓ 承認（合格）

ユーザーが手順1〜11を実機で実施し合格。OpenAI セクションの表示・モデル一覧取得（先頭が推奨モデル・非チャットモデル混入なし）・reasoning effort 欄の表示切替と候補値・不正な organization 値での Apply 中断・アプリ再起動後の API キー欄空表示と `pagefolio_settings.json` 非永続化をすべて確認。

### Task 3B: 単発 OCR・バッチ OCR・確認ダイアログ・単価突き合わせ → ✓ 承認（1回差し戻し後に合格）

**初回は失敗した。** 上記「Deviations from Plan」に記載のとおり `HTTP 401` が発生し、`36e7cc2` で修正。修正後、ユーザーが手順1〜8を再実施し合格。手順4の単価突き合わせは不一致の報告なし——`02-CAPABILITY-MATRIX.md` に記録した単価と公式価格ページの現在の公表値の間で、ユーザーから乖離の指摘はなかった（積極的な数値一致証明ではなく「差し戻しに値する不一致は見つからなかった」という消極的な確認結果として記録する）。

### Task 3C: フォールバック発動時の送信先再確認 → ✓ 承認（合格）

ユーザーが手順1〜8（`http://127.0.0.1:9` による `ConnectionError` 誘発を含む）を実機で実施し合格。フォールバック確認ダイアログに `OpenAI (ChatGPT)` と `api.openai.com` の両方が表示され、「いいえ」で送信されず、「はい」で OpenAI へ切り替わって OCR が完走し、切替後のヘッダ表示が OpenAI のものへ更新されることを確認。

## Final Verification

- `python -m pytest -q --basetemp="$LOCALAPPDATA/Temp/pf_pytest_tmp"` → **1382 passed**（失敗0・error 0）
- `ruff check .` → All checks passed
- `ruff format --check .` → 90 files already formatted
- `git diff pagefolio/ocr_providers/registry.py pagefolio/ocr_providers/errors.py pagefolio/ocr_fallback.py` → 空（変更面を広げない方針を維持）
- `git diff pagefolio/constants.py 開発履歴.md README.md pyproject.toml` → 空（バージョン更新は Phase 3 へ委譲・`pyproject.toml` 編集禁止を維持）

## Next Phase Readiness

- V190-OAI-07/08/09/10 が完了し、Phase 2（OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加）の全 15 要件（V190-CAT-01/02, V190-OAI-01〜13）が Complete
- OpenAI プロバイダは detail/reasoning effort/organization・project ID の設定・フォールバック・ドキュメントまで含めて既存5プロバイダと同等の完成度に到達
- Task 3B で発見・修正した「プロバイダ再生成分岐の catalog 未到達箇所」は、今後新プロバイダを追加する際のチェック項目として `patterns-established` に記録した
- APP_VERSION・開発履歴.md・README バッジの更新は引き続き Phase 3（V190-QA-03 リリースゲート）へ委譲
- Phase 3（品質保証・リリースゲート）が着手可能な状態

## Self-Check: PASSED

すべての作成/変更ファイルとコミットハッシュがディスク上/git 履歴上に存在することを確認済み。

---
*Phase: 02-ocr-openai-chatgpt*
*Completed: 2026-08-11*
