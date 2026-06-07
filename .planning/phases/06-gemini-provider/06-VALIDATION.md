---
phase: 6
slug: gemini-provider
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
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
| {N}-01-01 | 01 | 1 | REQ-{XX} | T-{N}-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*プランナーが各タスク確定時にこの表を充足する。Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ocr_providers.py` — `GeminiProvider` の payload/レスポンス/list_models/dual env var スタブ（OCR-API-02・OCR-QA-01）
- [ ] `tests/test_ocr.py` — producer-consumer メモリ非蓄積リグレッション・`build_provider` gemini 分岐スタブ（OCR-PERF-02・OCR-QA-01）
- [ ] `tests/conftest.py` — 既存 `FakeProvider`/`sample_pdf_doc` を再利用（新規追加が必要なら補完）

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
