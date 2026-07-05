---
phase: 3
slug: v1-5-0
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/test_v150_regression.py tests/test_pdf_ops.py -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_v150_regression.py tests/test_pdf_ops.py -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| （planner が PLAN.md 確定後に記入） | | | V171-PAGE-01〜03 / V171-TEST-01 | | | unit | `pytest` | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_v150_regression.py` — v1.5.0 新機能（白紙挿入・テキスト透かし・ページ番号・TOC 保持・D&D 指定位置挿入・ショートカット動的読込）の回帰テスト（V171-TEST-01・D-15 で新規ファイル分離）
- 既存 `tests/conftest.py` の共有フィクスチャを流用（新規インフラ導入なし）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 黒塗り/モザイク・トリミングの矩形ドラッグ操作感 | V171-PAGE-02, V171-PAGE-03 | Tkinter Canvas のマウスイベントは pytest で駆動不可（純ロジック部分は自動化） | アプリ起動 → 黒塗りモード ON → 矩形ドラッグ → 連続適用・回転ページでの位置一致を目視確認 |
| 画像透かしの見た目（位置・透過） | V171-PAGE-01 | 描画結果の視覚品質は目視が必要（挿入自体は自動テスト） | アプリ起動 → 画像透かし追加 → プレビューで位置・透過を確認 → Undo で復元確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
