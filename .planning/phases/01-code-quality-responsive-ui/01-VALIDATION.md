---
phase: 01
slug: code-quality-responsive-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | ast.parse (構文チェック) + 手動検証 |
| **Config file** | none — GUI アプリのため自動テストフレームワークなし |
| **Quick run command** | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` |
| **Full suite command** | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -c "import ast; ast.parse(open('pagefolio.py').read())"`
- **After every plan wave:** Run full syntax check + manual verification
- **Before `/gsd:verify-work`:** Syntax check green + manual GUI verification
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | QUAL-01 | syntax + manual | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` | N/A | ⬜ pending |
| 01-02-01 | 02 | 1 | UI-01, UI-02 | syntax + manual | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` | N/A | ⬜ pending |
| 01-02-02 | 02 | 1 | UI-03 | syntax + manual | `python -c "import ast; ast.parse(open('pagefolio.py').read())"` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. GUI アプリのため自動テストフレームワークの追加は不要。構文チェックのみで十分。

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ウィンドウリサイズで右パネルが見切れない | UI-01 | GUI レイアウトの視覚確認が必要 | アプリ起動 → ウィンドウを様々なサイズにリサイズ → 右ツールパネルが常に表示されることを確認 |
| PanedWindow sash ドラッグでパネル比率変更 | UI-02 | ドラッグ操作の確認が必要 | sash（境界線）をドラッグ → 3パネル全ての幅が変更されることを確認 |
| 極端に狭いウィンドウでサムネイルパネルが消えない | UI-03 | 極端なサイズでの視覚確認が必要 | ウィンドウを最小サイズ(800x600)まで縮小 → サムネイルパネルが表示されていることを確認 |
| 既存機能の動作確認 | QUAL-01 | 全機能の結合テストが必要 | 回転・削除・トリミング・結合・D&D・Undo/Redo を各1回実行 → 正常動作を確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
