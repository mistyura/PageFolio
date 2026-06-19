---
phase: 4
slug: ai-c
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-19
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 由来: `04-RESEARCH.md` の `## Validation Architecture`（HIGH 信頼度・実コード検証済）。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（+ pytest-cov 7.1.0） |
| **Config file** | pyproject.toml（`pythonpath`、`tests/**` で S101 除外）※編集禁止 |
| **Quick run command** | `python -m pytest tests/test_md_render.py tests/test_provider_ui.py tests/test_lang_parity.py -x -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | フル ~数十秒（現行 582 件ベースライン） |

---

## Sampling Rate

- **After every task commit:** Run quick run command（上表）
- **After every plan wave:** Run `python -m pytest -q`（フルスイート）
- **Before `/gsd-verify-work`:** フルスイート緑（**582 件**ベースライン維持）+ `ruff check . && ruff format .` 通過
- **Max feedback latency:** ~30 秒

---

## Per-Task Verification Map

> タスク ID は gsd-planner が確定する。下表は要件→テストの対応（研究由来）。プランナーは各タスクの `<automated>` verify をこの対応に紐付けること。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-0X-0X | TBD | 0 | V16-AI-01 | — | Markdown 行種別（H1/H2/箇条書き/コード）を正しく分類 | unit | `python -m pytest tests/test_md_render.py -q` | ❌ W0 | ⬜ pending |
| 04-0X-0X | TBD | 0 | V16-AI-01 | — | インライン span（`**bold**`/`` `code` ``）を抽出 | unit | `python -m pytest tests/test_md_render.py -q` | ❌ W0 | ⬜ pending |
| 04-0X-0X | TBD | 1 | V16-AI-02 | — | `resolve_ocr_prompt` がプロバイダ別テンプレを返す | unit | `python -m pytest tests/test_provider_ui.py -q` | ✅ 既存拡張 | ⬜ pending |
| 04-0X-0X | TBD | 1 | V16-AI-02 / 成功基準3 | T-04-IDISC | カスタムプロンプトが provider テンプレを上書きする（後方互換） | unit | `python -m pytest tests/test_provider_ui.py -q` | ✅ 既存拡張 | ⬜ pending |
| 04-0X-0X | TBD | 1 | V16-AI-02 | — | LMStudio/Tesseract は汎用プロンプトにフォールバック | unit | `python -m pytest tests/test_provider_ui.py -q` | ✅ 既存拡張 | ⬜ pending |
| 04-0X-0X | TBD | 1 | 回帰 | — | ja/en LANG キー対称性（新規文言追加時） | unit | `python -m pytest tests/test_lang_parity.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_md_render.py` — `parse_markdown` の行種別・インライン span を検証（V16-AI-01・新規）
- [ ] `tests/test_provider_ui.py` に `resolve_ocr_prompt` テスト群を追加（V16-AI-02・既存ファイル拡張）
- [ ] フレームワーク install: 不要（pytest 導入済み）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| プロバイダ別プロンプト文言の OCR 出力品質向上効果（Claude=XML / Gemini=明示指示） | V16-AI-02 | 文言効果は [ASSUMED]（研究 A1/A2/A4）。自動テストは「テンプレが返ること」までしか担保できず、品質向上は実 API での A/B 比較が必要 | 実 API（または実機相当）で同一ページを既定 vs プロバイダ別テンプレで OCR し、出力の構造化度・読みやすさを目視比較・記録 |
| Markdown 整形表示の見た目（見出し/箇条書きがプレーンより読みやすいこと） | V16-AI-01 | tk.Text のタグ描画は GUI 目視確認が確実 | OCRDialog で `markdown` プリセット出力を表示し、見出し・箇条書き・コードがスタイル付与され可読であることを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references（`tests/test_md_render.py`）
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
