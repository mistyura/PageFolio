---
phase: 02
slug: dnd-file-open
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | ast.parse (構文チェック) + 手動検証 |
| **Config file** | none — GUI アプリのため自動テストフレームワークなし |
| **Quick run command** | `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` |
| **Full suite command** | `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick syntax check
- **After every plan wave:** Run full syntax check + manual verification
- **Before `/gsd:verify-work`:** Syntax check green + manual GUI verification
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DND-01, DND-02, DND-03 | syntax + manual | `python -c "import ast; ..."` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pip install tkinterdnd2` — tkinterdnd2 パッケージのインストール確認

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| プレビュー領域に PDF をドロップしてファイルが開かれる | DND-01 | D&D はGUI操作 | エクスプローラーから PDF をプレビュー領域にドロップ → ファイルが開かれることを確認 |
| 複数 PDF 同時ドロップで結合ダイアログ | DND-02 | 複数ファイルD&D | エクスプローラーから複数 PDF を選択してドロップ → MergeOrderDialog が表示されることを確認 |
| ドラッグ中のビジュアルフィードバック | DND-03 | 視覚的確認 | ファイルをプレビュー領域上にドラッグ → 背景色変更+テキスト表示を確認。領域外に移動 → フィードバック消失を確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
