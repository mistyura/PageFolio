---
phase: 3
slug: ocr-e2e
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-15
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3（導入済み） |
| **Config file** | `pyproject.toml`（既存） |
| **Quick run command** | `pytest tests/test_ocr_engine.py -x` |
| **Full suite command** | `pytest`（ベースライン: 987 件グリーン・36.21秒） |
| **Estimated runtime** | ~37 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ocr_engine.py -x`
- **After every plan wave:** Run `pytest` + `ruff check . && ruff format .`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | V180-REFAC-03 | — | N/A — `OCRRunEngine` 単独 import + `on_success` コールバック | unit | `pytest tests/test_ocr_engine.py::TestOCRRunEngineUnit -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-REFAC-03 | — | N/A — `OCRDialog` 委譲後の回帰維持 | integration | `pytest tests/test_provider_ui.py tests/test_ocr_fallback.py tests/test_ocr.py -x` | ✅ | ⬜ pending |
| TBD | TBD | TBD | V180-QA-01 | — | N/A — 複数ページ正常系の全結果返却 | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_all_pages_success -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-QA-01 | — | N/A — ページエラー混在でも取りこぼしなし | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_partial_page_errors -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-QA-01 | — | N/A — キャンセルの有限時間反映 | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_cancel_stops_processing -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-QA-01 | — | N/A — サーキットブレーカーで残ページ API スキップ | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_circuit_breaker_stops_calls -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-QA-01 | — | N/A — OCR→サマリ一気通貫成功 | e2e (mock) | `pytest tests/test_ocr_engine.py::TestOCRRunEngineE2E::test_ocr_then_summary_flow -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task ID / Plan / Wave はプラン確定後に PLAN.md から転記する。*

---

## Wave 0 Requirements

- [ ] `tests/test_ocr_engine.py` — 新設。`OCRRunEngine` 単体テスト（D-16）+ E2E モックシナリオ（D-13/D-15）を同居させる
- [ ] `FakeProvider` の `complete_text_ex`/`supports_text_prompt` 拡張 — `tests/test_ocr_engine.py` 内の1クラスに限り拡張（他ファイルの `FakeProvider` は変更しない、D-14 遵守）
- [ ] resume 判断ロジック（`_pending_pages()`/`_can_resume()` 等）の既存回帰確認 — D-10 により `OCRRunEngine` は resume を知らない前提。分割後に既存テストが通ることを確認（新規テストファイル不要）
- [ ] フレームワークインストール不要（pytest 9.0.3 導入済み）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 単一ファイル OCR の実行・進捗・キャンセル・リトライの GUI 動作 | V180-REFAC-03 | Tkinter GUI はヘッドレス pytest で駆動不可（既存方針どおり間接テストのみ） | アプリ起動 → PDF を開く → OCR 実行 → 進捗表示・キャンセル・リトライを目視確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
