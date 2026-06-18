# Phase 6: Gemini Provider + 逐次レンダリング最適化 - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Gemini で OCR が実行でき、低スペック PC でも全ページ OCR 時のメモリ使用量が許容範囲に収まる状態を届けるフェーズ。Phase 5 で整えた Provider 抽象・`build_provider`・バックオフ共通層（`OCRRetryableError`）・コスト確認ゲート・プロバイダ選択 UI の上に、GeminiProvider・ページ単位の逐次レンダリング（メモリ最適化）・`ocr_scale` 既定見直し・OCR モックテストを載せる。

**このフェーズで作るもの（要件）:**
- **OCR-API-02**: `GeminiProvider`（`generateContent`・`inline_data`・モデル一覧・`GEMINI_API_KEY`/`GOOGLE_API_KEY`）。`build_provider` の `gemini` 分岐。
- **OCR-PERF-02**: 全ページ一括保持（現状の `self._images` 辞書蓄積）を廃止し、ページ単位の render→送信→破棄でメモリ上限を保証する。
- **OCR-PERF-05**: `ocr_scale` のデフォルトを 1.5 に見直し、コスト/速度↔精度のトレードオフヒントを UI に表示する。
- **OCR-QA-01**: 各 Provider の payload 構築・レスポンス解析・テキスト埋め込みスキップ判定をモックでテスト（`tests/test_ocr.py` ほか）。逐次レンダリングのメモリ非蓄積リグレッションも含む。

**このフェーズで作らないもの（スコープ外 → 別フェーズ）:**
- TesseractProvider・PluginManager 登録フック（`register_ocr_provider`）・本格的な多言語文言整備・README/開発履歴更新 → Phase 7（OCR-EXT-01/02・OCR-QA-02）
- OS キーストア連携（Windows Credential Manager）によるキー永続化 → 次マイルストーン（Out of Scope）

**絶対条件:**
- **成功基準2**: 100 ページの PDF で OCR 実行中に全ページの base64 画像が同時にメモリに乗らない（ページ単位レンダリング→送信→破棄）。
- **スレッド境界の維持（Phase 4 D-03）**: ワーカースレッド内に `fitz.Document`/`get_pixmap()` の直接呼び出しが一切存在しない。fitz レンダリングはメインスレッド（生産者）、API 呼び出しはワーカー（消費者）。
- **後方互換**: LM Studio / Claude の既存挙動・UI 操作・APIキーガード（成功基準1）を壊さない。

</domain>

<decisions>
## Implementation Decisions

### 逐次レンダリング方式（OCR-PERF-02・成功基準2）
- **D-01:** メモリ上限の保証方式は **上限付きバッファ（producer-consumer）**。メインスレッドが先読みレンダリングして上限 N 枚の境界付きキューに積み、ワーカーが消費したら破棄する。完全逐次（render1→send1）や「クラウドのみ逐次・ローカル現状維持」は不採用 — メモリ上限を保ちつつ LM Studio の並列度（最大 8）も維持でき、Phase 4 のスレッド境界（fitz=生産者/メイン・API=消費者/ワーカー）が方式と自然に整合するため。
- **D-02:** バッファ上限は **並列度連動**（例: `concurrency + 余裕分`）。ワーカーが飢えず、かつクラウド（並列 1-2）では極小・LM Studio（8）でも上限が効く。固定小数は LM Studio 高並列時にワーカーが部分的に飢えるため不採用。具体的な余裕分の係数は Claude 裁量。
- **D-03:** 進捗 UI は **統合プログレス**（「処理済み X/総数」の単一バー）。逐次化でレンダリングと送信が並行するため、OCR 完了ページ数を主軸にする。現状の「レンダリング中 cur/total」→「OCR 中 done/total」の 2 段表示は廃し、スキップページ（埋め込みテキスト）も処理済みに含めて数える。
- **D-04:** Phase 4 D-03 の「ワーカー内 fitz アクセスゼロ」は **必達**。現行 `ocr_dialog.py` の `_render_next_page`（メインスレッドで `page_to_png_b64`）と `_worker`（`run_parallel` 委譲）の責務分担を踏襲しつつ、「全ページ render 完了→worker 起動」の直列フローを producer-consumer の重なり実行へ作り替える。背景スレッド→`self.after(0, ...)` の UI 更新作法は維持。

