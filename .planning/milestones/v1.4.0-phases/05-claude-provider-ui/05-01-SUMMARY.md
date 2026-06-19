---
phase: 05-claude-provider-ui
plan: "01"
subsystem: ocr-providers
tags: [claude, anthropic, ocr, provider, tdd]
dependency_graph:
  requires: []
  provides:
    - ClaudeProvider（pagefolio/ocr_providers.py）
    - OCRRetryableError（pagefolio/ocr_providers.py）
  affects:
    - pagefolio/ocr.py（build_provider の claude 分岐・Phase 05-02 で実装）
    - pagefolio/ocr_dialog.py（OCRRetryableError 捕捉・Phase 05-03 で実装）
tech_stack:
  added: []
  patterns:
    - urllib.request 直叩き（LMStudioProvider アナログ）
    - TDD RED/GREEN サイクル（pytest + monkeypatch）
    - effort/temperature モデル別防御（EFFORT_MODELS 集合 + 前方互換プレフィックス判定）
key_files:
  created: []
  modified:
    - pagefolio/ocr_providers.py
    - tests/test_ocr_providers.py
decisions:
  - "EFFORT_MODELS に sonnet/opus 系を明示し haiku を除外（D-16）"
  - "list_models はキー未設定時に RECOMMENDED_MODELS を返すフォールバック（D-08）"
  - "429/5xx → OCRRetryableError / 4xx（429除く） → RuntimeError の区別"
  - "content type=='text' 走査で text ブロックを結合（Pitfall 6 対策・content[0] 決め打ち禁止）"
  - "エラーメッセージに self.api_key を含めない（T-05-01 情報漏洩防止）"
metrics:
  duration: "約 25 分"
  completed: "2026-06-06T09:23:00Z"
  tasks_completed: 3
  files_modified: 2
---

# Phase 05 Plan 01: ClaudeProvider・OCRRetryableError 基盤実装 Summary

ClaudeProvider が base64 PNG を Anthropic messages API へ送信し OCR テキストを返す基盤層。effort/temperature のモデル別防御と 429/5xx の OCRRetryableError 変換を実装。

## What Was Built

`pagefolio/ocr_providers.py` に以下を追加した。

### OCRRetryableError

`RuntimeError` のサブクラス。`retry_after: float | None` 属性を保持し、429/5xx リトライ可能を示す専用例外として機能する。後続プラン（05-03 バックオフ層）がこの例外を捕捉して指数バックオフを実装する。

### ClaudeProvider

`OCRProvider` を継承する Anthropic Claude messages API プロバイダ。

- **並列度**: `default_concurrency = 2` / `max_concurrency = 2`（OCR-PERF-03 Claude=2）
- **クラス定数**: `ANTHROPIC_VERSION = "2023-06-01"` / `MESSAGES_ENDPOINT` / `MODELS_ENDPOINT` / `RECOMMENDED_MODELS` / `EFFORT_MODELS`
- **`_supports_effort()`**: `EFFORT_MODELS` 集合 + `"opus"/"sonnet"` 含み `"haiku"` 非含みの前方互換判定（D-16）
- **`_build_payload()`**: effort 対応時は `output_config.effort` のみ付与（temperature なし）、非対応時（haiku）は `temperature` のみ（成功基準7）
- **`ocr_image()`**: 必須ヘッダー（`x-api-key` / `anthropic-version`）付き POST、429/5xx → OCRRetryableError 変換、content `type=="text"` ブロック走査結合（Pitfall 6 対策）
- **`list_models()`**: キー未設定時は静的 RECOMMENDED_MODELS を返す（D-08）、キー設定時は `/v1/models` から `capabilities.image_input.supported` フィルタ

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | ClaudeProvider・OCRRetryableError の失敗テストを追加 | db7fa9d | tests/test_ocr_providers.py |
| 1 GREEN | OCRRetryableError と ClaudeProvider 骨格（effort 判定・payload 構築） | 02e2a25 | pagefolio/ocr_providers.py |
| 2 | ocr_image / list_models テスト追加（429/503/400/混在レスポンス/ヘッダー） | 1dafdf5 | tests/test_ocr_providers.py |
| 3 | ruff・全テスト・構文確認グリーン確定 | 982bd2f | pagefolio/ocr_providers.py, tests/test_ocr_providers.py |

## Test Results

- テスト数: 56 件（既存 36 件 + 新規 20 件）
- `python -m pytest tests/test_ocr_providers.py tests/test_ocr.py -q`: 92 passed
- `ruff check .`: All checks passed

## Deviations from Plan

なし — プラン通りに実行した。

## Threat Model Compliance

| Threat ID | Status | 対応内容 |
|-----------|--------|---------|
| T-05-01 | mitigated | エラーメッセージ・logger 出力に self.api_key を含めない |
| T-05-02 | mitigated | レスポンス本文は body[:500] のみ例外メッセージに含める |
| T-05-03 | accepted | Provider は retryable 例外を送出するのみ。リトライ制御は呼び出し側（05-03）へ委譲 |
| T-05-04 | mitigated | ANTHROPIC_VERSION 定数で全リクエストにヘッダーを付与 |
| T-05-SC | n/a | 本プランは新規 pip 依存ゼロ（urllib のみ） |

## Known Stubs

なし。

## Threat Flags

新規エンドポイント: `https://api.anthropic.com/v1/messages`（POST）および `https://api.anthropic.com/v1/models`（GET）への外部通信。これらはプラン脅威モデルで既に計画済みのトラストバウンダリーである。

## Self-Check: PASSED

- `pagefolio/ocr_providers.py` に `class OCRRetryableError(RuntimeError)` が存在する: 確認済み
- `pagefolio/ocr_providers.py` に `class ClaudeProvider(OCRProvider)` が存在する: 確認済み
- コミット db7fa9d 存在: 確認済み
- コミット 02e2a25 存在: 確認済み
- コミット 1dafdf5 存在: 確認済み
- コミット 982bd2f 存在: 確認済み
