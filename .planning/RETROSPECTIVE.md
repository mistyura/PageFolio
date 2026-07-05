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

## Milestone: v1.6.0 — 品質向上・AI強化・設定/UI改善

**Shipped:** 2026-06-20
**Phases:** 4 | **Plans:** 11 | **Tasks:** 23 | **Sessions:** 複数（2026-06-18〜06-20 実装、06-20 にマイルストーンクローズ）

### What Was Built
- **設定/UI 改善（Phase 1）**: OCRDialog の数値パラメータ 4 Spinbox + model_combo を読み取り専用化し、編集導線を「⚙ LLM 設定…」へ一元化（全プロバイダ共通箇所でライブ同期）。二重入力（V16-UI-01）を解消。サムネイルスライダーを独立全幅行へ移設（V16-UI-02）。
- **ページネーション表示（Phase 2）**: 大量ページのサムネイル一覧を窓表示（既定 20）。index 変換（local↔global）を Tk/fitz 非依存の純ロジック層 `pagination.py` へ集約し、D&D/複数選択の全ページインデックス整合を機械保証。current_page 窓追従の不変条件で UAT snap back も解消（V16-UI-03）。
- **体感品質・OCR 堅牢性（Phase 3）**: 回転プレビュー即時反映をセレクション意味論の原因除去で修正（回転 w/h 単体テストを回帰アンカー化）。API キー秘匿の 3 経路回帰テスト化（caplog 値非出力・ソース実キースキャン・LANG parity）+ H5 実 API 検証チェックリスト（V16-QUAL-01〜04・pagefolio/ ソース無改変）。
- **AI 出力品質（Phase 4）**: OCR 結果 Markdown を (行種別, インライン span) へ変換する純関数 `parse_markdown` + プロバイダ別プロンプト解決 `resolve_ocr_prompt`（Claude=XML/Gemini=明示・custom 温存）を新設し、OCRDialog の薄い描画/解決層へ配線。コピー/保存は raw 維持（V16-AI-01/02）。

### What Worked
- **純ロジック層への切り出しが一貫して効いた**: `pagination.py`（Phase 2）・`md_render.parse_markdown` / `resolve_ocr_prompt`（Phase 4）を Tk 非依存の純関数として先に確定し、UI 配線を「純関数の戻り値を insert/tag_add するだけ」の薄い層に保てた。unit テストがヘッドレスで網羅でき、Wave1（純関数）→ Wave2（配線）の依存が明快。
- **実機 debug で真因特定**: Phase 3 H1 回転即時反映は表層パッチでなくセレクション意味論まで掘って原因除去。
- **safe-resume が誤マッチを防いだ**: 現 Phase 4(04-ai-c) の成果物がディスク不在と検出し、旧 v1.4.0 Phase4(04-provider-abstraction) の feat コミット誤マッチを退けて新規着手（フェーズ採番のマイルストーン跨ぎ問題）。

### What Was Inefficient
- **executor の Bash 権限拒否**: gsd-executor の Bash が ruff/pytest/git で拒否され、04-03 の検証・コミット・継続をオーケストレータがインライン代行する必要が生じた。
- **受入 grep ゲート × ruff format 折返しの衝突**: 単一行 grep 受入基準と ruff format の自動折返しが衝突し、`# fmt: off`/`# noqa: E501` の回避を要した（メソッドスコープ awk 受入への移行が再発防止候補）。
- **バージョン番号の二重化**: マイルストーン途中で APP_VERSION を v1.7.0 へ一時バンプ後、49e9893 で v1.6.0 へ巻き戻し。開発履歴.md に v1.7.0 エントリが残り、クローズ時に出荷版番の確認が必要になった（V16-D-04・整合は残課題）。
- **human-verify スキップ**: Phase 4 の gate=blocking チェックポイントをユーザー判断でスキップしクローズ。実描画/実 API 出力品質は未検証で deferred 受容。

### Patterns Established
- **Wave1 純関数 → Wave2 薄い配線**: ロジックを Tk/fitz 非依存の純関数へ集約し、UI 層は描画/解決の呼び出しのみに留める。表示専用の整形（tk.Text タグ）とエクスポート（raw 維持）を分離。
- **index 整合の純ロジック層化**: ページング等の「表示窓 vs 全体」整合は local↔global 変換を 1 モジュールへ集約し境界値 unit テストで固める。
- **監査=検証フェーズ**: セキュリティ監査（キー秘匿）はソース無改変で回帰テスト・実キースキャン・チェックリスト整備に徹する。