### Gemini Provider（OCR-API-02 / OCR-API-03）
- **D-05:** `GeminiProvider` は `ClaudeProvider`/`LMStudioProvider` と同じテンプレート（`__init__` 設定注入・`_build_payload`・`ocr_image`・`list_models`）で実装。STACK.md の Gemini 仕様に厳密に従う: エンドポイント `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`、認証は **`x-goog-api-key` ヘッダー方式**（URL クエリパラメータは採用しない — ログ/プロセスリスト漏洩回避）、画像は `inline_data: {mime_type, data}`、レスポンスは `candidates[].content.parts[].text` を走査して結合。
- **D-06:** API キーの環境変数解決は **`GEMINI_API_KEY` 優先 → 未設定なら `GOOGLE_API_KEY` フォールバック**（STACK.md / 設計仕様 §確定）。`OCRAPIKeyError` の明示エラーは「環境変数 `GEMINI_API_KEY` が未設定です」を主表示（フォールバック名も併記の余地は Claude 裁量）。キーは Phase 5 のセッションメモリ + `build_provider(api_key=...)` 注入経路を再利用し、`settings`/`os.environ` に書かない。
- **D-07:** 並列度は **Gemini=1**（`default_concurrency=1`/`max_concurrency=1`・OCR-PERF-03）をクラス属性で宣言。429/5xx は Phase 5 のバックオフ共通層（`OCRRetryableError(retry_after)`）にそのまま乗せる（`Retry-After` 優先・最大 3 回）。
- **D-08:** 推奨デフォルトモデルは **`gemini-2.5-flash` 主推奨**（コスト効率・OCR メイン）、`gemini-2.5-pro` を選択肢（高精度・複雑レイアウト）。`RECOMMENDED_MODELS` に静的保持し、「モデル更新」ボタン押下時のみ `/v1beta/models` を `supportedGenerationMethods` に `generateContent` を含むものでフィルタして上書き（D-08/Phase 5 踏襲）。旧プレビュー ID（`gemini-2.5-flash-preview-09-2025` 等・廃止予定）は使わない。

### Gemini パラメータ UI（OCR-API-02 + OCR-UI 連携）
- **D-09:** Gemini は **temperature 欄のみ表示**し、`thinkingBudget=0` を送って thinking を**明示無効化**する。OCR 用途に思考は不要で、flash の既定 ON によるコスト/レイテンシ増を回避するため。Phase 5 の effort/temperature 切替枠を thinking budget 欄として流用する案は不採用（OCR では過剰）。`thinkingConfig` の正確なフィールド配置（`generationConfig` 配下）はリサーチ/実装で確認（Claude 裁量）。
- **D-10:** Gemini 用の payload 構築責任は **Provider 内に集約**（Phase 5 D-16 の方針踏襲）。`generationConfig.temperature` と `thinkingConfig.thinkingBudget=0` を Provider が組み立てる。`llm_config.py` の provider 切替は Phase 5 の枠組み（D-07/D-17）に gemini 分岐を追加する形。

### ocr_scale 既定見直し（OCR-PERF-05）
- **D-11:** `DEFAULT_SETTINGS["ocr_scale"]` を **2.0 → 1.5** に変更。既存ユーザー（`llm_config` 保存時に 2.0 を明示保存済み）の保存値は **据え置き**（ワンタイム書き換えはしない）。後方互換最大・ユーザーの明示選択を尊重し、新規ユーザーのみ 1.5 既定の恩恵を受ける。既存ユーザーは UI ヒントで 1.5 へ誘導。
- **D-12:** トレードオフヒントは **設定欄（`llm_config.py` の `ocr_scale` スライダー近傍）に常設の短い説明**を置く（例:「低=速い/安い・高=精度、低スペックは 1.5 推奨」）。ツールチップ（Tkinter 標準なし・実装追加が必要・初見で気づかれにくい）やコスト確認ダイアログ併記（文言肥大）は不採用。文言は `lang.py` に日英で追加（Phase 7 の本格整備とは別の最小追加）。

