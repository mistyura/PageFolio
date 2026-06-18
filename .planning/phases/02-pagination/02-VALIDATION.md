---
phase: 2
slug: pagination
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 詳細な不変条件・境界値の根拠は `02-RESEARCH.md` の `## Validation Architecture`（L370-454）を参照。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2（+ pytest-cov 7.1.0） |
| **Config file** | `pyproject.toml`（`[tool.pytest.ini_options]` testpaths=["tests"]） |
| **Quick run command** | `pytest tests/test_pagination.py -x` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 秒 |

> 窓計算・local↔global 変換・クランプ・窓追従は Tkinter 非依存の純関数（新規 `pagefolio/pagination.py`）として切り出し、`tests/test_pagination.py` で `types.SimpleNamespace` スタブ＋境界値テストによりヘッドレス検証する（既存 `tests/test_viewer.py` の `_make_stub` 作法を踏襲）。ウィジェット描画そのものは検証対象外。

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_pagination.py -x`（純ロジックは高速・全数即時）
- **After every plan wave:** Run `pytest`（全スイート — 既存 test_viewer / test_pdf_ops との回帰確認）
- **Before `/gsd-verify-work`:** `pytest` 全緑 ＋ `ruff check . && ruff format .` 通過
- **Max feedback latency:** 15 秒

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | V16-UI-03 (SC1 / D-10) | — | N/A | unit | `pytest tests/test_pagination.py::TestWindowBounds -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | V16-UI-03 (SC3 / SC4 / D-06 / D-07 / D-11 / D-09) | — | N/A | unit | `pytest tests/test_pagination.py -x`（TestIndexConvert / TestDndIndexConvert / TestSelectionAcrossWindows / TestWindowFollow / TestClampWindowStart / TestNavState / TestWindowLabel） | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 2 | V16-UI-03 (SC2 / D-04 / D-05) | T-2-01 | 表示件数を 10〜100 にクランプ（非数値・範囲外を拒否） | unit | `pytest tests/test_pagination.py::TestPageSizePersist -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 2 | V16-UI-03 (SC1 / D-07 / Pitfall 1) | — | N/A | unit | `pytest tests/test_pagination.py -x`（窓範囲描画・選択 enumerate の global 変換） | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 3 | V16-UI-03 (D-01 / D-02 / D-03 / D-09) | T-2-01 | `ttk.Spinbox` `state="readonly"` で範囲外入力を構造的に防止 | unit+manual | `pytest tests/test_pagination.py::TestNavState -x` ＋ 人手UAT | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 3 | V16-UI-03 (SC3 / D-06 / D-11 / Pitfall 2,4,5) | — | D&D dest を `min(to_global(...), len(doc))` でクランプ | unit+manual | `pytest tests/test_pagination.py::TestDndIndexConvert -x` ＋ 人手UAT | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*File Exists: ❌ W0 = テスト基盤（test_pagination.py）は Wave 1 / 02-01 で新規作成される。*

---

## Wave 0 Requirements

- [ ] `tests/test_pagination.py` — 新規作成（02-01 / Wave 1）。7 テストクラス（TestWindowBounds / TestIndexConvert / TestDndIndexConvert / TestSelectionAcrossWindows / TestWindowFollow / TestClampWindowStart / TestNavState、加えて TestPageSizePersist / TestWindowLabel）で窓計算・local↔global 変換・D&D換算・選択保持・窓追従・クランプ・ナビ状態を検証。covers V16-UI-03 / D-06〜D-11。
- [ ] `tests/conftest.py` — 多ページ doc フィクスチャ（例 47 ページ）を追加し境界値テストを書きやすくする（02-01）。

*フレームワーク install は不要（pytest 既存）。基盤は 02-01（Wave 1）が作る。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 窓往復で `thumb_cache` が非クリアのまま高速描画される（A1 / Pitfall 2） | V16-UI-03 | キャッシュ挙動はレンダリング実機でないと体感確認できない | 大量ページ PDF を開き、前/次窓を往復してサムネイル再描画が即時（再生成なし）か確認 |
| 窓またぎ D&D で意図したページが正しい全ページ位置へ移動（A2 / SC3） | V16-UI-03 (S3) | D&D ドラッグ操作は GUI 実機操作が必要 | 窓2 を表示中に選択ページを別位置へドラッグ → `current_page`/順序が全ページインデックスと整合するか確認 |
| ページング表示中の複数選択でページ操作（削除・回転）が選択どおり適用（SC4） | V16-UI-03 (S4) | 複数選択 + 操作の連携は実機 UI で確認 | 窓をまたいで複数選択 → 削除/回転 → 選択どおり適用され `selected_pages` が全ページ index を指すか確認 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies（全 auto タスクに pytest 系 `<automated>`）
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references（test_pagination.py / 47p フィクスチャを 02-01 が作成）
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-18
