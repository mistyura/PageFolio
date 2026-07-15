# Phase 4: バッチ複数ファイルOCR - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning

<domain>
## Phase Boundary

新設バッチ OCR ダイアログ（`BatchOCRDialog`・現在開いているファイルとは独立）で、ユーザーは複数の PDF ファイルを一括で OCR キューに投入し、進捗を確認しながら失敗ファイルを分離してバッチ全体を完了させ、複数ファイル横断の統合サマリを得られるようにする。`fitz.Document` のスレッド間共有は禁止のままファイル間は逐次処理限定、キャンセルは2階層（バッチ全体／ファイル内）、進捗はファイル軸とページ軸の二段で管理する。

対象要件: V180-BATCH-01〜05（複数ファイルD&D投入・キュー状態表示・失敗分離継続・全体/個別キャンセル・統合サマリ）。

**スコープ外:** バックグラウンド常駐継続（ダイアログを閉じたら処理停止）・キューの永続化（アプリ再起動でクリア）・失敗ファイルの一括再試行・multiprocessing によるファイル並列処理・サムネイル仮想化（Phase 5）・通知UX/UI一貫性監査（Phase 6）。

</domain>

<decisions>
## Implementation Decisions

### 起動導線・投入方式
- **D-01:** バッチOCRダイアログは新規メニュー項目「バッチOCR」から起動する独立ダイアログとする。単一ファイルOCR（既存 🔍 ボタン）とは明確に別動線。
- **D-02:** キューへのファイル追加は D&D + 「+ ファイル追加」ボタン（`filedialog.askopenfilenames` 複数選択）の両方に対応する。D&D は既存 `file_drop.py`/`app.py:_on_dnd_drop` の `tk.splitlist` + `SUPPORTED_EXTENSIONS` フィルタパターンを新規ウィジェットへ拡張適用する。
- **D-03:** OCR実行開始前に、バッチ全体の集約コスト確認ダイアログ（対象ファイル数・総ページ数・概算コスト）を一括表示する（FEATURES.md Anti-Features の推奨に従う）。各ファイルのページ数は `fitz.open(path).page_count` の軽量呼び出しでメインスレッド・逐次に事前取得する（V14-D-05/06 の範囲内・レンダリングは行わない）。
- **D-04:** バッチOCRは現在メインウィンドウで開いているファイル（`self.doc`）と完全に独立させる。自動追加はせず、ユーザーが明示的にファイルパスで選ぶ。編集中の未保存変更との衝突を構造的に避ける。

### キュー一覧の表示・操作
- **D-05:** キュー一覧は `ファイル名 / 状態（待機・実行中・完了・失敗） / ページ内進捗` の3列構成（`ttk.Treeview` 想定）。
- **D-06:** 失敗ファイルは行の文字色をテーマ辞書の警告色（`C["WARNING"]`）にする（`tag_configure` によるTreeviewタグ付けパターン）。
- **D-07:** キュー内ファイルの操作は**削除のみ**、かつ**待機中ファイルのみ**可能とする。実行中・完了・失敗済みの行は削除ボタンを無効化する。並び替えUI（`MergeOrderDialog` パターン）は今回は不採用。
- **D-08:** バッチ全体の進捗（ファイル数軸）は、ダイアログ上部に固定の進捗バー + 「ファイル x/合計」ラベルで常時表示する。キュー一覧の状態列（ページ内進捗）とは別軸として明示的に二段表示する（PITFALLS.md 落とし穴5「ファイル/ページ二軸の進捗集計が矛盾する」への対応）。

### 失敗・キャンセルの挙動
- **D-09:** ファイル単位の失敗（fatal エラー・サーキットブレーカー発動等）発生時は自動スキップして次ファイルへ進む（V180-BATCH-03 の要件文言どおり）。一時停止して確認を挟むことはしない。
- **D-10:** キャンセルUIは「バッチ中止」ボタン1つのみとする。「このファイルのみスキップ」という個別ボタンは設けない。ただし**内部実装は2階層のキャンセルフラグを維持**する（バッチ全体の cancel flag + 既存のファイル内 `_cancel_flag`/`_run_gen`）。「バッチ中止」押下時は両方のフラグを同時にセットし、実行中のファイルも含めて即座に停止させる（PITFALLS.md 落とし穴4の内部ロジックはそのまま踏襲し、UI露出のみユーザー選択で1ボタンに絞る）。
- **D-11:** 「バッチ中止」後も、完了済みファイルの OCR 結果はダイアログ内に保持され、閲覧・統合サマリ生成に引き続き使える。ダイアログを閉じた時点で破棄する（キューの永続化はしない — FEATURES.md Anti-Features の確定方針どおり）。
- **D-12:** 失敗ファイルの一括再試行機能（FEATURES.md で Differentiator/P2 扱い）は本フェーズに含めない。

