---
phase: 4
slug: ocr
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-15
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（`pyproject.toml` の `[tool.pytest.ini_options]`） |
| **Config file** | `pyproject.toml`（`testpaths = ["tests"]`・`pythonpath = ["src"]`） |
| **Quick run command** | `pytest tests/test_batch_ocr_state.py tests/test_batch_ocr_dialog.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~60 秒（フルスイート・既存 700 件超の回帰込み） |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_batch_ocr_state.py tests/test_batch_ocr_dialog.py -x`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*タスク ID はプランニング完了後に確定。要件→テストのマッピングは RESEARCH.md の Validation Architecture より。*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | V180-BATCH-01 | — | 複数ファイルD&D投入でキューに追加される（フィルタ・重複除外含む） | unit | `pytest tests/test_batch_ocr_state.py::test_enqueue_files -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-BATCH-02 | — | キュー状態遷移（待機→実行中→完了/失敗）と全体進捗集計が正しい | unit | `pytest tests/test_batch_ocr_state.py::test_state_transitions -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-BATCH-03 | — | ファイル単位の fatal 発生時に自動スキップし次ファイルへ進む（fitz は逐次のまま） | integration | `pytest tests/test_batch_ocr_dialog.py::test_file_failure_continues -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-BATCH-04 | — | バッチ中止押下で2階層フラグが同時セットされ、実行中ファイルが停止し次ファイルへ進まない | integration | `pytest tests/test_batch_ocr_dialog.py::test_batch_cancel_stops_all -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | V180-BATCH-05 | — | ファイル横断連結（見出し挿入）+ 入力過大警告（`_confirm_summary_cost` 拡張）が動作する | unit + integration | `pytest tests/test_batch_ocr_dialog.py::test_batch_summary_concat -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_batch_ocr_state.py` — 新規純ロジック層（キュー状態遷移・BatchState 進捗集計）の単体テスト。`tests/test_ocr_pipeline.py`（`PipelineState` の Lock 保護テストパターン）を参考にする
- [ ] `tests/test_batch_ocr_dialog.py` — E2E モックテスト。`tests/test_ocr_engine.py` の `FakeProvider` パターンをそのまま流用し、複数ファイル分の `OCRRunEngine` 生成を検証する
- [ ] Framework install: 不要（pytest は既存導入済み）

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 実ウィンドウでの D&D 投入（tkinterdnd2） | V180-BATCH-01 | tkinterdnd2 の OS ネイティブ D&D イベントはヘッドレステスト不可 | アプリ起動 → メニュー「バッチOCR」→ エクスプローラから複数 PDF をダイアログへドロップ → キューに追加されることを確認 |
| Treeview 行の警告色表示（失敗ファイル） | V180-BATCH-02 | テーマ色の視覚確認は目視が必要 | 失敗ファイルを発生させ、行が `C["WARNING"]` 色で表示されることを両テーマ（dark/light）で確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
