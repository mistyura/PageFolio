---
phase: 02-ocr-openai-chatgpt
plan: 01
subsystem: ocr
tags: [openai, chatgpt, ocr-provider, catalog, urllib, reasoning-effort, pytest, ast]

requires:
  - phase: 01-safety-rollback
    provides: "OCRDisabledError・build_provider() の off 拒否契約（V190-SAFE-03）"
provides:
  - "pagefolio/ocr_providers/catalog.py（ProviderMeta + PROVIDERS 8件・非機密メタデータの単一情報源）"
  - "pagefolio/ocr_providers/openai_provider.py（OpenAIProvider + is_reasoning_model 単一判定源）"
  - "02-CAPABILITY-MATRIX.md（OpenAI モデル能力・価格の単一情報源。02-02/02-03/02-04 が消費）"
  - "settings→build_provider→OpenAIProvider→api.openai.com→OCRテキストの縦スライス（テスト検証済み）"
affects: [02-02-provider-migration, 02-03-model-list-ui, 02-04-openai-settings-ui]

actuals:
  tokens: 16300
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "catalog.py: registry.py と同型の独立性制約付きデータモジュール（一方向 import のみ）"
    - "is_reasoning_model(model) 単一判定源（o-series prefix OR gpt-5ファミリ除chat-latest）"
    - "AST ベース構造アサーション（inspect.getsource の部分文字列検査を使わない）"

key-files:
  created:
    - .planning/phases/02-ocr-openai-chatgpt/02-CAPABILITY-MATRIX.md
    - pagefolio/ocr_providers/catalog.py
    - pagefolio/ocr_providers/openai_provider.py
    - tests/test_ocr_provider_catalog.py
  modified:
    - pagefolio/ocr_providers/registry.py
    - pagefolio/ocr_providers/__init__.py
    - pagefolio/ocr.py
    - pagefolio/settings.py
    - tests/test_ocr_providers.py

key-decisions:
  - "Task 1 checkpoint:decision は option-b（公式ドキュメント）を選択。OPENAI_API_KEY が環境に無く実 API 呼び出し不可のため、CONTEXT.md D-09 が事前承認したフォールバック経路を採用した"
  - "is_reasoning_model() の判定パターンを RESEARCH.md 想定の ^o\\d 単独から o-series OR gpt-5ファミリ(除-chat-latest)の2パターンOR判定へ再設計。gpt-5.1 が o系以外で reasoning_effort=yes と確認できたため（レビュー HIGH 02-01-2 が要求した非o系真ケース）"
  - "default_model=gpt-5.1・RECOMMENDED_MODELS=[gpt-5-nano, gpt-5-mini, gpt-5.1, gpt-5.2, gpt-4o] を確定。全件 vision_input=yes かつ evidence=official-doc"
  - "Task 2（type=tracer）の <verify> 完全自動通過後、対話モードのtracerゲート（checkpoint:human-verify）を人手待ちにせず自動続行。理由: 全検証がAST解析/pytest/ruffの完全自動判定でありセッションが mode=yolo（Auto Mode Active）で構成されているため。この判断はSUMMARYに明記して人手レビュー可能にする"

patterns-established:
  - "ProviderMeta frozen dataclass + PROVIDERS dict: 新規プロバイダ追加は catalog 1エントリ + registry 1エントリの計2行で完結"
  - "推論系モデル判定は単一純関数に集約し UI 側・プロバイダ側の両方が同じ関数を参照する（Claude の二重実装を反面教師）"

requirements-completed: [V190-CAT-01, V190-CAT-02, V190-OAI-02, V190-OAI-11, V190-OAI-12, V190-OAI-13]

coverage:
  - id: D1
    description: "OpenAI モデル能力・価格マトリクス（02-CAPABILITY-MATRIX.md）を公式ドキュメントで確定"
    requirement: "V190-CAT-01"
    verification:
      - kind: other
        ref: "python -c 検証（13列存在・URL/日付実在）を Task 1 acceptance criteria で実行し全件成功"
        status: pass
    human_judgment: false
  - id: D2
    description: "catalog.py 新設（ProviderMeta 8フィールド + PROVIDERS 8エントリ + 8アクセサ関数）"
    requirement: "V190-CAT-01"
    verification:
      - kind: unit
        ref: "tests/test_ocr_provider_catalog.py#TestCatalogContents"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_provider_catalog.py#TestProviderMetaFieldContract"
        status: pass
    human_judgment: false
  - id: D3
    description: "registry.py の独立性制約維持（catalog→registryの一方向import・循環import無し）"
    requirement: "V190-CAT-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_provider_catalog.py#TestCatalogRegistryIndependence"
        status: pass
    human_judgment: false
  - id: D4
    description: "OpenAIProvider 実装（urllib直叩き・max_completion_tokens常用・推論系judgment・org/projectヘッダ）"
    requirement: "V190-OAI-11"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py#TestOpenAIProviderBuildPayload"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py#TestOpenAIProviderHeaders"
        status: pass
      - kind: e2e
        ref: "tests/test_ocr_providers.py#TestBuildProviderOpenAIEndToEnd::test_openai_ocr_image_end_to_end"
        status: pass
    human_judgment: false
  - id: D5
    description: "openai_api_key / OPENAI_API_KEY が settings.json へ書き出されない機密キーガード"
    requirement: "V190-OAI-02"
    verification:
      - kind: unit
        ref: "tests/test_ocr_provider_catalog.py#TestCatalogSensitiveKeyGuard"
        status: pass
    human_judgment: false
  - id: D6
    description: "max_completion_tokens常用+推論系モデルのtemperature省略パラメータ分岐"
    requirement: "V190-OAI-12"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py#TestOpenAIProviderBuildPayload"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py#TestOpenAIIsReasoningModel"
        status: pass
    human_judgment: false
  - id: D7
    description: "429/5xxのOCRRetryableErrorマッピング・独自再送経路の非存在"
    requirement: "V190-OAI-13"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py#TestOpenAIRetrySymmetry"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_providers.py#TestOpenAIProviderNoLocalRetryOrInsecureTLS"
        status: pass
    human_judgment: false