### 統合サマリ・結果閲覧
- **D-13:** バッチ完了後の統合サマリは手動トリガー（「📊 サマリ作成」ボタン）とする。既存 `OCRDialog` の単一ファイル版と同じUX。バッチ完了時の自動生成はしない（不要な送信コストの発生を避ける）。
- **D-14:** V180-BATCH-05 の「入力過大時の事前警告」は、既存 `_confirm_summary_cost`（文字数表示・毎回確認ダイアログ）をそのまま拡張し、複数ファイル連結後の合計文字数を渡すことで満たす。新規のハード閾値・自動切り詰めロジックは追加しない。
- **D-15:** 統合サマリ生成時、複数ファイルの OCR 結果テキストを連結する際は、各ファイルの先頭にファイル名見出し（例: `=== ファイル名.pdf ===`）を挿入して連結する。LLM がファイル境界を認識しやすくし、サマリ品質を上げる。
- **D-16:** 各ファイルの OCR 結果の閲覧・エクスポートは、ファイル選択ドロップダウン/リストで切り替えて、既存 `OCRDialog` の結果ビュー（Markdown整形描画 `_insert_markdown`・コピー/保存は raw 維持）をそのまま流用する。エクスポートはファイル単位。

### Claude's Discretion
- ページ内進捗表示の具体的なウィジェット（プログレスバー併記 vs テキストのみ「n/m」）
- `PipelineState` の上位に置く薄い純関数層（ファイル完了/失敗イベント集計・落とし穴5対応）の内部データ構造・関数API設計（`BatchState` 等の名称含む）
- キュー投入時の事前ページ数スキャンでファイルが壊れている/開けない場合のエラー表示文言・キュー上の扱い
- ファイル選択ドロップダウン/リスト（D-16）のウィジェット種類（`ttk.Combobox` vs `tk.Listbox`）
- 新規メニュー項目「バッチOCR」（D-01）のメニューバー上の配置位置

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・フェーズ定義
- `.planning/REQUIREMENTS.md` — V180-BATCH-01〜05 の要件文言（本フェーズの対象5要件）
- `.planning/ROADMAP.md` — Phase 4 の Goal・Success Criteria（成功基準5項目）・依存関係（Phase 3 完了前提・OCRRunEngine 再利用の明記）

### リサーチ成果物
- `.planning/research/PITFALLS.md` 落とし穴3「バッチ複数ファイル OCR が fitz Document のスレッド間共有禁止を破る」・落とし穴4「バッチキューのキャンセルが現在処理中のファイルのみに留まる」・落とし穴5「バッチ OCR の進捗集計がファイル単位/ページ単位で二重に矛盾する」— 本フェーズの中心的リスク3点。回避策（ファイル間逐次処理・2階層キャンセルフラグ・`PipelineState` 上位の薄い純関数層）が既に明記されている
- `.planning/research/FEATURES.md` §3「バッチ複数ファイル OCR」— Table Stakes（キュー一覧・個別/全体進捗・失敗分離・D&D投入）・Differentiators（一括要約・バックグラウンド継続・失敗一括再試行）・Anti-Features（並列fitzレンダリング・確認なし一括送信・キュー永続化）の境界線
- `.planning/research/SUMMARY.md` — バッチOCR推奨アプローチ（`ocr_pipeline.py` の producer-consumer をファイル単位でもう一段ラップする設計）

### 前フェーズの決定事項
- `.planning/phases/03-ocr-e2e/03-CONTEXT.md` — `OCRRunEngine` の設計（D-01: producer 非内包・D-11: 実行ごとに新規生成）が本フェーズの「ファイルごとに Engine を新規生成して再利用」という設計の直接的根拠
- `.planning/phases/02-ai/02-CONTEXT.md` — 送信先確認ダイアログの毎回表示・明示同意方針（D-10 踏襲元）・`MergeOrderDialog` の並び替えUIパターン（本フェーズでは不採用だが将来の並び替え要望時の参考）