### OCR モックテスト（OCR-QA-01）
- **D-13:** **逐次レンダリングのメモリ非蓄積リグレッションテストを入れる**。`FakeProvider` の `ocr_image` 呼び出し時点で同時保持される画像数が上限（並列度連動）を超えないことを機械的に検証し、成功基準2 を守る網にする。producer-consumer ロジックは Tk/スレッド非依存に切り出せる形で実装し、テスト可能性を確保する（切り出しの具体は Claude 裁量）。
- **D-14:** Gemini モックテストは **既存 LMStudio/Claude パターン踏襲で主要 4 点**: ① payload 構築（`inline_data`・`x-goog-api-key` ヘッダー・`thinkingBudget=0`）② レスポンス解析（`candidates[].content.parts[].text` 結合）③ `list_models`（`supportedGenerationMethods` フィルタ）④ dual env var 解決（`GEMINI_API_KEY`→`GOOGLE_API_KEY`）。テキスト埋め込みスキップ判定は既存 `has_embedded_text` テストを確認・補完。

### Claude's Discretion
- producer-consumer のバッファ上限の余裕係数（D-02）・キュー/Queue 実装の具体形・キャンセル時の in-flight ページ処理（D-01/D-04）
- `OCRAPIKeyError` のフォールバック env 名併記の有無（D-06）
- Gemini `thinkingConfig.thinkingBudget` の正確なフィールド配置・generationConfig 構造（D-09）
- バッファ上限テストの切り出し方（producer-consumer を Tk 非依存ヘルパー化するか）（D-13）
- `ocr_scale` ヒント文言の正確な表現（D-12）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 設計の正典・API 仕様（Gemini）
- `.planning/research/STACK.md` §Gemini (Google AI Studio) API — **Phase 6 の最重要参照**。エンドポイント（`/v1beta/models/{model}:generateContent`）、認証（`x-goog-api-key` ヘッダー推奨・URL クエリは漏洩リスクで非推奨）、`inline_data` 画像フォーマット（mime_type/data・20MB 上限）、レスポンス構造（`candidates[].content.parts[].text`）、`list_models`（`/v1beta/models`・`supportedGenerationMethods` フィルタ）、推奨モデル（`gemini-2.5-flash`/`gemini-2.5-pro`・GA stable ID・旧 preview 廃止）、dual env var（`GEMINI_API_KEY`→`GOOGLE_API_KEY`）、`_post_json` 共通骨格。
- `docs/OCRプロバイダ化_見積もり仕様.md` — v1.4.0 全体の確定スコープ。Phase 6 該当: §プロバイダ比較表（Gemini エンドポイント/inline_data/推奨モデル）・§低スペック対策（逐次レンダリング #9・`ocr_scale` 1.5 見直し）。dual env var フォールバック規約（§59）。
- `.planning/research/PITFALLS.md` — メモリ逼迫（逐次レンダリングの根拠）・クラウド並列度抑制（Gemini=1）・429 レート制限の扱い。
- `.planning/research/ARCHITECTURE.md` — `OCRMixin`/`ocr_providers.py` 統合設計・`run_parallel()` 一般化・スレッド境界の位置づけ（producer-consumer 化の土台）。

### 要件・ロードマップ・前フェーズ
- `.planning/ROADMAP.md` §Phase 6 — Goal・Success Criteria（1〜4）・依存（Phase 5 完了前提）。
- `.planning/REQUIREMENTS.md` — Phase 6 担当の 4 要件（OCR-API-02・OCR-PERF-02・OCR-PERF-05・OCR-QA-01）・Out of Scope（SDK 不採用・settings.json 平文保存禁止）。
- `.planning/phases/05-claude-provider-ui/05-CONTEXT.md` — Phase 5 確定事項。**特に D-14（バックオフ共通層 `OCRRetryableError` を Gemini 再利用前提で設計済み）・D-16/D-17（payload 構築の Provider 集約・effort/temperature 欄切替）・D-08（モデル一覧の静的+更新ボタン）・セッションキー注入経路**。
- `.planning/phases/04-provider-abstraction/04-CONTEXT.md` — Phase 4 確定事項。**特に D-03（ワーカー内 fitz アクセスゼロ）・D-02（逐次レンダリングを Phase 6 へ温存）・D-04（base64 PNG 入力契約）・D-05（Provider は画像 in→テキスト out に純化・fitz 判定は Mixin/メインスレッド）・D-10/D-11（並列度クラス属性）**。

