---
phase: 2
slug: pagination
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-18
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> 詳細な不変条件・境界値の根拠は `02-RESEARCH.md` の `## Validation Architecture` を参照。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml`（`pytest` 設定 + `pythonpath`） |
| **Quick run command** | `pytest tests/test_viewer.py -q` |
| **Full suite command** | `pytest` |
| **Estimated runtime** | ~15 秒 |

> 窓計算・local↔global 変換は Tkinter 非依存の純関数として切り出し、`tests/test_viewer.py` の `_make_stub`（SimpleNamespace スタブ）方式でヘッドレス検証する。

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_viewer.py -q`
- **After every plan wave:** Run `pytest`
- **Before `/gsd-verify-work`:** Full suite must be green（`ruff check . && ruff format .` も通すこと）
- **Max feedback latency:** 15 秒

---

## Per-Task Verification Map

> プランナーが各 PLAN.md のタスクに合わせて埋める。新規の変換ヘルパー（`window_bounds` / `to_global` / `to_local` / `window_for_page` / `clamp_window_start` / `window_label` / `window_nav_state`）は純ロジック unit テストで全境界値・往復不変条件を検証する。

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {2-XX-XX} | {XX} | {W} | V16-UI-03 | — / T-2-01 | 件数入力を 10〜100 にクランプ | unit | `pytest tests/test_viewer.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_viewer.py` — 窓計算・local↔global 変換・窓追従（D-11）・端数最終窓の純ロジックテストを追加（既存ファイルへ追記、`_make_stub` 流用）
- [ ] 既存 `tests/conftest.py` のフィクスチャを流用（新規共有フィクスチャは原則不要）

*pytest 基盤は既存。新規インストールは不要。*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 窓往復で `thumb_cache` が非クリアのまま高速描画される（A1） | V16-UI-03 | キャッシュ挙動はレンダリング実機でないと体感確認できない | 大量ページ PDF を開き、前/次窓を往復してサムネイル再描画が即時（再生成なし）か確認 |
| 窓またぎ D&D で意図したページが正しい全ページ位置へ移動（A2） | V16-UI-03 (S3) | D&D ドラッグ操作は GUI 実機操作が必要 | 窓2 を表示中に選択ページを別位置へドラッグ → `current_page`/順序が全ページインデックスと整合するか確認 |
| ページング表示中の複数選択でページ操作（削除・回転）が選択どおり適用（S4） | V16-UI-03 (S4) | 複数選択 + 操作の連携は実機 UI で確認 | 窓をまたいで複数選択 → 削除/回転 → 選択どおり適用され `selected_pages` が全ページ index を指すか確認 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
