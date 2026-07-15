---
phase: 5
slug: blob-shortcutsdialog
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-16
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1（`requirements.txt`） |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths = ["tests"]`） |
| **Quick run command** | `pytest tests/test_pagination.py tests/test_viewer.py tests/test_undo_stress.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 秒（フルスイート・既存回帰込み） |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_pagination.py tests/test_viewer.py tests/test_undo_stress.py tests/test_shortcuts_dialog.py tests/test_selection_invariant.py -x`（存在する該当ファイルのみ）
- **After every plan wave:** Run `pytest`（全件）
- **Before `/gsd-verify-work`:** Full suite must be green + `ruff check . && ruff format .`
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | V180-PERF-01 | — | N/A | unit | `pytest tests/test_pagination.py -k visible -x`（新設関数名は計画時確定） | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-PERF-02 | — | N/A | unit | `pytest tests/test_pagination.py -k lru -x`（配置先次第でファイル名変更あり） | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-PERF-03 | — | N/A | property + unit | `pytest tests/test_selection_invariant.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-ROBUST-01 | — | N/A | unit + stress | `pytest tests/test_undo_stress.py -x` | ✅ 既存へ追加（D-14） | ⬜ pending |
| TBD | TBD | TBD | V180-ROBUST-03 | — | N/A | unit | `pytest tests/test_shortcuts_dialog.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_shortcuts_dialog.py` — WR-01/WR-02 の回帰テスト（`ShortcutsDialog` 専用テストは未存在。実 Tk ウィジェット依存部のハーネス方式は計画時判断）
- [ ] `tests/test_selection_invariant.py` — D-04 プロパティ風テスト（`random.Random(seed)` 駆動・純関数のみで 500+ ページ相当をシミュレート）
- [ ] `pagination.py`（または新規 LRU モジュール）への可視範囲純関数・LRU コンテナのユニットテスト（配置先確定後に対応ファイルへ追加）
- [ ] フォーカスガード純関数のユニットテスト（Tk 非依存）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 大量ページ PDF での実スクロール体感速度 | V180-PERF-01 | 実描画性能は実 Tk ウィンドウ + 実 PDF でのみ確認可能 | 500+ ページの PDF を開きサムネイルペインをスクロールして遅延なく描画されることを確認 |
| ShortcutsDialog のキャプチャ表示切替 | V180-ROBUST-03 | 実際の視覚残留は目視確認が確実 | ShortcutsDialog で行 A のキャプチャ開始→行 B へ切替時に行 A の「キーを押してください」が消えることを確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