### Key Lessons
1. **純関数先行は配線フェーズを安価にする**: UI に触れる前にロジックを Tk 非依存純関数へ落とすと、テスト網羅・後方互換ガード・配線の薄さが同時に得られる。
2. **バージョン番号は一度バンプしたら巻き戻さない**: 途中バンプ→巻き戻しは履歴ドキュメントに不整合の痕跡を残す。版番はマイルストーン完了時に一度だけ確定する方針を徹底する。
3. **オーケストレータのインライン代行は権限拒否の確実なリカバリ**: executor の Bash 拒否時は再 spawn せず、検証・コミット・継続をオーケストレータが直接実施するのが速い。
4. **human-verify スキップは記録に残す**: gate=blocking のスキップは VERIFICATION を human_needed のまま deferred 受容として明示記録する。

### Cost Observations
- Model mix: executor=opus（parallelization 設定 true だが #683 で逐次降格）・reviewer/verifier=sonnet
- Notable: local main が origin 先行のため worktree 並列を逐次実行へ降格（既知パターン）。Wave1 純関数は files_modified 重複ゼロで並行実行。

---

## Milestone: v1.7.1 — 現機能ブラッシュアップ + APIキー入力欄

**Shipped:** 2026-07-05
**Phases:** 4 | **Plans:** 16 | **Tasks:** 41 | **Sessions:** 複数（2026-07-04〜07-05 実装、07-05 にマイルストーンクローズ）

### What Was Built
- **APIキー入力欄の一元化（Phase 1）**: LLMConfigDialog に Claude/Gemini/RunPod のマスク付きキー入力欄を追加し、解決優先順を「環境変数優先」から「入力値（セッションキー）優先」へ反転。OCRDialog 側の旧セッションキー UI を撤去して導線を一元化し、送信先確認ダイアログの RunPod 誤開示（CR-01）もギャップ閉塞プランで解消。
- **OCR 磨き込み（Phase 2）**: プラグイン OCR registry の重複名ポリシー・unload 時登録解除・公開アクセサ化。Tesseract の言語段階的縮退フォールバック。producer-consumer 実行パイプラインの二重実装（`ocr.py` 未使用ヘルパー vs `ocr_dialog.py` 独自実装）を新設 `ocr_pipeline.py` へ一本化（v1.4.0 期レビュー L-1、高リスクのため独立プランへ隔離して実行）。
- **ページ操作磨き込み + 回帰テスト（Phase 3）**: 画像（ロゴ）透かし対応（v1.5.0 のテキストのみ制限を解除）。`_derotate_rect` 共通ヘルパーで黒塗り/モザイク/トリミングの回転座標ズレを構造的に解消。黒塗り/モザイクの連続適用・粒度スライダー。v1.5.0 新機能（TOC保持・D&D挿入・ショートカット読込）の回帰テストを新規分離。
- **UI/UX 磨き込み + バグ棚卸し（Phase 4）**: ShortcutsDialog 新設（実キーキャプチャ編集・重複拒否、v1.5.0 の JSON 直接編集ミニマム実装を置き換え）。SettingsDialog 3セクション再編・LLMConfigDialog 共通/固有グルーピング + ネスト適用トランザクション化。未使用 LANG キー11件削除と検出回帰テストの常設。

### What Worked
- **高リスク項目の独立プラン隔離**: Phase 2 の producer-consumer 一本化（L-1・`ocr.py`/`ocr_dialog.py` 横断）を他の OCR 磨き込みプランから切り離し、Wave 4 で単独実行・単独検証したことで、二重実装解消という大きな変更が他の小粒プランを巻き込まずに完了した。
- **レビュー残の現行照合を計画時に必須化**: v1.4.0 期レビュー（L-1〜L-6）は v1.6.0〜v1.7.0 で一部解消済みだったため、各フェーズ計画時に現行コード照合で「活き残り」を確定してから対象化する方針（V171-R-05）が、解消済み項目への無駄な再実装を防いだ。
- **「棚卸し→改善」型要件の計画時確定**: PAGE-02/03・TEST-03 は具体項目を計画時に確定・記録する方針（V171-R-06）が、実装時の手戻りを防いだ。

