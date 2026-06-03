# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.3.0 — コード最適化 MVP

**Shipped:** 2026-06-03
**Phases:** 3 | **Plans:** 8 | **Sessions:** 数セッション（2026-06-03 に 3 フェーズを集中実行）

### What Was Built
- **Undo/Redo の対称デルタ化**: `doc.tobytes()` 全体シリアライズを撤廃し op 別逆デルタへ全面刷新（BUG-01 挿入 Undo 修正・BUG-02 フリーズ解消）。Undo スタックを `collections.deque(maxlen=MAX_UNDO)` 化し O(1) トリム（REFAC-03）。
- **プレビュー最適化**: ページ切り替え時のフルシリアライズを廃止し `page.get_pixmap()` 同期直接呼び出しへ。Tk 非依存の純関数 `_render_preview_pixmap` を抽出（BUG-03）。
- **構造リファクタリング**: `dialogs.py`（1,191 行）を `pagefolio/dialogs/` サブパッケージへ、`constants.py`（711 行）を `lang.py`/`themes.py` へ分割。後方互換 import 表面を完全維持（REFAC-01/02）。
- **API 整理**: `settings._current_font_size` の外部直接アクセスを公開 API（`set_current_font_size`/`get_current_font_size`）へ一本化。stale binding バグも解消（REFAC-04）。
- **テスト網羅**: Undo 往復（TEST-01）・プレビュー回帰（TEST-02）・import 回帰（TEST-03・4クラス34テスト）を整備。最終 **pytest 199 件全通・ruff クリーン**。

### What Worked
- **詳細な CONTEXT.md（discuss-phase）が効いた**: Phase 3 では D-01〜D-09 の locked decision が具体的な行番号付きで揃っており、リサーチ・計画・実行・検証が一直線に進んだ。
- **リサーチでの実測検証**: Phase 3 リサーチが「`LLMConfigDialog` はトップレベル非公開」「setter に `global` 必須」を実コード実行で先に発見し、実装トラップを未然に回避。
- **後方互換 import 表面の温存方針**: 再エクスポートで既存 import を壊さない方針が一貫しており、TEST-03 の import 回帰テストがその安全網として機能。
- **テストがバグを発見**: Phase 1 の全 op 往復安全網テストが delete/move/merge_resize の対称デルタバグ 3 件を自動検出・修正。

### What Was Inefficient
- **マイルストーン監査の未実施**: `/gsd-audit-milestone` を経ずにクローズへ進んだ（各フェーズは個別に検証 passed だったため許容）。クロスフェーズ E2E 監査は次回習慣化したい。
- **軽微な保守債が残存**: コードレビューで `except Exception:` のロガー欠落・`font_size` デフォルト不整合（10 vs 12）・roundtrip テストの `finally` 欠落が advisory として残った（非ブロッキング）。
- **既存の小不整合の伝播リスク**: 既存コードの `get("font_size", 10)` 不整合が新 setter 経由で表面化しうる点はリファクタ時にもっと早く拾えた。

### Patterns Established
- **discuss → research → plan → check → execute → verify の GSD チェーン**が小規模最適化でも有効。
- **「明示 import + シンボル存在 assert」の import 回帰テスト**（`tests/test_imports.py`）を後方互換の機械的保証として常設。
- **Tk 非依存テスト方針**（root を立てない・import/純関数のみ）を踏襲し CI/ヘッドレス安全を維持。
- **リファクタは挙動不変が原則**（D-04: setter はクランプを入れず単純代入）。

### Key Lessons
1. リファクタ前の「実測リサーチ」（実際に import/grep/実行して確認）が、ドキュメント上の前提ズレを最も安く潰す。
2. 後方互換を守るなら、その境界を機械的に検証する import 回帰テストを同時に入れると将来のリファクタが安全になる。
3. コードレビューの advisory 指摘（規約違反・既存不整合）は小さいうちに別タスク化しておくと負債が積み上がらない。

### Cost Observations
- Model mix: planner=opus、researcher/executor/verifier/reviewer=sonnet（mode: yolo の自律チェーン）
- Notable: 単一プランのウェーブは worktree 並列の利得がないため main tree 逐次実行に切替え、Windows の worktree マージ負荷を回避。

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.3.0 | 数 | 3 | GSD フルチェーン（discuss→plan→execute→verify）を最適化プロジェクトに初適用 |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.3.0 | 199 passed | （未計測） | 全要件を新規依存ゼロで達成 |

### Top Lessons (Verified Across Milestones)

1. 詳細な locked decision（CONTEXT.md）が下流フェーズの手戻りを最小化する。
2. 後方互換の境界は機械的テストで保護する（import 回帰テスト）。