### 既存コード（拡張・リファクタ対象）
- `pagefolio/ocr_providers.py` — `OCRProvider` 抽象基底（`ocr_image`/`list_models`・`default_concurrency`/`max_concurrency`・例外規約）・`OCRAPIKeyError(env_var)`・`OCRRetryableError(message, retry_after)`・`LMStudioProvider`/`ClaudeProvider`（payload/レスポンス/list_models 実装テンプレート・`ClaudeProvider` の `_build_payload`/`_supports_effort`/`MODELS_ENDPOINT`/`RECOMMENDED_MODELS`/`EFFORT_MODELS`）。**`GeminiProvider` をここに追加**。
- `pagefolio/ocr.py` — `build_provider(settings, api_key=None)`（`lmstudio`/`claude` 分岐済み・**`gemini` 分岐の追加点**）・`run_parallel`（バックオフ共通層・`on_progress`/`is_cancelled`・fatal/error 区別・**producer-consumer 化との結合点**）・`OCRMixin._start_ocr`・定数 `DEFAULT_OCR_CONCURRENCY=2`/`MAX_OCR_CONCURRENCY=8`/`DEFAULT_OCR_TIMEOUT`/`DEFAULT_OCR_MAX_TOKENS`/`DEFAULT_OCR_TEMPERATURE`。
- `pagefolio/ocr_dialog.py` — `OCRDialog`・**`_render_next_page`（メインスレッドで `page_to_png_b64(page, scale=self._ocr_scale)` → `self._images[page_idx]` に蓄積：逐次化の主改修点）**・`_start_worker_thread`/`_worker`（`run_parallel` 委譲・`self._images`/`self._ocr_page_indices` を渡す）・`on_progress`（「待機中」表示・統合プログレス化の組込先）・`self._images = {}`（line 80・全ページ保持の元凶）・`self._skipped_pages`/`has_embedded_text` 統合。
- `pagefolio/settings.py` — `DEFAULT_SETTINGS`（`ocr_scale: 2.0`（**→ 1.5 へ変更**）・`ocr_provider: "off"`）・`_save_settings`（キーガード前提・`settings` 辞書をそのまま JSON 化）。
- `pagefolio/dialogs/llm_config.py` — OCR 設定欄（`ocr_scale_var`（DoubleVar・既定 2.0・**1.5 へ既定変更とヒント常設の追加先**）・`1.0〜4.0` クランプ保存（line 620 周辺）・provider ドロップダウン/モデル更新/effort・temperature 欄切替（Phase 5・**gemini 分岐追加点**）。
- `pagefolio/lang.py` — 文言辞書。`ocr_scale_short`/`settings_ocr_scale`・`ocr_progress_render`/`ocr_progress_ocr`（統合プログレス化で見直し）・`ocr_waiting_retry`。**Gemini 名・dual env var エラー・`ocr_scale` トレードオフヒントの日英最小追加**。
- `pagefolio/ocr.py` の `page_to_png_b64` — PDF→PNG base64 変換（scale 引数）。逐次化後もこのヘルパーを生産者側で利用。

