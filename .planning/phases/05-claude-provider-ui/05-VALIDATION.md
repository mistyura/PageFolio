---
phase: 05
slug: claude-provider-ui
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-07
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Reconstructed retroactively from phase artifacts (State B) — 05-01〜05-05 SUMMARY / 05-UAT。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（pytest-cov 7.1.0） |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths=["tests"]`, `pythonpath=["src"]`） |
| **Quick run command** | `python -m pytest tests/test_ocr_providers.py tests/test_ocr.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 秒（329 テスト） |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_ocr_providers.py tests/test_ocr.py -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 秒

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01 | 01 | 1 | OCR-PERF-03 | T-05-04 | Claude 並列度を 2 に固定し 429 を抑制 | unit | `pytest tests/test_ocr_providers.py::TestClaudeProvider -q` | ✅ | ✅ green |
| 05-01 | 01 | 1 | OCR-UI-04 | T-05-15 | effort 非対応モデル(haiku)に effort を送らず temperature を送る | unit | `pytest tests/test_ocr_providers.py -k effort -q` | ✅ | ✅ green |
| 05-01 | 01 | 1 | OCR-PERF-04 | T-05-03 | 429/5xx を OCRRetryableError に変換し retry_after を保持 | unit | `pytest tests/test_ocr_providers.py -k "429 or 503 or retryable" -q` | ✅ | ✅ green |
| 05-01 | 01 | 1 | OCR-SEC-01 | T-05-01/02 | エラー・ログにキー値・本文全体を含めない | unit | `pytest tests/test_ocr_providers.py -k "http_error or message" -q` | ✅ | ✅ green |
| 05-02 | 02 | 1 | OCR-SEC-01 | T-05-05/06 | `_SENSITIVE_KEYS` ガードで API キーを settings.json に書かない | unit | `pytest tests/test_settings_keyguard.py -q` | ✅ | ✅ green |
| 05-03 | 03 | 2 | OCR-SEC-02 | T-05-11 | キー未解決時 OCRAPIKeyError を送出し外部送信しない | unit | `pytest tests/test_ocr.py::TestResolveApiKey -q` | ✅ | ✅ green |
| 05-03 | 03 | 2 | OCR-SEC-03 | T-05-08/09 | キーは引数注入のみ・os.environ/settings に書かない | unit | `pytest tests/test_ocr.py -k "os_environ_not_written or not_polluted or injected" -q` | ✅ | ✅ green |
| 05-03 | 03 | 2 | OCR-PERF-04 | T-05-10 | 指数バックオフ最大3回・Retry-After 優先・無限ループ無し | unit | `pytest tests/test_ocr.py -k "retry or backoff or waiting" -q` | ✅ | ✅ green |
| 05-04 | 04 | 3 | OCR-UI-01 | T-05-15 | `_model_supports_effort` でモデル別 effort/temperature 切替(D-16) | unit | `pytest tests/test_provider_ui.py::TestModelSupportsEffort -q` | ✅ | ✅ green |
| 05-04 | 04 | 3 | OCR-UI-02 | T-05-14 | off 時/doc 未開時に OCR ボタンを disabled 化 | unit | `pytest tests/test_provider_ui.py::TestUpdateOcrButtonsState -q` | ✅ | ✅ green |
| 05-04 | 04 | 3 | OCR-SEC-01 | T-05-12/13 | `_apply` で api_key 系を llm_settings に格納しない | unit | `pytest tests/test_ocr.py::*apply* -k "not_leak or does_not_leak" -q` | ✅ | ✅ green |
| 05-05 | 05 | 3 | OCR-UI-03 | T-05-18 | クラウド時のみコスト確認(host/page/cost/プライバシー)・キャンセル可 | unit | `pytest tests/test_provider_ui.py -k "ConfirmCost or EstimateCost or IsCloudProvider" -q` | ✅ | ✅ green |
| 05-05 | 05 | 3 | OCR-SEC-03 | T-05-16/17 | env 未設定時のみマスク入力欄・`_session_api_keys` 限定格納 | unit | `pytest tests/test_provider_ui.py::TestNeedsSessionKey -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.
（pytest + pyproject.toml は既設。新規フレームワーク導入なし。retroactive 監査で `tests/test_provider_ui.py` を追加し UI ロジック層のギャップを充足。）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| プロバイダ DD の実描画・欄の pack/pack_forget 切替の見た目 | OCR-UI-01 | Tk ウィジェットの実レンダリングは headless で再現困難。ロジック層(`_model_supports_effort`)は自動化済み | `python pagefolio.py` → LLM 設定 → claude 選択で URL 欄が消え claude モデル欄表示・opus/sonnet で effort 欄・haiku で temperature 欄 |
| マスク入力欄(show="*")の実表示・コスト確認ダイアログの実描画 | OCR-UI-03 / OCR-SEC-03 | messagebox/Entry の実描画は GUI 依存。判定ロジックは自動化済み | `python pagefolio.py` → claude で OCR 実行 → env 未設定でマスク欄表示・コスト確認の3要素表示・キャンセルで中止 |

*上記は UAT（05-UAT.md）で 11/11 pass 済み（2026-06-07）。ロジック層はすべて自動回帰テスト化済み。*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < ~5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-07

---

## Validation Audit 2026-06-07

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

監査詳細: OCR-UI-01/02/03（UI ロジック層）の自動テスト欠落を検出。gsd-nyquist-auditor が `tests/test_provider_ui.py`（29 テスト）を追加して充足。既存 287 + 29 = 329 テスト全件 green、`ruff check .` クリア。実装ファイルへの変更なし。
