---
phase: 06-gemini-provider
plan: "01"
subsystem: ocr-provider
tags: [gemini, ocr, provider, tdd, dual-env-var, api-key-security]
dependency_graph:
  requires: []
  provides:
    - GeminiProvider クラス（pagefolio/ocr_providers.py）
    - build_provider gemini 分岐（pagefolio/ocr.py）
    - _resolve_api_key gemini dual env var 対応（pagefolio/ocr.py）
    - _cloud_providers に gemini 追加（pagefolio/ocr.py）
  affects:
    - Plan 06-02（producer-consumer 逐次レンダリング）
    - Plan 06-03（Gemini UI — LLMConfigDialog・OCRDialog）
tech_stack:
  added: []
  patterns:
    - ClaudeProvider テンプレートを踏襲した Provider 実装
    - dual env var フォールバック（GEMINI_API_KEY → GOOGLE_API_KEY）
    - x-goog-api-key ヘッダー認証（?key= URL クエリ不使用）
    - 関数内 import で循環 import 回避
key_files:
  created: []
  modified:
    - pagefolio/ocr_providers.py
    - pagefolio/ocr.py
    - tests/test_ocr_providers.py
    - tests/test_ocr.py
decisions:
  - "[Phase 06-01]: GeminiProvider は ClaudeProvider と同型テンプレートで実装（D-05）"
  - "[Phase 06-01]: default_concurrency=1 / max_concurrency=1（D-07: Gemini Free Tier 10 RPM）"
  - "[Phase 06-01]: thinkingConfig は generationConfig 直下に配置・thinkingBudget=0（D-09/Pitfall-C）"
  - "[Phase 06-01]: GEMINI_API_KEY 優先・GOOGLE_API_KEY フォールバック dual env var 解決（D-06）"
  - "[Phase 06-01]: x-goog-api-key ヘッダー認証・URL ?key= クエリ不使用（D-05/T-06-01）"
  - "[Phase 06-01]: candidates 空チェック RuntimeError（Pitfall-D/T-06-03）"
metrics:
  duration: "約 6 分"
  completed: "2026-06-07"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
---

# Phase 06 Plan 01: GeminiProvider 中核実装 Summary

**One-liner:** x-goog-api-key ヘッダー認証・thinkingBudget=0・dual env var 解決を備えた GeminiProvider を ClaudeProvider テンプレートで実装し、build_provider / _resolve_api_key / _cloud_providers に gemini 配線を追加。

---

## Objective

OCR-API-02（Gemini で OCR 実行）と OCR-QA-01（Provider モックテスト）の中核実装。
GeminiProvider クラスを ocr_providers.py に追加し、ocr.py に gemini 配線を加えた。
TDD パターンで RED（テスト先行）→ GREEN（実装）の順で実施。

---

## Tasks Completed

| Task | 説明 | Commit | ファイル |
|------|------|--------|---------|
| 1 | GeminiProvider モックテスト追加（RED） | 070ed31 | tests/test_ocr_providers.py, tests/test_ocr.py |
| 2 | GeminiProvider クラス実装（GREEN） | 16b1487 | pagefolio/ocr_providers.py |
| 3 | build_provider・_resolve_api_key・_cloud_providers に gemini 配線 | 86ae460 | pagefolio/ocr.py |

---

## Implementation Details

### GeminiProvider クラス（pagefolio/ocr_providers.py）

- `default_concurrency = 1` / `max_concurrency = 1`（D-07: Gemini Free Tier 10 RPM 対応）
- `RECOMMENDED_MODELS = ["gemini-2.5-flash", "gemini-2.5-pro"]`（D-08: 旧 preview ID 不使用）
- `_build_payload`: `contents[0].parts` に `inline_data`（先頭）+ `text`（次）を配置
  - `generationConfig.thinkingConfig.thinkingBudget = 0`（Pitfall-C: generationConfig 直下）
- `ocr_image`: `x-goog-api-key` ヘッダー認証（URL `?key=` 不使用・D-05/T-06-01）
  - 429/5xx → `OCRRetryableError`、4xx → `RuntimeError`（ClaudeProvider と同型）
- `_parse_response`: `candidates` 空チェック → `promptFeedback.blockReason` 含む RuntimeError（Pitfall-D/T-06-03）
- `list_models`: api_key 未設定時は RECOMMENDED_MODELS・設定時は `generateContent` フィルタ

### gemini 配線（pagefolio/ocr.py）

- `_resolve_api_key("gemini", ...)`: `GEMINI_API_KEY` 優先 → `GOOGLE_API_KEY` フォールバック → セッションキー → `OCRAPIKeyError("GEMINI_API_KEY")`（D-06）
- `build_provider({"ocr_provider": "gemini"}, api_key=...)`: `GeminiProvider` を返す（OCR-API-02）
- `_start_ocr` の `_cloud_providers = {"claude", "gemini"}`: gemini を追加

---

## Test Results

| テストスイート | 結果 |
|--------------|------|
| `pytest tests/test_ocr_providers.py -k Gemini -q` | 22 passed |
| `pytest tests/test_ocr.py -k "Gemini or BuildProvider or ResolveApiKey" -q` | 23 passed |
| `pytest tests/test_ocr_providers.py tests/test_ocr.py -q`（全件・回帰含む） | 146 passed |
| `ruff check .` | クリーン |

---

## Deviations from Plan

なし — プランどおりに実行。

---

## Threat Model Coverage

| Threat ID | 対応状況 |
|-----------|---------|
| T-06-01 | `x-goog-api-key` ヘッダー認証実装・`?key=` URL クエリ不使用を grep/テストで検証 |
| T-06-02 | api_key は os.environ 読み取りのみ・settings への書き込みなしをテストで検証 |
| T-06-03 | candidates 空チェック → RuntimeError 実装・テストで検証 |
| T-06-04 | 例外メッセージに api_key・b64_png を含まない（HTTP エラー本文のみ） |

---

## Known Stubs

なし。

---

## Threat Flags

なし（計画された Gemini API 境界のみ。新規境界の追加なし）。

---

## Self-Check

確認済みファイル:
- `pagefolio/ocr_providers.py` に `class GeminiProvider(OCRProvider)` が存在する: OK
- `pagefolio/ocr.py` に `elif name == "gemini":` が存在する: OK
- `pagefolio/ocr.py` に `if provider_name == "gemini":` が存在する: OK
- `pagefolio/ocr.py` の `_cloud_providers = {"claude", "gemini"}` が存在する: OK
- `tests/test_ocr_providers.py` に `class TestGeminiProviderBuildPayload` が存在する: OK
- `tests/test_ocr.py` に `class TestResolveApiKeyGemini` と `class TestBuildProviderGemini` が存在する: OK

確認済みコミット:
- 070ed31: test(06-01) RED — 存在確認 OK
- 16b1487: feat(06-01) GeminiProvider 実装 — 存在確認 OK
- 86ae460: feat(06-01) gemini 配線 — 存在確認 OK

## Self-Check: PASSED
