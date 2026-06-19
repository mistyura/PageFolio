# Phase 4: プロバイダ抽象化 - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

OCR バックエンドを差し替え可能にする「土台」を作るフェーズ。LM Studio 専用だった現行 OCR を `OCRProvider` の一実装へ移し、`run_parallel()` をプロバイダ非依存に一般化し、テキスト埋め込みページの OCR スキップ機構を新設する。

**このフェーズで作るもの:**
- 新規 `ocr_providers.py`: `OCRProvider` 抽象基底（`ocr_image()` / `list_models()` / 例外規約 / 並列度ポリシー）
- `LMStudioProvider`: 現行 LM Studio ロジックを Provider 実装へリファクタ
- `run_parallel(provider, ...)`: 現行 `call_lm_studio_parallel` をプロバイダ非依存に一般化（プロバイダ別並列度を受け取る）
- `has_embedded_text()`（新設）: ページのテキスト埋め込み判定で OCR をスキップ
- スレッド境界の明確化: ワーカースレッド内から `fitz` / `get_pixmap()` の直接呼び出しを排除

**このフェーズで作らないもの（スコープ外 → 別フェーズ）:**
- Claude Provider・セキュリティ基盤・プロバイダ選択 UI → Phase 5
- Gemini Provider・逐次レンダリング化・`ocr_scale` 見直し → Phase 6
- Tesseract Provider・PluginManager 登録フック・本格的な多言語文言整備・ドキュメント更新 → Phase 7
- 429/5xx 指数バックオフリトライ（クラウド固有）→ Phase 5

**絶対条件:** LM Studio の OCR 挙動・UI 操作が v1.3.0 と完全後方互換であること（成功基準1）。

</domain>

<decisions>
## Implementation Decisions

### スレッド境界の再構成（成功基準3対応）
- **D-01:** fitz レンダリングをワーカースレッドの外へ出す出し方は **Claude 裁量**。基本線は「事前レンダリング最小構成」——メインスレッドで全ページを（`after()` で小分けし UI フリーズを回避しつつ）レンダリングして b64 辞書を揃え、ワーカースレッドは API 呼び出しのみを担う。
- **D-02:** 逐次レンダリング化（render→送信→破棄のページ単位逐次化）は **Phase 6 に温存**。Phase 4 では踏み込まない。今のスコープを超える再構成（部分逐次化）は行わない。
- **D-03:** 成功基準3「ワーカースレッド内に `fitz.Document` / `get_pixmap()` の直接呼び出しが一切存在しない」を満たすことが必達。現行 `_worker` フェーズ1の `page_to_png_b64(self.doc[page_idx], ...)`（ocr_dialog.py:475）をメインスレッド側へ移す。現行の progress コールバック（`self.after(0, ...)` による進捗更新）との整合を保つ。

### Provider インターフェースの境界
- **D-04:** `OCRProvider.ocr_image()` の入力型は **base64 PNG 文字列**。現行 `call_lm_studio(b64_png, ...)` の契約を踏襲。Claude/Gemini/LM Studio いずれも最終的に base64 を使うため再エンコード不要で、後方互換も崩さない。
- **D-05:** Provider は「画像 in → テキスト out」に**純化**する。`has_embedded_text()` 判定と `page.get_text()` は fitz に触れるため Provider 内には置かず、Mixin/Dialog 側（メインスレッド）に配置する。これによりスレッド境界（D-03）とも整合する。

### 埋め込みテキストの扱い（成功基準2対応）
- **D-06:** 「テキスト埋め込み済み（OCR不要）」の判定は **文字数しきい値方式**。`page.get_text()` の非空白文字数がしきい値以上ならスキップ扱い。ページ番号・薄い OCR レイヤー等のわずかな文字による誤検出を抑制する。しきい値の具体値は計画/実装段階で調整（Claude 裁量）。
- **D-07:** 判定は**ページ単位**に適用。混在 PDF（テキストありページ + スキャンページ）で、テキストありページは API を呼ばず `page.get_text()` の結果を採用し、スキャンページのみ Vision API に回す。
- **D-08:** スキップしたページは **UI に明示**する（進捗・結果に「テキスト抽出（OCRスキップ）」等を表示）。ユーザーが「なぜ API が呼ばれなかったか」「コスト削減効果」を把握できるようにする。抽出テキストは OCR 結果と同じ結果辞書へ統合しつつ、由来を区別表示する（統合方法・文言詳細は Claude 裁量）。
- **D-09:** スキップ通知の日英文言を Phase 4 で**最小限追加**する（`lang.py`）。プロバイダ名・コスト警告等を含む本格的な多言語文言整備は Phase 7。