### 既存テスト（拡張対象）
- `tests/test_ocr.py` — `FakeProvider`・`TestPageToPngB64`・`TestLMStudioProviderPayload`（payload/レスポンス検証パターン）。**Gemini テストと逐次レンダリングのメモリ非蓄積テストの追加先**。
- `tests/test_ocr_providers.py` — `TestOCRProviderAbstract`・`TestOCRAPIKeyError`・`TestLMStudioProvider*`（基本属性・`ocr_image`・payload・接続エラー）。**`GeminiProvider` の同型テスト追加先**。
- `tests/conftest.py` — `sample_pdf_doc` 等の共通フィクスチャ。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OCRRetryableError(message, retry_after)`（ocr_providers.py:66）: Phase 5 で「Gemini（並列度 1・同じ 429 リスク）を見越して」プロバイダ非依存に設計済み。GeminiProvider はこの契約で 429/5xx を投げるだけでよい。
- `_post_json` 共通骨格（STACK.md・3 プロバイダ共通の urllib POST + 例外正規化）: Gemini もこれで実装。HTTPError→RuntimeError / socket.timeout→TimeoutError / URLError→ConnectionError + retryable 判定。
- `ClaudeProvider`（ocr_providers.py:203）: `_build_payload`/`ocr_image`/`list_models`/`RECOMMENDED_MODELS`/能力マップ（`EFFORT_MODELS`）の実装テンプレート。GeminiProvider はヘッダー（`x-goog-api-key`）・payload（`contents[].parts[].inline_data` + `generationConfig` + `thinkingConfig`）・レスポンス解析（`candidates[].content.parts[].text`）・モデル ID 静的リストだけ差し替えれば書ける。
- `build_provider`（ocr.py）: `claude` 分岐の隣に `gemini` 分岐を追加。`_start_ocr` 側は ValueError を try/except 済み（Phase 4 CR-01）。
- `_render_next_page`/`_worker` の責務分担（ocr_dialog.py）: 「fitz はメインスレッド・API はワーカー」の境界は producer-consumer 化後も維持できる土台。現状は「全 render 完了→worker」の直列だが、生産者（render）と消費者（API）を重ねて走らせる形に作り替える。
- `llm_config.py` の Var + クランプ保存パターン（`ocr_scale_var` を `max(1.0, min(4.0, ...))`）: 既定変更・ヒント常設・gemini 欄追加も同パターン。

### Established Patterns
- Provider クラス属性で並列度宣言（Phase 4 D-10）: GeminiProvider は `default_concurrency=1`/`max_concurrency=1`。`run_parallel` がクランプ。
- スレッド安全パターン: 背景スレッド → `self.after(0, ...)` でメインスレッドへ UI 更新を委譲（Pitfall 3）。逐次化の進捗更新・統合プログレスもこの作法に乗せる。
- バックオフ共通層は `run_parallel` 内で一元管理（Phase 5 D-14）。Gemini は Provider が retryable を投げるだけ。
- 関数内 import で循環 import 回避（`build_provider`/`_start_ocr` 前例）。GeminiProvider の import も同様。
- APIキー非永続化（Phase 5 D-01）: `build_provider(api_key=...)` 注入・`settings`/`os.environ`/ログ/結果にキーを出さない。Gemini でも同一規約を厳守。

### Integration Points
- `build_provider`（ocr.py）/ `_start_ocr`: provider 選択・キー解決（env or セッション属性）・provider へのキー注入の結合点。`gemini` 分岐を追加。
- `OCRDialog._render_next_page` ↔ `_worker`/`run_parallel`: producer-consumer 化の中核。`self._images` 一括辞書を上限付きバッファ（キュー）へ置き換える。
- `llm_config.py`: provider ドロップダウンへ gemini 分岐・temperature 欄・`ocr_scale` 既定/ヒント。
- `lang.py`: Gemini 名・dual env var エラー・`ocr_scale` ヒントの日英文言。

</code_context>

<specifics>
## Specific Ideas

- 成功基準2の検証観点: 「`ocr_image` 呼び出し時点で同時に保持される画像数 ≤ 並列度連動の上限」を `FakeProvider` で機械的に確認（D-13）。100 ページでも全 base64 が同時にメモリに乗らないことをテストで保証する。
- GeminiProvider の payload は STACK.md §Gemini の `inline_data` フォーマット（`mime_type: "image/png"` / `data: <base64>`）に厳密に従う。`contents[].parts[]` に画像とプロンプトテキストを並べる。
- thinking は `thinkingConfig.thinkingBudget=0` で明示無効化（flash の既定 ON によるコスト/レイテンシ増回避・D-09）。
- 認証は `x-goog-api-key` ヘッダーのみ（URL クエリ `?key=` は採用しない・ログ漏洩回避・D-05）。
- `ocr_scale` 既定は 1.5 へ。既存保存値は触らない（D-11）。ヒントは設定欄常設の短文（D-12）。

</specifics>

<deferred>
## Deferred Ideas

- **キャンセル時の in-flight ページ処理の細部** → 計画/実装段階で詰める（Claude 裁量・D-01/D-04）。既存 `_cancel_flag` ハンドリングを producer-consumer に合わせて整合させる。
- **Gemini の 20MB inline_data 上限超過時の挙動** → 通常の PDF ページ（PNG 変換後）では問題にならない（STACK.md）。極端な高解像度ページのガードは必要なら計画時に検討。`ocr_scale` 1.5 既定化はこの上限にも有利。
- **TesseractProvider・PluginManager 登録フック（`register_ocr_provider`）・本格的な多言語文言整備・README/開発履歴更新** → Phase 7（OCR-EXT-01/02・OCR-QA-02）。
- **OS キーストア連携（Windows Credential Manager）によるキー永続化** → 次マイルストーン（Out of Scope）。
- **`ocr_scale` の既存ユーザーへのワンタイム移行** → 今回は不採用（D-11・据え置き）。将来「旧既定値と一致するなら移行」を再検討する余地は残る。

None beyond the above — discussion stayed within phase scope.

</deferred>

---

*Phase: 6-gemini-provider*
*Context gathered: 2026-06-07*
