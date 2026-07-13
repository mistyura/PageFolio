---
phase: 1
slug: foundation-split
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（`pyproject.toml` の `[tool.pytest.ini_options]`） |
| **Config file** | `pyproject.toml`（`testpaths = ["tests"]`） |
| **Quick run command** | `pytest tests/test_imports.py tests/test_ocr_providers.py tests/test_settings_keyguard.py -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | quick ~10 秒 / full ~60 秒 |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_imports.py tests/test_ocr_providers.py tests/test_settings_keyguard.py -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green + `ruff check . && ruff format --check .` クリーン
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD（プランニング後に確定） | — | 0 | V180-REFAC-01 | — | N/A | unit（import 回帰） | `pytest tests/test_imports.py -k OcrProviders -x` | ❌ W0 | ⬜ pending |
| TBD | — | — | V180-REFAC-01 | — | N/A | unit（既存回帰） | `pytest tests/test_ocr_providers.py -q` | ✅ | ⬜ pending |
| TBD | — | — | V180-REFAC-02 | — | N/A | unit（import 回帰） | `pytest tests/test_imports.py -k LlmConfig -x` | ✅（部分的に既存） | ⬜ pending |
| TBD | — | — | V180-REFAC-02 | — | N/A | unit（既存回帰） | `pytest tests/test_provider_ui.py -q` | ✅ | ⬜ pending |
| TBD | — | 0 | V180-ROBUST-02 | — | API キーが設定ファイルへ保存されない | unit | `pytest tests/test_settings_keyguard.py -k SensitiveKeysConstant -x` | ❌ W0 | ⬜ pending |
| TBD | — | — | V180-ROBUST-02 | — | keyguard 3 経路の非保存維持 | unit（既存回帰） | `pytest tests/test_settings_keyguard.py -q` | ✅ | ⬜ pending |
| TBD | — | 最終 | 全要件 | — | N/A | full suite | `pytest -q && ruff check . && ruff format --check .` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_imports.py` — `ocr_providers` パッケージ向けの後方互換 import テストクラスを追加（全 17 シンボル。分割**前**に追加して現行コードで緑を確認してから分割する — CONTEXT.md D-09/D-11 必達）
- [ ] `tests/test_settings_keyguard.py` — `sensitive_keys()` 生成結果が現行 10 エントリを部分集合として含むことを検証するテストを追加
- [ ] Framework install: 不要（pytest 導入済み）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LLM 設定ダイアログの表示・操作 | V180-REFAC-02 | Tkinter GUI の実表示は自動化対象外（既存テストは headless で import/ロジックのみ検証） | `python pagefolio.py` 起動 → 「⚙ LLM設定」を開き、プロバイダ切替・モデル一覧取得・適用が分割前と同一挙動であることを目視確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