### 並列度ポリシー（成功基準4対応）
- **D-10:** プロバイダ別並列度は **Provider のクラス属性**（`default_concurrency` / `max_concurrency` 等）で宣言する。`run_parallel()` は Provider のポリシーを読み、`settings` の値を `[1, provider.max_concurrency]` でクランプして用いる。
- **D-11:** これにより成功基準4「新しいプロバイダクラスをファイルに追加するだけで `run_parallel()` から呼び出せる（プロバイダ別並列度が受け取れる）」を満たす。Phase 5/6 の Gemini=1 / Claude=2、LM Studio 最大8 もこの仕組みに乗せる。

### 後方互換（公開関数の扱い）
- **D-12:** 現行公開関数（`call_lm_studio` / `call_lm_studio_parallel` / `fetch_lm_studio_models` 等、`ocr_dialog.py` が import）の残置/移設/ラッパー化は **Claude 裁量**。基本線は「呼び出し側を更新するクリーンなリファクタ」——LM Studio 固有関数は `LMStudioProvider` 内へ移し、`ocr_dialog.py` は新 Provider/`run_parallel` API を使うよう更新する。
- **D-13:** `page_to_png_b64` のような**プロバイダ非依存の汎用レンダリングユーティリティ**は残置/移設して再利用する（Provider には属さない）。
- **D-14:** API サーフェスの後方互換は不問（ライブラリではなくアプリ内部のため）。LM Studio の**振る舞い**の後方互換は成功基準1で担保する。

### Claude's Discretion
- スレッド境界の具体的な出し方（D-01: 事前レンダリングの小分け方法・コーディネータ実装）
- 埋め込みテキスト判定しきい値の具体値（D-06）
- スキップ結果の結果辞書への統合方法・表示文言の細部（D-08）
- 現行公開関数の関数ごとの残置/移設/ラッパー化判断（D-12）
- 例外規約の統一方針（`ConnectionError` / `TimeoutError` / `RuntimeError` の Provider 横断的な扱い — 現行 `call_lm_studio` の規約を基底へ昇格）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 設計の正典
- `docs/OCRプロバイダ化_見積もり仕様.md` — v1.4.0 全体の確定スコープ・フェーズ分割・各 API 差分・低スペック対策方針。Phase 4 該当箇所: §2.1 プロバイダ抽象化（採用方式・`ocr_image()`/`list_models()`/例外規約）、§4.2 テキスト埋め込み判定による OCR スキップ、§4.3 レンダリング負荷・メモリ（逐次化は Phase 6）、§5 作業項目 #1〜#3・#8。
  - **注意:** 同仕様書 §3 の「Opus 4.7/4.8 は `temperature` 不可」記述は誤り。API 細部は `.planning/research/STACK.md` のリサーチ結果で上書きする（Phase 5 で関係）。Phase 4 には直接影響しない。

### リサーチ成果（v1.4.0）
- `.planning/research/SUMMARY.md` — エグゼクティブサマリ。Phase 04 は「既存コードのリファクタが主体・追加調査不要」。Pitfall #4（fitz スレッド非安全）のスレッド境界明確化を完了条件に含めること。
- `.planning/research/ARCHITECTURE.md` — `OCRMixin` を土台に `ocr_providers.py` を新設する統合設計。`run_parallel()` 一般化・`has_embedded_text()` 新設の位置づけ。
- `.planning/research/PITFALLS.md` — Pitfall #4（fitz スレッド非安全 = 成功基準3の根拠）。Pitfall #2/#3（メモリ・並列度）は主に Phase 6/5。

### 要件・ロードマップ
- `.planning/ROADMAP.md` §Phase 4 — Goal・Success Criteria（1〜4）・依存（Phase 3 = v1.3.0 完了済み）。
- `.planning/REQUIREMENTS.md` — OCR-PROV-01 / OCR-PROV-02 / OCR-PROV-03 / OCR-PERF-01（Phase 4 担当の4要件）。

