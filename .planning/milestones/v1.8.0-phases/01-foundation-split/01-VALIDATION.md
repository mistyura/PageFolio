---
phase: 1
slug: foundation-split
status: approved
nyquist_compliant: true
wave_0_complete: true
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
| 01-01/Task1 | 01-01 | 1（W0 安全網） | V180-REFAC-01 | — | N/A | unit（import 回帰） | `pytest tests/test_imports.py -k OcrProviders -q` | ❌ W0（本タスクで追加） | ⬜ pending |
| 01-01/Task2 | 01-01 | 1（W0 安全網） | V180-REFAC-02 | — | N/A | unit（import 回帰） | `pytest tests/test_imports.py -k "LlmConfig or PackageSurface or llm_config" -q` | ✅（部分的に既存・補完） | ⬜ pending |
| 01-02/Task1 | 01-02 | 2 | V180-REFAC-01 | — | N/A | unit（import + 既存回帰） | `pytest tests/test_imports.py -k OcrProviders tests/test_ocr_providers.py -q` | ✅ | ⬜ pending |
| 01-02/Task2 | 01-02 | 2 | V180-ROBUST-02 | T-01-01 | `sensitive_keys()` が現行 10 エントリを部分集合として網羅 | unit + full suite | `pytest tests/test_settings_keyguard.py -q && pytest -q` | ❌（本タスクで追加） | ⬜ pending |
| 01-03/Task1 | 01-03 | 3 | V180-ROBUST-02 | T-01-01 | API キーが設定ファイルへ保存されない | unit | `pytest tests/test_settings_keyguard.py -q` | ✅ | ⬜ pending |
| 01-03/Task2 | 01-03 | 3 | V180-ROBUST-02 | — | キー解決経路の挙動不変 | unit（既存回帰） | `pytest tests/test_provider_ui.py tests/test_ocr.py tests/test_ocr_providers.py -q` | ✅ | ⬜ pending |
| 01-04/Task1 | 01-04 | 3 | V180-REFAC-02 | — | N/A | unit（import + source-scan + MRO 構造） | `pytest tests/test_imports.py -k "LlmConfig or llm_config" tests/test_provider_ui.py -q` | ✅ | ⬜ pending |
| 01-04/Task2 | 01-04 | 3 | V180-ROBUST-02 | — | 環境変数チェックの registry 統合（挙動不変） | unit（既存回帰） | `pytest tests/test_provider_ui.py tests/test_imports.py -q` | ✅ | ⬜ pending |
| 最終ゲート | — | 最終 | 全要件 | — | N/A | full suite | `pytest -q && ruff check . && ruff format --check .` | ✅ | ⬜ pending |

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved（2026-07-14 · gsd-plan-checker VERIFICATION PASSED・全 8 タスクに automated verify を確認）