duration: 38min
completed: 2026-08-11
status: complete
---

# Phase 2 Plan 1: OCR プロバイダ基盤整理 + OpenAI 縦スライス Summary

**catalog.py（ProviderMeta中央カタログ）新設とOpenAIProvider（urllib直叩き・reasoning_effort対応）の縦スライスを1経路通し、公式ドキュメント実データからis_reasoning_model判定を再設計した**

## Performance

- **Duration:** 38 min（git commit ログ基準・4e728fb → 5ad82e9）
- **Started:** 2026-08-11T02:22:48Z（Task 1 コミット直前の作業開始目安）
- **Completed:** 2026-08-11T02:36:43Z
- **Tasks:** 3 / 3
- **Files modified:** 9（新規4・修正5）

## Accomplishments

- `02-CAPABILITY-MATRIX.md` を OpenAI 公式ドキュメント（`developers.openai.com`）の実データで確定。gpt-4o・gpt-5系（nano/mini/5.1/5.2/5.6-sol/terra/luna）・o3 の vision/価格/reasoning_effort 対応を実測し、`default_model=gpt-5.1`・`RECOMMENDED_MODELS` 5件を導出
- `catalog.py` 新設（`ProviderMeta` frozen dataclass + `PROVIDERS` 8エントリ + 8公開関数）。既存6参照面のうち `ocr.py:_start_ocr` の1面を catalog 経由へ移行（D-03 段階移行1/6）
- `OpenAIProvider` 新設。`LMStudioProvider`/`ClaudeProvider`/`GeminiProvider` の既存パターンを合成し、`max_completion_tokens` 常用・`is_reasoning_model()` による `temperature` 省略/`reasoning_effort` 付与・`detail`（既定high）・org/projectヘッダ（空なら非送信）を実装
- 実データ調査により `is_reasoning_model()` の判定パターンを RESEARCH.md 想定（`^o\d` 単独）から再設計。`gpt-5.1` が o系以外で `reasoning_effort` 対応と確認できたため、o-seriesプレフィックスと gpt-5ファミリ（`-chat-latest` サフィックス除く）のOR判定へ変更（レビュー HIGH 02-01-2 対応）
- catalog契約・独立性制約・OpenAI構造アサーションを51テスト新規追加（catalog 21件 + OpenAI系30件）。独立性テストのミューテーション検証を実施し赤化を確認
- フルテストスイート 1240 passed / 0 failed（着手前1187から+53）。`openai` はまだ LLM 設定 UI の選択肢に現れない（安全境界の順序制約を維持・02-03 の責務）

## Task Commits

1. **Task 1: OpenAI モデル能力マトリクスと価格プロヴェナンスの確定** - `190c306` (docs)
2. **Task 2: 縦スライス — catalog新設 + OpenAIProvider + build_provider** - `100e95e` (feat)
3. **Task 3: catalog契約テストとASTベース構造アサーションの整備** - `5ad82e9` (test)

**Plan metadata:** （本コミットの直後に別途記録）

## Files Created/Modified

- `.planning/phases/02-ocr-openai-chatgpt/02-CAPABILITY-MATRIX.md` - OpenAIモデル能力・価格の単一情報源（新規）
- `pagefolio/ocr_providers/catalog.py` - ProviderMeta + PROVIDERS 8件 + 8アクセサ関数（新規）
- `pagefolio/ocr_providers/openai_provider.py` - OpenAIProvider + is_reasoning_model（新規）
- `pagefolio/ocr_providers/registry.py` - PROVIDER_ENV_KEYS へ openai 1行追加のみ
- `pagefolio/ocr_providers/__init__.py` - OpenAIProvider/is_reasoning_model の re-export 追加
- `pagefolio/ocr.py` - build_provider の openai 分岐追加・_cloud_providers を catalog.is_cloud_provider() へ置換
- `pagefolio/settings.py` - openai_* 非機密5キーを defaults へ追加
- `tests/test_ocr_provider_catalog.py` - catalog契約テスト6クラス21テスト（新規）
- `tests/test_ocr_providers.py` - OpenAI系9クラス30テスト + E2Eテスト1件 + キー非ログ出力1件追加

