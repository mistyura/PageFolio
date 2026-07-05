---
phase: 2
slug: ocr
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-05
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（pytest-cov 7.1.0） |
| **Config file** | pyproject.toml |
| **Quick run command** | 各タスクの `<automated>` コマンド（対象テストファイル限定 `pytest <targets> -q`） |
| **Full suite command** | `pytest -q`（+ wave 境界で `ruff check . && ruff format --check .`） |
| **Estimated runtime** | フルスイート ~21 秒（728 tests・2026-07-05 実測）／対象限定 ~2〜5 秒 |

---

## Sampling Rate

- **After every task commit:** Run 当該タスクの `<automated>` コマンド（下表参照）
- **After every plan wave:** Run `pytest -q` + `ruff check . && ruff format --check .`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | V171-OCR-03 | — | N/A | unit | `pytest tests/test_plugins.py -q` | ✅ | ⬜ pending |
| 2-01-02 | 01 | 1 | V171-OCR-03 | — | N/A | unit | `pytest tests/test_plugins.py tests/test_ocr.py tests/test_provider_ui.py -q` | ✅ | ⬜ pending |
| 2-02-01 | 02 | 2 | V171-OCR-02 | — | N/A | unit | `pytest tests/test_ocr_providers.py -q` | ✅ | ⬜ pending |
| 2-02-02 | 02 | 2 | V171-OCR-02 | — | N/A | unit | `pytest tests/test_provider_ui.py tests/test_lang_parity.py -q` | ✅ | ⬜ pending |
| 2-03-01 | 03 | 3 | V171-OCR-01 | T-2-01 / T-2-02 / T-2-03 | http/https 以外の URL スキームを RuntimeError で拒否・Gemini モデル名をパスセグメントとしてエスケープ・HTTP エラー body を一定長で切り詰め | unit | `pytest tests/test_ocr_providers.py -q` | ✅ | ⬜ pending |
| 2-03-02 | 03 | 3 | V171-OCR-01 | — | N/A | unit | `pytest tests/test_provider_ui.py -q` | ✅ | ⬜ pending |
| 2-04-01 | 04 | 4 | V171-OCR-04 | — | N/A | unit | `pytest tests/test_ocr_pipeline.py -q` | ❌ W0（TDD タスク内で新設） | ⬜ pending |
| 2-04-02 | 04 | 4 | V171-OCR-04 | — | N/A | unit | `pytest tests/test_ocr.py tests/test_provider_ui.py tests/test_ocr_pipeline.py -q` | ✅ | ⬜ pending |
| 2-04-03 | 04 | 4 | V171-OCR-04 | — | N/A | integration | `pytest tests/test_ocr.py tests/test_ocr_pipeline.py tests/test_ocr_providers.py tests/test_provider_ui.py tests/test_plugins.py -q && pytest -q && ruff check . && ruff format --check .` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

- pytest 9.0.2 は導入済み（`pyproject.toml` 設定・`tests/conftest.py` フィクスチャあり）
- `tests/test_ocr_pipeline.py` は Wave 0 ではなく Task 2-04-01（`tdd="true"`）がタスク内で新設する（TDD: テスト先行）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tesseract 言語フォールバック時の非モーダル注記が OCRDialog 上に表示される | V171-OCR-02 | Tk ウィジェットの実表示（配置・視認性）は headless テストで完全再現不可（文言生成ロジック自体は `tests/test_provider_ui.py` で自動検証） | 指定言語パックが欠如した環境で `tesseract_lang` に未導入言語を設定して OCR を実行し、ダイアログ内にフォールバック注記が表示されることを目視確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references（test_ocr_pipeline.py は TDD タスク 2-04-01 内で新設）
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-05
