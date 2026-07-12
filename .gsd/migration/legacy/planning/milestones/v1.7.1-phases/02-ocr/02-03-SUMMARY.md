---
phase: 02-ocr
plan: 03
subsystem: ocr
tags: [ocr-providers, url-validation, urllib, llm-config, i18n-none]

requires:
  - phase: 02-01
    provides: "PluginManager.get_ocr_provider/list_ocr_providers 公開アクセサ（本プランは未使用だが同フェーズの土台）"
  - phase: 02-02
    provides: "TesseractProvider 段階的縮退・OCRDialog 非モーダル注記パターン（本プランは独立に L-6 を解消）"
provides:
  - "_require_http_scheme(url) 共通ヘルパー（LM Studio/Ollama/RunPod の _post_chat/list_models 計6箇所へ統一適用・http/https 以外は RuntimeError）"
  - "Gemini モデル名の URL パスセグメントエスケープ（urllib.parse.quote(self.model, safe=\"\")）"
  - "_raise_mapped_http_error の err_body 500文字切り詰め（全プロバイダ共通ヘルパー経由で LMStudio/Claude/Gemini/Ollama/RunPod 全てに波及）"
  - "ClaudeProvider.list_models の has_more/last_id カーソルページネーション対応"
  - "LLMConfigDialog._probe_lm_provider(update_combo) 共通ヘルパー（_fetch_models/_test_connection の重複解消・LM Studio ペアのみ）"
  - "OCRDialog._apply_llm_settings 末尾での app._update_ocr_buttons_state() 呼び出し（provider再生成の例外有無に関わらず実行）"
affects: [02-04]

tech-stack:
  added: []
  patterns:
    - "urllib.parse.urlsplit(url).scheme によるスキーム検証を全 URL 系プロバイダへ統一適用するパターン（_require_http_scheme）"
    - "update_combo フラグによるパラメータ化で薄いラッパーメソッドへ重複ロジックを集約するパターン（_probe_lm_provider）"
    - "provider再生成の try/except 外側に副作用呼び出しを置くことで例外パスでも状態同期を保証するパターン（getattr+callable の防御的呼び出し）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_providers.py
    - pagefolio/dialogs/llm_config.py
    - pagefolio/ocr_dialog.py
    - tests/test_ocr_providers.py
    - tests/test_provider_ui.py
    - .planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md

key-decisions:
  - "_require_http_scheme はリクエスト送信直前（_post_chat/list_models 冒頭）で呼び、コンストラクタでの eager 検証はしない（RESEARCH.md A2・空URL/入力途中でもインスタンス化は失敗させない既存方針を維持）"
  - "RunPodProvider は既存の api_key/url 未設定チェック（早期 return/raise）の後段に _require_http_scheme を追加し、優先順位（キー未設定→URL未設定→スキーム不正）を保った"
  - "ClaudeProvider.list_models は _fetch_models_page(after_id) ヘルパーへ1ページ分の HTTP 呼び出しを切り出し、while ループでカーソルを辿る設計にした（1ページ完結時は従来と同一結果で後方互換）"
  - "_probe_lm_provider の重複解消は LM Studio ペアのみに限定し、Ollama ペア（_fetch_ollama_models/_test_ollama_connection）は D-11 に従い変更していない（Pitfall 5 回避・意図的な暗黙拡張なし）"
  - "_update_ocr_buttons_state 呼び出しは getattr(self.app, \"_update_ocr_buttons_state\", None) + callable チェックの防御的パターンとし、既存 SimpleNamespace スタブとの後方互換を維持した（新規テスト以外の既存スタブは無変更で通過）"

patterns-established:
  - "全プロバイダ共通ヘルパー（_raise_mapped_http_error 等）を変更する際は Pitfall 4 のとおり横断的な既存テストへの影響を確認してから進める"

requirements-completed: [V171-OCR-01]

