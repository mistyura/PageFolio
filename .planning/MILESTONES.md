# Milestones

## v1.3.0 コード最適化 MVP (Shipped: 2026-06-03)

**Phases completed:** 3 phases, 8 plans, 3 tasks

**Key accomplishments:**

- `doc.tobytes()` 全体シリアライズを撤廃し全 op を op 別逆デルタで往復させる対称 Undo/Redo 設計への全面刷新（BUG-01 挿入 Undo 修正・BUG-02 フリーズ解消）
- `_undo_stack`/`_redo_stack` を `collections.deque(maxlen=MAX_UNDO)` に変更し `_save_undo` の手動 `list.pop(0)` O(n) トリムを撤廃して上限管理を O(1) に一本化（REFAC-03）
- 挿入 Undo の内容同一性（digest）・redo 往復テスト（D-07）と全 op 最小往復安全網テストを追加し、テストで発見した delete/move/merge_resize の対称デルタバグ 3 件を Rule 1 自動修正（TEST-01 / Deferred 安全網）
- ページ切り替え時の `doc.tobytes()` フルシリアライズを廃止し、`page.get_pixmap()` の同期直接呼び出しへ変更。Tk 非依存の純関数ヘルパー `_render_preview_pixmap` を抽出してテスト可能にし、回帰テスト `tests/test_viewer.py` を新規作成した。
- 711 行の混在モジュール `pagefolio/constants.py` を責務別に3分割（themes.py・lang.py・再エクスポート化した constants.py）し、後方互換 import 表面を完全に維持したリファクタリング。
- Task 3（最終ゲート）
- `set_current_font_size` / `get_current_font_size` 公開 API を settings.py に追加し、app.py・merge.py・llm_config.py の `_current_font_size` 直接アクセスをすべて API 経由に置換（DEBT-04 解消 / D-02 stale binding 修正）。

---