### 前例パターン（コード内）
- `pagefolio/ocr_engine.py` — `OCRRunEngine`（D-01/D-09〜D-11 の直接再利用対象。ファイルごとに新規インスタンス化する）
- `pagefolio/file_drop.py`・`pagefolio/app.py:_on_dnd_drop`（`tk.splitlist` + `SUPPORTED_EXTENSIONS` フィルタパターン。D-02 の踏襲元）
- `pagefolio/ocr_dialog.py:1194-1265` — `_confirm_cost`/`_confirm_summary_cost`（D-03/D-14 の拡張対象。バッチ集約確認・過大入力警告に流用）
- `pagefolio/ocr_dialog.py:2006-` — `_on_summary`/`_summary_worker`/`complete_text_ex` 呼び出し（D-13/D-15 の拡張対象。ファイル横断統合サマリの土台）
- `pagefolio/dialogs/merge.py` — `MergeOrderDialog`（並び替えUI前例。本フェーズでは不採用だが将来必要になった場合の参考実装）
- `pagefolio/ocr.py:541-` — `_start_ocr`（provider 生成・concurrency クランプのロジック。バッチ側でファイルごとに同様の処理をループ内で行う必要がある）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OCRRunEngine`（`pagefolio/ocr_engine.py`）: ファイルごとに新規生成して再利用できる（Phase 3 D-01/D-11 が直接の設計根拠）。producer（fitz レンダリング連鎖）は呼び出し側（`BatchOCRDialog`）が持つ
- `_confirm_cost`/`_confirm_summary_cost`（`ocr_dialog.py`）: バッチ集約コスト確認（D-03）・サマリ過大入力警告（D-14）にそのまま拡張利用できる
- `file_drop.py` の `tk.splitlist` + `SUPPORTED_EXTENSIONS` フィルタ: バッチキューへのD&D実装にそのまま応用できる
- `_insert_markdown` 等の整形描画ロジック（`ocr_dialog.py`）: ファイル別結果ビュー（D-16）にそのまま流用できる

### Established Patterns
- fitz メインスレッド限定・逐次レンダリング（V14-D-05/06）: バッチではファイル間処理にも拡張適用する（落とし穴3対応・multiprocessing不採用）
- `_run_gen` 世代ガード・`cancel_flag` パターン: バッチ全体 cancel flag と既存ファイル内 flag の2階層構成として拡張する（落とし穴4対応。UIボタンは D-10 により1つに集約するが、内部フラグ構造は2階層のまま）
- 送信先確認ダイアログの毎回表示・明示同意（既定off・コスト確認、V14-D-03/OCR-SEC-01）: バッチ集約確認・サマリ過大警告もこの方針をそのまま踏襲する

### Integration Points
- 新規メニュー項目からの `BatchOCRDialog`（新規 `Toplevel`）起動。`self.doc`/`self.filepath` は一切参照しない独立設計（D-04）
- ファイルごとに `build_provider` を再生成し、`concurrency`・APIキー解決を再評価する（`ocr.py:_start_ocr` と同様のロジックをファイルループ内で実行）
- `PipelineState` の外側にファイル完了/失敗イベントを集計する薄い純関数層（`ocr_pipeline.py`/`ocr_engine.py` と同じ Tk/fitz 非依存の系譜）を新設し、D-08 の二段進捗表示を支える

</code_context>

<specifics>
## Specific Ideas

- 議論全体を通じて「シンプルさ・過剰実装回避」を一貫して選択: 集約コスト確認は追加するが独自の切り詰め閾値ロジックは追加しない（D-14）・キャンセルUIは1ボタンに絞る（D-10、内部の2階層構造は維持）・失敗ファイル一括再試行は見送る（D-12）
- 失敗時は一貫して「処理を止めない」方向: 自動スキップ（D-09）・中止後も完了済み結果は保持（D-11）
- 統合サマリは既存の単一ファイル版（`OCRDialog` の「📊 サマリ作成」ボタン）と同じ手動トリガーUXを踏襲する（D-13）

</specifics>

<deferred>
## Deferred Ideas

- **失敗ファイルの一括再試行機能** — FEATURES.md で Differentiator/P2 扱い。将来の別フェーズ/別タスク候補（D-12 で明示的に不採用）

</deferred>

---

*Phase: 4-バッチ複数ファイルOCR*
*Context gathered: 2026-07-15*
