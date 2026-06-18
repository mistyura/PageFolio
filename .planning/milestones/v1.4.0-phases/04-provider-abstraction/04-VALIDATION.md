---
phase: 04
slug: provider-abstraction
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-09
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Reconstructed retroactively from phase artifacts (State B) — 04-01〜04-04 SUMMARY / 04-VERIFICATION。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（pytest-cov 7.1.0） |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths=["tests"]`, `pythonpath=["src"]`） |
| **Quick run command** | `python -m pytest tests/test_ocr_providers.py tests/test_ocr.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 秒（380 テスト） |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_ocr_providers.py tests/test_ocr.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File | Status |
|---------|------|------|-------------|-----------|-------------------|------|--------|
| 04-01-T1 | 01 | 1 | OCR-PROV-01 | unit | `pytest tests/test_ocr_providers.py::TestOCRProviderAbstract -q` | test_ocr_providers.py | ✅ green |
| 04-01-T2 | 01 | 1 | OCR-PROV-01 | unit | `pytest tests/test_ocr_providers.py::TestOCRAPIKeyError -q` | test_ocr_providers.py | ✅ green |
| 04-01-T3 | 01 | 1 | OCR-PROV-02 | unit | `pytest tests/test_ocr_providers.py::TestLMStudioProviderBasic -q` | test_ocr_providers.py | ✅ green |
| 04-01-T4 | 01 | 1 | OCR-PROV-02 | unit | `pytest tests/test_ocr_providers.py::TestLMStudioProviderOcrImage -q` | test_ocr_providers.py | ✅ green |
| 04-01-T5 | 01 | 1 | OCR-PROV-02 | unit | `pytest tests/test_ocr_providers.py::TestLMStudioProviderListModels -q` | test_ocr_providers.py | ✅ green |
| 04-02-T1 | 02 | 2 | OCR-PROV-03 | unit | `pytest tests/test_ocr.py::TestRunParallel -q` | test_ocr.py | ✅ green |
| 04-02-T2 | 02 | 2 | OCR-PERF-01 | unit | `pytest tests/test_ocr.py::TestHasEmbeddedText -q` | test_ocr.py | ✅ green |
| 04-02-T3 | 02 | 2 | OCR-PROV-03 | unit | `pytest tests/test_ocr.py::TestBuildProvider -q` | test_ocr.py | ✅ green |
| 04-03-T1 | 03 | 3 | OCR-PERF-01 | unit | `pytest tests/test_ocr.py::TestOcrProviderDefault -q` | test_ocr.py | ✅ green |
| 04-04-CR01 | 04 | 4 | OCR-PROV-02 | unit | `pytest tests/test_ocr.py::TestStartOcrUnknownProvider -q` | test_ocr.py | ✅ green |
| 04-04-CR02 | 04 | 4 | OCR-PROV-02 | unit | `pytest tests/test_ocr.py::TestOcrDialogOnRun -q` | test_ocr.py | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ダイアログでモデルを変更して「読み取り実行」を押すと LM Studio に送信される `model` フィールドがダイアログ選択値と一致する | OCR-PROV-02 | HTTP リクエスト内容の確認は実際の LM Studio サーバへの接続が必要 | LM Studio 起動・モデル一覧取得・別モデル選択・実行・LM Studio ログで model フィールドを確認 |
| タイムアウト設定変更後に応答の遅い LM Studio に OCR 実行した際、エラーメッセージの秒数と実際待機時間が一致する | OCR-PROV-02 | 実際の HTTP タイムアウト挙動は実環境での動作確認が必要 | タイムアウト 10 秒に設定・接続断 LM Studio に対して実行・表示秒数と実待機時間を比較 |

---

## Validation Audit 2026-06-09

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved (automated) | 3 |
| Escalated (manual-only) | 0 |

**Gap 1 (CR-01):** `TestStartOcrUnknownProvider` — `_start_ocr` が未対応プロバイダ名の `ValueError` を捕捉して `showerror + return` することを自動検証
**Gap 2 (CR-02):** `TestOcrDialogOnRun` — `_on_run` が `model_var`/`max_tokens_var`/`temperature_var` の live 値で `LMStudioProvider` を再生成することを自動検証
**Gap 3 (04-03):** `TestOcrProviderDefault` — `ocr_provider` デフォルト値が `"off"` であることを自動検証
