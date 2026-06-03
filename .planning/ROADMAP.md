# Roadmap: PageFolio コード最適化

## Overview

既存の PageFolio コードベースに対して、バグ修正・リファクタリング・テスト充実の 3 軸で品質を底上げする。
Phase 1 で Undo/Redo の正確性とパフォーマンス基盤を固め、Phase 2 でプレビューのシリアライズ排除と構造的リファクタリングを行い、
Phase 3 で残る API 整理とテスト網羅を完成させる。各フェーズ完了時点でテストが全通している状態を維持する。

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Undo/Redo 修正** - ページ挿入 Undo のバグ修正、Undo スタックの O(1) 化、Undo シリアライズコスト削減
- [ ] **Phase 2: プレビュー最適化とリファクタリング** - プレビューのフルシリアライズ廃止、dialogs / constants の分割
- [ ] **Phase 3: API 整理と回帰テスト** - settings 公開 API 化、import 回帰テスト整備

## Phase Details

### Phase 1: Undo/Redo 修正

**Goal**: Undo/Redo システムが正しく動作し、大きな PDF でも UI をブロックしない
**Depends on**: Nothing (first phase)
**Requirements**: BUG-01, BUG-02, REFAC-03, TEST-01
**Success Criteria** (what must be TRUE):

  1. ページ挿入操作の後に Undo を実行すると、挿入されたページが正確に除去されて元の状態に戻る
  2. Undo スタックへの追加と上限超過時の削除が O(1) で完了する（deque 使用）
  3. 大きな PDF（10 MB 以上）で Undo を実行しても UI がフリーズしない（BUG-02 対応の設計判断を反映）
  4. `pytest` が全通し、BUG-01 の修正を検証するユニットテスト（TEST-01）が含まれる

**Plans**: 3 plansPlans:
**Wave 1**

- [x] 01-01-PLAN.md — Undo/Redo の対称デルタ化・挿入 Undo 修正・pdf_bytes 撤廃（BUG-01/BUG-02）

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Undo/Redo スタックの deque(maxlen=MAX_UNDO) 化（REFAC-03）

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-03-PLAN.md — 挿入 Undo/Redo 内容同一性テスト・全 op 往復の安全網テスト（TEST-01）

### Phase 2: プレビュー最適化とリファクタリング

**Goal**: ページ切り替えのシリアライズが廃止され、主要モジュールの行数が管理可能な水準になる
**Depends on**: Phase 1
**Requirements**: BUG-03, REFAC-01, REFAC-02, TEST-02
**Success Criteria** (what must be TRUE):

  1. ページ切り替え時に `doc.tobytes()` が呼ばれない（`page.get_pixmap()` 直接呼び出しに変更済み）
  2. `pagefolio/dialogs/` サブパッケージが存在し、既存の `from pagefolio.dialogs import ...` import が動作する
  3. `constants.py` が `lang.py` / `themes.py` に分割され、既存の `C["BG_DARK"]` 等の参照が動作する
  4. `pytest` が全通し、BUG-03 の回帰テスト（TEST-02）が含まれる

**Plans**: TBD

### Phase 3: API 整理と回帰テスト

**Goal**: settings モジュールがプライベート変数への外部アクセスを持たず、import 回帰テストで全リファクタリングの安全性が保証される
**Depends on**: Phase 2
**Requirements**: REFAC-04, TEST-03
**Success Criteria** (what must be TRUE):

  1. `settings.py` に `set_current_font_size(size)` 関数が存在し、`app.py` が `_current_font_size` を直接書き換えていない
  2. `tests/` に import 回帰テスト（TEST-03）が存在し、REFAC-01〜04 で変更されたすべての import パスが壊れていないことを検証する
  3. `pytest` が全通し、`ruff check . && ruff format .` でエラーがない

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Undo/Redo 修正 | 2/3 | In progress | - |
| 2. プレビュー最適化とリファクタリング | 0/TBD | Not started | - |
| 3. API 整理と回帰テスト | 0/TBD | Not started | - |
