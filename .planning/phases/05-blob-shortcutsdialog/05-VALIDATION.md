---
phase: 5
slug: blob-shortcutsdialog
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-16
updated: 2026-07-16
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
| 05-01 Task1 | 05-01 | 1 | V180-PERF-02 | T-05-01 | thumb_cache 上限コンテナ | unit | `pytest tests/test_thumb_cache.py -x` | ✅ | ✅ green（9 passed） |
| 05-01 Task2 | 05-01 | 1 | V180-PERF-01 | T-05-02 | 可視範囲/優先描画順序純関数 | unit | `pytest tests/test_pagination.py -k "Visible or PrioritizedRender or visible or render_order" -x` | ✅ | ✅ green（14 passed） |
| 05-01 Task3 | 05-01 | 1 | V180-PERF-03 | T-05-02 | selected_pages 全ページ不変条件 | property + unit | `pytest tests/test_selection_invariant.py -x` | ✅ | ✅ green（21 passed） |
| 05-02 Task1 | 05-02 | 2 | V180-PERF-02 | T-05-03 | LruCache(THUMB_CACHE_MAX) 配線 | unit | `pytest tests/test_pagination.py tests/test_viewer.py -x` | ✅ | ✅ green（95 passed） |
| 05-02 Task2 | 05-02 | 2 | V180-PERF-01 | T-05-04, T-05-05 | 可視範囲優先描画 + デバウンス + _thumb_gen 世代ガード | unit | `pytest tests/test_viewer.py tests/test_pagination.py -x` | ✅ | ✅ green（95 passed） |
| 05-03 Task1 | 05-03 | 1 | V180-ROBUST-01 | T-05-06, T-05-07, T-05-08 | Blob `_released`/`__del__` リーク検出 | unit + stress | `pytest tests/test_undo_stress.py -x` | ✅ 既存へ追加（D-14） | ✅ green（7 passed） |
| 05-03 Task2 | 05-03 | 1 | V180-ROBUST-01 | T-05-06, T-05-07, T-05-08 | D-14 3項目回帰（AV衝突mock/二重解放連鎖/tmpdir残留） | unit + stress | `pytest tests/test_undo_stress.py -x` | ✅ 既存へ追加（D-14） | ✅ green（7 passed） |
| 05-04 Task1 | 05-04 | 1 | V180-ROBUST-03 | T-05-10 | WR-01 表示残留修正 | unit | `pytest tests/test_shortcuts_dialog.py -k "wr01 or WR01 or start_capture or restore" -x` | ✅ | ✅ green（2 passed） |
| 05-04 Task2 | 05-04 | 1 | V180-ROBUST-03 | T-05-10, T-05-11 | WR-02 フォーカスガード純関数 | unit | `pytest tests/test_shortcuts_dialog.py -k "wr02 or WR02 or suppress or focus" -x` | ✅ | ✅ green（10 passed） |
| 05-04 Task3 | 05-04 | 1 | V180-ROBUST-03 | T-05-10, T-05-11 | ShortcutsDialog WR-01/WR-02 回帰一式 | unit | `pytest tests/test_shortcuts_dialog.py -x` | ✅ | ✅ green（12 passed） |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*全10タスク COVERED（MISSING/PARTIAL なし）。フルスイート再検証: `pytest` 1078 passed・`ruff check . && ruff format . --check` クリーン（2026-07-16）。*

---

## Wave 0 Requirements

- [x] `tests/test_shortcuts_dialog.py` — WR-01/WR-02 の回帰テスト新設済み（12テスト・全green、05-04 Task3）
- [x] `tests/test_selection_invariant.py` — D-04 プロパティ風テスト新設済み（21テスト・`random.Random(seed)` 駆動、05-01 Task3）
- [x] `tests/test_thumb_cache.py` / `tests/test_pagination.py` — 可視範囲純関数・LRU コンテナのユニットテスト新設済み（05-01 Task1/2）
- [x] `tests/test_shortcuts_dialog.py` 内 — フォーカスガード純関数のユニットテスト（Tk 非依存、`should_suppress_for_focused_input`）新設済み（05-04 Task2）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 大量ページ PDF での実スクロール体感速度 | V180-PERF-01 | 実描画性能は実 Tk ウィンドウ + 実 PDF でのみ確認可能 | 500+ ページの PDF を開きサムネイルペインをスクロールして遅延なく描画されることを確認 |
| ShortcutsDialog のキャプチャ表示切替 | V180-ROBUST-03 | 実際の視覚残留は目視確認が確実 | ShortcutsDialog で行 A のキャプチャ開始→行 B へ切替時に行 A の「キーを押してください」が消えることを確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-07-16

---

## Validation Audit 2026-07-16

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

全10タスクの `<automated>` 検証コマンドを個別再実行し全green確認（COVERED）。監査エージェント（gsd-nyquist-auditor）は不要（ギャップ0件のため Step 3 短絡ルール適用）。