coverage:
  - id: D1
    description: "LM Studio / Ollama / RunPod のユーザー入力 URL が http/https 以外のスキームで RuntimeError になる（_require_http_scheme を6箇所へ統一適用）"
    requirement: "V171-OCR-01"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestRequireHttpScheme, TestUrlSchemeEnforcedOnProviders"
        status: pass
    human_judgment: false
  - id: D2
    description: "Gemini モデル名が URL パスセグメントとしてエスケープされてエンドポイントに埋め込まれる（quote(self.model, safe='')）"
    requirement: "V171-OCR-01"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestGeminiModelEscape"
        status: pass
    human_judgment: false
  - id: D3
    description: "HTTP エラーメッセージの body が500文字で切り詰められる（_raise_mapped_http_error 共通ヘルパー経由・全プロバイダ波及）"
    requirement: "V171-OCR-01"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestErrorBodyTruncation"
        status: pass
    human_judgment: false
  - id: D4
    description: "ClaudeProvider.list_models が has_more/last_id カーソルを辿って全モデルを取得する（1ページ完結時は後方互換）"
    requirement: "V171-OCR-01"
    verification:
      - kind: unit
        ref: "tests/test_ocr_providers.py::TestClaudeListModelsPagination"
        status: pass
    human_judgment: false
  - id: D5
    description: "LLMConfigDialog の _fetch_models/_test_connection 重複ロジックが _probe_lm_provider(update_combo) へ集約される（呼び出し元は不変・LM Studioペアのみ）"
    requirement: "V171-OCR-01"
    verification:
      - kind: unit
        ref: "pytest tests/test_provider_ui.py -q（全体グリーンで回帰なし確認・専用ユニットテストは新設せず既存回帰網羅に依拠）"
        status: pass
    human_judgment: false
  - id: D6
    description: "OCR ダイアログで provider を 'off' に切り替えるとメイン画面ツールバーの OCR ボタンが disabled になる（app._update_ocr_buttons_state() 経由・provider再生成の例外有無に関わらず実行）"
    requirement: "V171-OCR-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyLlmSettingsOffToggleButtons"
        status: pass
    human_judgment: false

duration: 約35分
completed: 2026-07-05
status: complete
---

# Phase 02 Plan 03: L-6 一括解消（URL検証・Gemini quote・エラー切り詰め・Claude ページネーション・設定重複解消・offボタン同期）Summary

**OCRプロバイダ層のURLスキーム検証統一適用・Gemini quoteエスケープ・エラーbody切り詰め・Claude list_modelsページネーションに加え、LLMConfigDialogの重複解消とoff切替時のOCRボタン状態同期をV171-OCR-01（L-6）として一括実装**

## Performance

- **Duration:** 約35分（調査・実装・テスト作業）
- **Started:** 2026-07-05T01:20:00Z (推定)
- **Completed:** 2026-07-05T01:36:22Z
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments
- `pagefolio/ocr_providers.py` に `_require_http_scheme(url)` 共通ヘルパーと `_ALLOWED_URL_SCHEMES = ("http", "https")` を新設し、LM Studio/Ollama/RunPod の `_post_chat`/`list_models`（計6箇所）へ統一適用（L-6e/D-13）
- Gemini `_post_payload` のエンドポイント生成で `urllib.parse.quote(self.model, safe="")` によりモデル名を URL パスセグメントとしてエスケープ（L-6f）
- `_raise_mapped_http_error` の `err_body` を500文字へ切り詰め。全プロバイダ共通ヘルパー経由のため LMStudio/Claude/Gemini/Ollama/RunPod 全てのエラーメッセージに一貫適用（L-6d）
- `ClaudeProvider.list_models` を `_fetch_models_page(after_id)` へリファクタし、`has_more`/`last_id` カーソルを辿る while ループで全ページのモデルを連結（1ページ完結時は後方互換）（L-6b）
- `LLMConfigDialog._fetch_models`/`_test_connection`（LM Studio 用）の重複ロジックを `_probe_lm_provider(update_combo)` へ集約。呼び出し元シグネチャは不変。Ollama ペアは D-11 に従い対象外のまま維持（L-6i）
- `OCRDialog._apply_llm_settings` 末尾（provider 再生成の try/except 外側）に `app._update_ocr_buttons_state()` 呼び出しを追加し、"off" 切替時にツールバー OCR ボタンが disabled になるよう同期（L-6j）
- `260610-aaa-REVIEW.md` の L-6b/d/e/f/i/j に解消済みマーク＋コミットハッシュを追記（D-12）

## Task Commits

Each task was committed atomically:

1. **Task 1: プロバイダ層 L-6 修正（URL スキーム検証・Gemini quote・エラー body 切り詰め・Claude list_models ページネーション）** - `892244c` (feat)
2. **Task 2: 設定ダイアログ重複解消（L-6i）+ "off" 切替ボタン状態同期（L-6j）+ REVIEW.md 追記** - `14d09f5` (feat), `e129a29` (docs)

## Files Created/Modified
- `pagefolio/ocr_providers.py` - `_require_http_scheme`/`_ALLOWED_URL_SCHEMES` 新設・LM Studio/Ollama/RunPod の6箇所へ適用・Gemini `quote()` エスケープ・`_raise_mapped_http_error` の500文字切り詰め・`ClaudeProvider._fetch_models_page`/`list_models` ページネーション
- `pagefolio/dialogs/llm_config.py` - `_probe_lm_provider(update_combo)` 新設、`_fetch_models`/`_test_connection` を薄いラッパー化
- `pagefolio/ocr_dialog.py` - `_apply_llm_settings` 末尾に `app._update_ocr_buttons_state()` の防御的呼び出しを追加
- `tests/test_ocr_providers.py` - `TestRequireHttpScheme`/`TestUrlSchemeEnforcedOnProviders`/`TestGeminiModelEscape`/`TestErrorBodyTruncation`/`TestClaudeListModelsPagination` を新規追加（計17テスト）
- `tests/test_provider_ui.py` - `_make_apply_llm_settings_stub` に `app_extra` パラメータを追加（後方互換）、`TestApplyLlmSettingsOffToggleButtons`（正常系/例外系/後方互換の3ケース）を新規追加
- `.planning/quick/260610-aaa-v140-review-fixplan/260610-aaa-REVIEW.md` - L-6b/d/e/f/i/j に解消済みマークとコミットハッシュ（892244c, 14d09f5）を追記。L-6a/g/h は L-1 独立プラン（02-04）へ吸収済みである旨を注記

## Decisions Made
- `_require_http_scheme` はリクエスト送信直前（`_post_chat`/`list_models` 冒頭）で呼び、コンストラクタでの eager 検証は行わない（RESEARCH.md A2 の推奨どおり。空 URL や入力途中の値でもプロバイダのインスタンス化自体は失敗させない既存方針と整合）
- `RunPodProvider` は既存の `api_key`/`url` 未設定チェック（早期 raise/return）の後段に `_require_http_scheme` を追加し、例外の優先順位（キー未設定 → URL 未設定 → スキーム不正）を変えなかった
- `ClaudeProvider.list_models` は1ページ分の HTTP 呼び出しを `_fetch_models_page(after_id)` に切り出し、`while True` ループで `has_more`/`last_id` を辿る設計にした（1ページで完結する応答は従来と同一の呼び出し回数・結果になる後方互換）
- `_probe_lm_provider` による重複解消は RESEARCH.md Pitfall 5 のとおり LM Studio ペアのみに限定し、Ollama ペア（`_fetch_ollama_models`/`_test_ollama_connection`）は本プランで変更していない（D-11 の暗黙拡張禁止に従い明示的にスコープ外のまま維持）
- `_update_ocr_buttons_state` 呼び出しは `getattr(self.app, "_update_ocr_buttons_state", None)` + `callable()` チェックの防御的パターンとし、既存の `SimpleNamespace` スタブ（同属性を持たない）を含む既存テストが無改修で通過するようにした

## Deviations from Plan

None - 計画どおり実行した。

## Issues Encountered
None - 計画どおり実行し、既存テストへの回帰は発生しなかった（Pitfall 4 のエラー body 切り詰め横断影響は事前確認済みで既存 assert は全て通過）。

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- V171-OCR-01（L-6 一括解消）完了。残る L-1（producer-consumer 一本化・独立プラン）は 02-04 の担当
- `_require_http_scheme`/`_probe_lm_provider`/`ClaudeProvider._fetch_models_page` は 02-04 から独立して利用可能（相互依存なし）

---
*Phase: 02-ocr*
*Completed: 2026-07-05*

## Self-Check: PASSED

All created/modified files confirmed present on disk. All commit hashes (892244c, 14d09f5, e129a29) confirmed present in git log.
