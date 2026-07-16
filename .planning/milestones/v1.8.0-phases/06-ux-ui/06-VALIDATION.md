---
phase: 6
slug: ux-ui
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-16
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1（`requirements.txt`） |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths = ["tests"]`） |
| **Quick run command** | `pytest -x`（プラン確定後にフェーズ対象テストへ絞り込み） |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 秒（フルスイート・既存回帰込み） |

---

## Sampling Rate

- **After every task commit:** Run `pytest -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-01-01 | 01 | 1 | V180-QA-02 | — | N/A | unit | `pytest` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*（プラン確定後に validate-phase / executor がタスク単位で更新する。上記はシード行。）*

---

## Wave 0 Requirements

- [ ] トースト状態管理の単体テスト stub（V180-QA-02 — Tk 非依存の純ロジック部分）
- [ ] フォントハードコード検出のソーススキャンテスト stub（V180-QA-03 / D-13 — `test_source_keyguard.py` 前例踏襲）
- [ ] insert→undo→redo→undo 往復回帰テスト stub（D-17 — `deferred-items.md` の再現コード流用）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| トーストの表示位置・視覚確認（右下オーバーレイ・テーマ追従） | V180-QA-02 | Tkinter の描画結果は目視確認が必要 | アプリ起動→保存失敗を誘発（読み取り専用パス等）→右下トースト表示・再試行ボタン・✕ボタンを確認 |
| スクロールホイール動作の是正確認 | V180-QA-03 | 実ホイールイベントの体感確認 | 是正対象ダイアログを開きホイールスクロールを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