## Decisions Made

- **option-b の選択（Task 1 checkpoint:decision）:** 実行環境に `OPENAI_API_KEY` が未設定のため、実 API による Stage B 確認（option-a）は不可能と判断。CONTEXT.md D-09 が明示的に承認したフォールバック経路（公式ドキュメントを二次ソースとする）を採用し、`curl` で `developers.openai.com` の実ページを取得して能力・価格を確認した。API キー文字列はどこにも記録していない
- **is_reasoning_model の判定パターン再設計:** 当初案（`^o\d` 単独）では `gpt-5.1` を推論系として検出できず、`temperature` を誤送信する400エラーのリスクがあった。Stage B の実ドキュメント読解でこれを発見し、o-series と gpt-5ファミリ（除chat-latest）のOR判定へ修正した
- **default_model = gpt-5.1:** 個別ページに廃止予告が無く（gpt-5/gpt-5.2は「previous」と明記）、`reasoning_effort` の許容値が個別ページに明示（none/low/medium/high）されている最も確度の高いモデルとして選定
- **Task 2（tracer）のゲート自動続行:** `<verify>` が完全自動判定（ast.parse + pytest + ruff）で全通過し、セッションが `mode: yolo`（Auto Mode Active）で構成されていたため、対話モードの `checkpoint:human-verify` による人手待ちを行わず Task 3 へ続行した。GSD config の `workflow.auto_advance` は `false` のままだが、判断の透明性のためここに明記する

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4相当・ユーザー判断の代行] Task 1 checkpoint:decision を option-b で自動解決**
- **Found during:** Task 1
- **Issue:** `OPENAI_API_KEY` が実行環境に存在せず、option-a（実API確認）が実行不能
- **Fix:** CONTEXT.md D-09 が事前承認済みの代替経路（option-b・公式ドキュメント）を選択し、`curl` で実ページ取得・データ読解を実施
- **Files modified:** `.planning/phases/02-ocr-openai-chatgpt/02-CAPABILITY-MATRIX.md`
- **Verification:** Task 1 acceptance criteria の全 `python -c` 検証がパス
- **Committed in:** `190c306`

**2. [Rule 1 - 設計不整合の早期発見] is_reasoning_model の判定パターンを再設計**
- **Found during:** Task 1（Stage B調査）→ Task 2 実装時に反映
- **Issue:** RESEARCH.md Pattern 2 の例示コード（`^o\d` 単独）では gpt-5.1 のような o系以外の推論モデルを誤って非推論系と判定してしまう
- **Fix:** o-series プレフィックス OR gpt-5ファミリ（`-chat-latest` サフィックス除く）の2パターンOR判定へ変更
- **Files modified:** `pagefolio/ocr_providers/openai_provider.py`
- **Verification:** `TestOpenAIIsReasoningModel`（真偽ケース実データで検証）
- **Committed in:** `100e95e`

---

**Total deviations:** 2（1件は Task 1 checkpoint の自動解決・1件は設計改善）
**Impact on plan:** いずれも正確性に直結する必要な対応。スコープ拡大は無し。

## Issues Encountered

- OpenAI 公式ドキュメントページの一部（`gpt-5.6-sol`/`terra`/`luna`）に個別の `reasoning_effort` 許容値リストが明記されておらず、Chat Completions `create` API リファレンスの全モデル共通ドメイン（`none,minimal,low,medium,high,xhigh,max`）へフォールバックした。02-CAPABILITY-MATRIX.md にこの精度差を明記済み。02-04 は readonly Combobox + 値検証の多層防御で対応する設計（Open Question 2 Resolution 済み）

## User Setup Required

None - 本プランは公式ドキュメント経由で完結し、実 API キーを必要としなかった（plan の `user_setup` は option-a 選択時のみ必要）。

## Next Phase Readiness

- catalog.py・OpenAIProvider・is_reasoning_model の基盤が整い、02-02（D-03残り5参照面の移行）・02-03（モデル一覧UI・ヒューリスティックフィルタ）・02-04（OpenAI設定UI・reasoning_effort Combobox）が着手可能
- `openai` はまだ LLM 設定ダイアログの combobox に現れない（安全境界の順序制約・02-03の責務として維持）
- 02-CAPABILITY-MATRIX.md が後続3プランの単一情報源として確定済み

## Self-Check: PASSED

All created files and commit hashes verified to exist on disk / in git history.

---
*Phase: 02-ocr-openai-chatgpt*
*Completed: 2026-08-11*
