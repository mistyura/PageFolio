---
phase: 1
slug: api-llm
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-05
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（`pyproject.toml` `[tool.pytest.ini_options]` で `testpaths = ["tests"]`） |
| **Config file** | `pyproject.toml`（`[tool.pytest.ini_options]`・`[tool.ruff]`） |
| **Quick run command** | `pytest tests/test_ocr.py tests/test_provider_ui.py tests/test_settings_keyguard.py -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | クイック ~10 秒 / フル ~60 秒（707 件ベースライン） |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ocr.py tests/test_provider_ui.py tests/test_settings_keyguard.py -q`
- **After every plan wave:** Run `pytest`（フルスイート・707 件ベースライン）
- **Before `/gsd-verify-work`:** フルスイートグリーン + `ruff check . && ruff format .` クリーン
- **Max feedback latency:** ~60 秒

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD（計画時に確定） | — | — | V171-KEY-01 | T-1-01 | APIキー入力値が `llm_settings` dict に流入しない | unit | `pytest tests/test_provider_ui.py -k "ApiKeyNotInSettings" -x` | ❌ W0 | ⬜ pending |
| TBD | — | — | V171-KEY-01 | T-1-01 | `*_api_key` 系が `settings.json` に非出力（`_SENSITIVE_KEYS` ガード） | unit | `pytest tests/test_settings_keyguard.py -x` | ✅ | ⬜ pending |
| TBD | — | — | V171-KEY-02 | — | 入力値が環境変数より優先（claude） | unit | `pytest tests/test_ocr.py -k "TestResolveApiKey" -x` | ✅ 書き換え要 | ⬜ pending |
| TBD | — | — | V171-KEY-02 | — | 入力値が環境変数より優先（gemini・dual env var 内部順序不変） | unit | `pytest tests/test_ocr.py -k "TestResolveApiKeyGemini" -x` | ✅ 書き換え要 | ⬜ pending |
| TBD | — | — | V171-KEY-02 | — | 両方未設定で `OCRAPIKeyError` raise（claude/gemini） | unit | `pytest tests/test_ocr.py -k "raises or no_env_no_session" -x` | ✅ | ⬜ pending |
| TBD | — | — | V171-KEY-02 / V171-KEY-03 | — | 両方未設定でクラウド OCR 開始時に `messagebox.showerror`（`_check_cloud_api_key`） | unit | `pytest tests/test_provider_ui.py -k "CheckCloudApiKey" -x` | ❌ W0 | ⬜ pending |
| TBD | — | — | V171-KEY-04 | — | RunPod `_resolve_api_key` 3 ケース（入力優先/環境変数フォールバック/raise） | unit | `pytest tests/test_ocr.py -k "TestResolveApiKeyRunPod" -x` | ❌ W0 | ⬜ pending |
| TBD | — | — | V171-KEY-04 | T-1-02 | RunPod セッションキーが `_session_api_keys["runpod"]` に格納（claude スロット誤格納の回帰防止） | unit | `pytest tests/test_provider_ui.py -k "RunpodSessionKeySlot" -x` | ❌ W0 | ⬜ pending |
| TBD | — | — | V171-TEST-02 | — | 全体回帰（既存 707 件 + 新規） | full | `pytest` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task ID 列は gsd-planner が PLAN.md 作成時に確定する。*

---

## Wave 0 Requirements

- [ ] `tests/test_ocr.py::TestResolveApiKeyRunPod` — RunPod 版 `_resolve_api_key` テストクラス新設（claude/gemini と同型: 入力優先へ書き換え後の 3 ケース + os.environ 非書込み確認）
- [ ] `tests/test_provider_ui.py::TestCheckCloudApiKey`（仮称） — `_check_cloud_api_key` の 3 プロバイダ分岐 + messagebox 呼び出し確認（撤去される `TestNeedsSessionKey` の実質的後継）
- [ ] `tests/test_provider_ui.py` — LLMConfigDialog の APIキー欄 → `llm_settings` 非流入 + `_session_api_keys` 格納/クリアの検証クラス新設
- `tests/test_lang_parity.py` は既存の ja/en キー集合一致テストが新規キーを自動カバーするため追加不要

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| APIキー欄のマスク表示（show="*"）と 👁 トグルの実表示 | V171-KEY-01 | Tkinter 実描画の目視確認（ヘッドレスでは描画品質を検証不能） | アプリ起動 → LLM設定ダイアログ → キー入力 → マスク/表示切替を目視 |
| 入力キーによる実クラウド OCR 実行（Claude/Gemini/RunPod） | V171-KEY-02/04 | 実 API キーと課金を伴うため自動化対象外 | 環境変数未設定でダイアログにキー入力 → OCR 実行 → 成功を確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
