---
phase: 6
slug: gemini-provider
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-07
audited: 2026-06-09
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (`pythonpath`, ruff/pytest 設定) |
| **Quick run command** | `pytest tests/test_ocr.py tests/test_ocr_providers.py -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ocr.py tests/test_ocr_providers.py -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 01 | W0 | OCR-API-02, OCR-QA-01 | T-06-01 / T-06-02 | x-goog-api-key ヘッダー方式（URL クエリ漏洩なし） | unit | `pytest tests/test_ocr_providers.py -k Gemini -q` | ✅ | ✅ green |
| 06-01-T2 | 01 | 1 | OCR-API-02 | T-06-03 | candidates 空 → RuntimeError (SAFETY ブロック正規化) | unit | `pytest tests/test_ocr_providers.py -k Gemini -q` | ✅ | ✅ green |
| 06-01-T3 | 01 | 1 | OCR-API-02 | T-06-02 / T-06-05 | api_key を settings へ書き込まない（読み取り専用） | unit | `pytest tests/test_ocr.py -k "Gemini or BuildProvider or ResolveApiKey" -q` | ✅ | ✅ green |
| 06-02-T1 | 02 | 2 | OCR-PERF-02, OCR-QA-01 | T-06-06 | del b64 で送信後破棄・上限付きバッファ（maxsize=concurrency+1） | unit | `pytest tests/test_ocr.py::TestProducerConsumerMemory -q` | ✅ | ✅ green |
| 06-02-T2 | 02 | W0 | OCR-PERF-02 | T-06-06 | 同時保持画像数 ≤ concurrency+1 を機械検証 | unit | `pytest tests/test_ocr.py::TestProducerConsumerMemory -q` | ✅ | ✅ green |
| 06-02-T3 | 02 | 2 | OCR-PERF-02 | T-06-07 / T-06-08 | _worker 内 fitz アクセスゼロ・キャンセルデッドロックなし | unit | `pytest tests/test_ocr.py -q` | ✅ | ✅ green |
| 06-03-T1 | 03 | 1 | OCR-PERF-05 | — | N/A | unit | `pytest tests/test_settings_keyguard.py -q` | ✅ | ✅ green |
| 06-03-T2 | 03 | 1 | OCR-QA-01 | T-06-04 | エラー文言に api_key・b64 を含まない | unit | `pytest tests/test_provider_ui.py -q` | ✅ | ✅ green |
| 06-03-T3 | 03 | 1 | OCR-API-02 | — | N/A | unit | `pytest tests/test_provider_ui.py -q` | ✅ | ✅ green |
| 06-04-T1 | 04 | 3 | OCR-PERF-02 | T-06-08 | concurrency 本のワーカー起動・終了シグナル concurrency 本 | unit | `pytest tests/test_ocr.py::TestWorkerConcurrency -q` | ✅ | ✅ green |
| 06-04-T2 | 04 | 3 | OCR-QA-01 | — | _finish_cancelled 2 回呼びで結果二重挿入なし（冪等） | unit | `pytest tests/test_ocr.py::TestFinishIdempotent -q` | ✅ | ✅ green |
| 06-04-T3 | 04 | 3 | OCR-PERF-05, OCR-QA-01 | T-06-02 | GOOGLE_API_KEY 系を _SENSITIVE_KEYS が保護 | unit | `pytest tests/test_settings_keyguard.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_ocr_providers.py` — `GeminiProvider` の payload/レスポンス/list_models/dual env var スタブ（OCR-API-02・OCR-QA-01）
- [x] `tests/test_ocr.py` — producer-consumer メモリ非蓄積リグレッション・`build_provider` gemini 分岐スタブ（OCR-PERF-02・OCR-QA-01）
- [x] `tests/conftest.py` — 既存 `FakeProvider`/`sample_pdf_doc` を再利用（新規追加なし）

*既存テストインフラ（pytest）で大半をカバー。Gemini/逐次レンダリングのテストファイルは既存ファイルへ追記。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 実 Gemini API での OCR 実行（テキスト返却） | OCR-API-02 | 実 API キー・課金・ネットワーク依存のためモック不可 | `GEMINI_API_KEY` を設定し、OCR ダイアログで Gemini を選択して数ページ実行しテキストが返ることを確認 |
| `ocr_scale` ヒント文言の UI 表示 | OCR-PERF-05 | Tkinter 描画の目視確認 | llm_config 設定ダイアログを開き、`ocr_scale` スライダー近傍にトレードオフ説明が常設表示されることを確認 |

*成功基準2（メモリ非蓄積）は自動テストでカバー（Wave 0）。上記のみ手動。*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed

---

## Validation Audit 2026-06-09

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved by auditor | 0 |
| Escalated to manual-only | 0 |
| Pre-existing manual-only | 2 |
| Total automated tests | 377 (全 PASS) |

**根拠:** 06-VERIFICATION.md（passed / 4/4 must-haves verified）と一致。
全 12 タスクに自動検証コマンドが対応し、サンプリング継続性（3 連続タスクに 1 本以上の自動 verify）を満たす。
フルスイート `pytest -q` で 377 passed（2.70s）を確認済み。
