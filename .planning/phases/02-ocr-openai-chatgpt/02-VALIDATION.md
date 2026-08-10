---
phase: 2
slug: ocr-openai-chatgpt
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml`（編集禁止 — 既存設定をそのまま使用） |
| **Quick run command** | `pytest tests/ -q -x` |
| **Full suite command** | `ruff check . && ruff format --check . && pytest` |
| **Estimated runtime** | ~{N} 秒（プランナーが実測値で確定） |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -q -x`
- **After every plan wave:** Run `ruff check . && ruff format --check . && pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** {N} 秒（プランナーが確定）

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {2-01-01} | 01 | 1 | V190-CAT-01 | — | {pending — planner fills} | unit | `{command}` | ⬜ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> このマップは gsd-planner が PLAN.md 生成時に各タスクへ展開する。plan-phase 時点ではスケルトンのみ。

---

## Wave 0 Requirements

- [ ] {pending — planner fills}

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OpenAI 実キーでのモデル一覧取得・vision OCR 実行 | V190-OAI-02/03/11 | 実 API キーと課金が必要（CI 不可） | LLM 設定 UI で OpenAI を選択 → セッション限定キー入力 → モデル一覧取得 → 1ページ OCR 実行 |
| 送信先確認・コスト確認ダイアログの表示 | V190-OAI-04/05/06 | Tkinter モーダルダイアログ（GUI 操作） | OpenAI 選択状態で OCR / バッチ OCR を起動し、送信先ホスト表示とコスト確認が順に出ることを目視確認 |
| フォールバック発動時の送信先再確認 | V190-OAI-07 | 一次プロバイダ失敗を実環境で誘発する必要あり | 一次プロバイダのキーを無効化 → OCR 実行 → OpenAI へフォールバックし送信先確認が再提示されることを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < {N}s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
