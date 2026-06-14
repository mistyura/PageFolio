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

## Milestone: v1.4.0 — OCR プロバイダ化 + クラウドAPI対応

**Shipped:** 2026-06-14
**Phases:** 4（Phase 04〜07）| **Plans:** 14 | **Tasks:** 26 | **Sessions:** 複数（2026-06-06〜06-12 実装、06-14 にマイルストーンクローズ）

### What Was Built
- **OCRProvider 抽象化（Phase 04）**: `abc.ABC` 基底 `OCRProvider` + `build_provider` ファクトリ。LM Studio を Provider 実装へリファクタし `run_parallel()` を一般化。埋め込みテキストスキップで API 呼び出しを節約。
- **Claude Provider + セキュリティ基盤（Phase 05）**: messages API による Claude OCR。`_SENSITIVE_KEYS` ガードで APIキー平文保存を構造的に防止。コスト確認ダイアログ・指数バックオフ・プロバイダ選択 UI。
- **Gemini Provider + 逐次レンダリング（Phase 06）**: x-goog-api-key 認証・dual env var の GeminiProvider。`queue.Queue(maxsize=concurrency+1)` の bounded buffer で全ページ base64 一括保持を廃止しメモリ上限を機械保証。`ocr_scale` 既定 1.5。
- **Tesseract + PluginManager（Phase 07）**: subprocess 直叩きのオフライン OCR（pytesseract 非依存）。`register_ocr_provider` フックでサードパーティ登録。日英文言・README・開発履歴を整備。

### What Worked
- **同型テンプレートでのプロバイダ横展開**: ClaudeProvider を雛形に GeminiProvider を実装（D-05）。インターフェース契約を Phase 04 で固めたことで Phase 05/06/07 が直線的に進んだ。
- **セキュリティ最優先タスク化**: APIキーガード（`_SENSITIVE_KEYS`）を Phase 05 着手直前の最優先に置き、平文漏洩リスクを早期に潰した。
- **ギャップクロージャの活用**: Phase 04/06 の検証で見つかった後方互換・並列度の BLOCKER を 04-04 / 06-04 のギャッププランで確実に解消。

### What Was Inefficient
- **Phase 07 の記録未クローズ**: 実装（commit `0c5dbfd`）は完了していたが SUMMARY.md 作成・STATE/ROADMAP 更新が漏れ、後続 v1.4.1〜v1.4.4 が記録不整合の上に積層。マイルストーンクローズ時に遡及クローズアウトが必要になった。
- **クイックタスクの完了マーカー欠落**: v1.4.1〜v1.4.4 のクイックタスク 4 件が監査で [unknown]/[missing] 判定。出荷済みだが記録上の完了印が欠けていた。
- **マイルストーン監査の人手検証ギャップ**: Phase 04 の `human_needed` 検証項目が未クローズのまま出荷。

### Patterns Established
- **二段プロバイダ解決**: `build_provider` 内蔵分岐 → `plugin_manager._provider_registry` フォールバック。
- **フィーチャ検出フラグ**: 起動時 1 回だけ外部コマンド（Tesseract）の存在・能力を評価しモジュールフラグ化。
- **APIキー非永続の徹底**: 環境変数＋セッションメモリ（`_session_api_keys`）のみ。`_SENSITIVE_KEYS` に大文字バリアントも登録。
- **スレッド境界の明確化**: fitz `get_pixmap()` はメインスレッド限定、ワーカーには base64 bytes のみ渡す。

### Key Lessons
1. **実装完了とフェーズクローズは別物**: コミットが入っても SUMMARY.md・STATE・ROADMAP を即更新しないと、後続作業が記録不整合の上に積み上がる。フェーズ完了時に bookkeeping をその場で閉じる。
2. **safe-resume ゲートが効いた**: execute-phase の「実装コミットあり・SUMMARY 欠落」検出が、既存コードの破壊的な再実装を未然に防いだ。
3. インターフェース契約を最初のフェーズで固めると、同型プロバイダの横展開が安価になる。
4. セキュリティ critical なガードは独立した最優先タスクとして前倒しする。

### Cost Observations
- Model mix: executor/verifier=opus（config: model_profile balanced・mode yolo）
- Notable: ローカル main が origin より大幅先行のため GSD worktree 並列が #683 で自動降格。単一プランフェーズは main tree 逐次実行で十分。

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.3.0 | 数 | 3 | GSD フルチェーン（discuss→plan→execute→verify）を最適化プロジェクトに初適用 |
| v1.4.0 | 複数 | 4 | 機能追加マイルストーン（OCR プロバイダ化）を GSD で実施。ギャップクロージャ・遡及クローズアウトを経験 |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.3.0 | 199 passed | （未計測） | 全要件を新規依存ゼロで達成 |
| v1.4.0 | 490 passed（v1.4.4 時点） | （未計測） | urllib 直叩きで全プロバイダを新規依存ゼロ実装 |

### Top Lessons (Verified Across Milestones)

1. 詳細な locked decision（CONTEXT.md）が下流フェーズの手戻りを最小化する。
2. 後方互換の境界は機械的テストで保護する（import 回帰テスト）。
3. 実装完了直後にフェーズ記録（SUMMARY/STATE/ROADMAP）を閉じる。記録の遅延は後続作業の不整合を生む（v1.4.0 Phase 07 の教訓）。