### 既存コード（リファクタ対象）
- `pagefolio/ocr.py` — 現行 LM Studio 実装。`OCR_PROMPTS` / `page_to_png_b64`（46行）/ `build_chat_payload` / `call_lm_studio`（例外規約: ConnectionError/TimeoutError/RuntimeError）/ `call_lm_studio_parallel`（136行・ThreadPoolExecutor・concurrency クランプ・fatal/error 区別）/ `fetch_lm_studio_models` / `OCRMixin`。定数: `DEFAULT_OCR_CONCURRENCY=2` / `MAX_OCR_CONCURRENCY=8`。
- `pagefolio/ocr_dialog.py` — `OCRDialog`。`_worker`（439行〜）が背景スレッドでフェーズ1（直列レンダリング・`page_to_png_b64(self.doc[...])`）→フェーズ2（`call_lm_studio_parallel` 委譲）→フェーズ3（UI 反映）を実行。スレッド境界リファクタの主対象。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `page_to_png_b64(page, scale)`（ocr.py:46）: プロバイダ非依存の fitz→PNG→base64 変換。D-13 で汎用ユーティリティとして残置/再利用。
- `call_lm_studio_parallel`（ocr.py:136）の ThreadPoolExecutor 駆動・concurrency クランプ・`on_progress`/`is_cancelled` コールバック・fatal(connection/timeout) と err(ページ単位) の区別構造: `run_parallel()` 一般化の骨格として流用できる。
- 例外規約（`ConnectionError`=接続失敗 / `TimeoutError`=タイムアウト / `RuntimeError`=API/フォーマットエラー）: `OCRProvider` 基底の共通例外規約へ昇格する素地。
- `OCRMixin._start_ocr`（ocr.py:284）の settings 読み出し（url/model/preset/scale/timeout/max_tokens/temperature/concurrency クランプ）: プロバイダ選択を挟む拡張点。

### Established Patterns
- Mixin パターン（`OCRMixin` を `PDFEditorApp` が統合）: `ocr_providers.py` は Mixin ではなく Provider クラス群を集約する新規モジュール。`OCRMixin` 側がプロバイダを生成・利用する。
- スレッド安全パターン: 背景スレッド → `self.after(0, ...)` でメインスレッドへ UI 更新を委譲。レンダリングをメインスレッドへ移す際もこの作法を維持（D-03）。
- 設定永続化は `pagefolio_settings.json`（`_save_settings()`）。Phase 4 では `ocr_provider` enum は Phase 5 で導入のため、ここでは LM Studio 既定動作を壊さない範囲に留める。

### Integration Points
- `OCRDialog._worker`（ocr_dialog.py:439-522）: レンダリング段をメインスレッドへ分離し、API 段は `run_parallel(provider, ...)` 呼び出しへ差し替える主たる結合点。
- `OCRMixin._start_ocr` / OCRDialog 生成（ocr.py:305）: 将来のプロバイダ選択を受けられるよう、LM Studio Provider を組み立てて渡す結合点。
- `has_embedded_text()` の呼び出し位置: レンダリング前（メインスレッド）に各ページを判定し、テキストありページは Vision 経路から除外して結果辞書へ直接投入。

</code_context>

<specifics>
## Specific Ideas

- スレッド境界の判定: 「ワーカースレッド内に `fitz`/`get_pixmap()` の直接呼び出しがゼロ」を grep 等で機械的に確認できる状態をゴールとする（成功基準3）。
- `run_parallel()` の一般化は、Provider の `ocr_image(b64_png) -> text` を per-page で呼ぶ形に揃える。Provider 差し替えだけで並列 OCR が動くこと（成功基準4）を最小実装で示す。
- テキスト埋め込みスキップは「多くのケースでコスト・待ち時間がゼロ」になる効果が狙い（設計仕様 §4.2）。混在 PDF でページごとに API 呼び出し有無が分岐する点をテスト観点として意識。

</specifics>

<deferred>
## Deferred Ideas

- **逐次レンダリング化（render→送信→破棄のページ単位逐次化）** → Phase 6（OCR-PERF-02）。Phase 4 の事前レンダリング最小構成を土台に発展させる。
- **`ocr_scale` デフォルト 1.5 化 + トレードオフ UI 表示** → Phase 6（OCR-PERF-05）。
- **クラウドプロバイダ別並列度の実値（Gemini=1 / Claude=2）と 429/5xx 指数バックオフ** → Phase 5/6（OCR-PERF-03/04）。Phase 4 ではポリシーの「持ち方」（D-10）だけを用意。
- **`ocr_provider` enum・プロバイダ選択 UI・APIキー未設定エラー・キーガード** → Phase 5（OCR-SEC/OCR-UI 群）。
- **本格的な多言語文言整備（プロバイダ名・コスト警告・精度注記）・README/開発履歴更新** → Phase 7（OCR-QA-02）。Phase 4 はスキップ通知文言の最小追加のみ。
- **OCR モックテスト（payload 構築・レスポンス解析）の本格整備（`tests/test_ocr.py`）** → Phase 6（OCR-QA-01）。ただし Phase 4 のリファクタで後方互換を担保する最小テスト（埋め込みスキップ・`run_parallel` 動作）は計画時に検討余地あり。

None beyond the above — discussion stayed within phase scope.

</deferred>

---

*Phase: 4-provider-abstraction*
*Context gathered: 2026-06-06*