### What Was Inefficient
- **APP_VERSION の更新漏れ**: 4 フェーズとも `pagefolio/constants.py` の `APP_VERSION` 更新（CLAUDE.md 変更時チェックリスト）を実施せず、v1.7.0 のまま `/gsd-complete-milestone` まで到達。マイルストーンクローズ時に発覚し、その場で v1.7.1 へ更新・README/開発履歴.md を同期した。v1.6.0 の教訓（バージョン番号は一度だけ確定・途中バンプ→巻き戻しを避ける）とは別に、「バンプ自体を忘れる」という新しい失敗モード。
- **締め前監査の同一4件が3回連続で受容**: v1.4.0・v1.6.0 に続き v1.7.1 クローズでも同じ 4 件のクイックタスク記録マーカー欠落が audit-open で再検出され、再度ユーザー判断で受容。実データは v1.4.0〜v1.4.4 で出荷済みのため実害はないが、根本的な記録修復（マーカー付与）が3マイルストーン分先送りされている。

### Patterns Established
- **独立プラン隔離による高リスク変更の分離**: 複数モジュール横断のリファクタは、他の並行プランから独立した Wave として単独実行・単独検証する（Phase 2 L-1 一本化）。
- **レビューバックログの鮮度管理**: 古いレビュー由来の要件は「計画時に現行コード照合で活き残りを確定してから対象化」を標準手順化。

### Key Lessons
1. **バージョン番号更新は最終フェーズのタスクとして明示的にチェックリスト化する**: CLAUDE.md に手順は明記されているが、各フェーズの実行チェックリストに組み込まれていないと素通りされる。次マイルストームでは最終フェーズの成功基準に APP_VERSION 更新を明示的に含める。
2. 高リスク・横断的なリファクタは他のプランと並行させず、独立 Wave として隔離すると安全に完了できる（v1.7.1 Phase 2）。
3. レビューバックログ（L-1〜L-6 のような）は時間経過で一部解消されるため、対象化前に現行コード照合を必須ステップにする。
4. 同一の記録マーカー欠落を毎回「受容」するだけでなく、3 回目以降は実際にマーカーを補完する対応も検討する。

### Cost Observations
- Model mix: model_profile balanced（mode: yolo の自律チェーン）
- Notable: 125 コミット・98 ファイル変更・約 18,100 行追加/970 行削除を約 1 日（2026-07-04〜07-05）で完了。

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.3.0 | 数 | 3 | GSD フルチェーン（discuss→plan→execute→verify）を最適化プロジェクトに初適用 |
| v1.4.0 | 複数 | 4 | 機能追加マイルストーン（OCR プロバイダ化）を GSD で実施。ギャップクロージャ・遡及クローズアウトを経験 |
| v1.6.0 | 複数 | 4 | Wave1 純関数 → Wave2 配線の二段構成を定着。executor Bash 拒否のインライン代行・版番二重化・human-verify スキップを経験 |
| v1.7.1 | 複数 | 4 | レビューバックログ（L-1〜L-6）の鮮度管理を計画時必須化。高リスク横断リファクタの独立プラン隔離を定着。APP_VERSION 更新漏れを経験 |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.3.0 | 199 passed | （未計測） | 全要件を新規依存ゼロで達成 |
| v1.4.0 | 490 passed（v1.4.4 時点） | （未計測） | urllib 直叩きで全プロバイダを新規依存ゼロ実装 |
| v1.6.0 | 597 passed | （未計測） | pagination.py / md_render.py を標準ライブラリのみで新設 |
| v1.7.1 | 859 passed | （未計測） | ocr_pipeline.py を標準ライブラリのみで新設 |

### Top Lessons (Verified Across Milestones)

1. 詳細な locked decision（CONTEXT.md）が下流フェーズの手戻りを最小化する。
2. 後方互換の境界は機械的テストで保護する（import 回帰テスト）。
3. 実装完了直後にフェーズ記録（SUMMARY/STATE/ROADMAP）を閉じる。記録の遅延は後続作業の不整合を生む（v1.4.0 Phase 07 の教訓）。
4. ロジックは Tk/fitz 非依存の純関数へ先に落とし、UI 層を薄い配線に保つとテスト網羅と後方互換が安価になる（v1.6.0）。
5. バージョン番号はマイルストーン完了時に一度だけ確定し、途中バンプ→巻き戻しを避ける（v1.6.0）。バンプ自体を忘れないよう最終フェーズの成功基準に明示的に含める（v1.7.1）。
6. 高リスク・横断的なリファクタは独立 Wave として他プランから隔離すると安全に完了できる（v1.7.1）。
