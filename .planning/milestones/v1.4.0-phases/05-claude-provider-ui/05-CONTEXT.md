# Phase 5: Claude Provider + セキュリティ基盤 + プロバイダ選択 UI - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

クラウド OCR（まず Claude）を **安全に** 実行できる土台を作るフェーズ。Phase 4 で整えた Provider 抽象・`build_provider`・並列度ポリシー機構（`OCRProvider` クラス属性）の上に、ClaudeProvider・APIキーガード・プロバイダ選択 UI・コスト確認ダイアログ・クラウド向けバックオフを載せる。

**このフェーズで作るもの（要件）:**
- OCR-SEC-01/02/03: APIキーを `settings.json` / `os.environ` に書かないガード・未設定時の明示エラー・保存されないセッションメモリ入力欄
- OCR-API-01/03: `ClaudeProvider`（messages API・urllib 直叩き）・プロバイダ別モデル一覧取得
- OCR-UI-01/02/03/04: SettingsDialog でのプロバイダ選択・off で OCR ボタン無効化・クラウド実行前のコスト確認ダイアログ・モデル別パラメータ（effort/temperature）防御
- OCR-PERF-03/04: クラウド並列度抑制（Claude=2）・429/5xx 指数バックオフ（最大3回・Retry-After 優先）

**このフェーズで作らないもの（スコープ外 → 別フェーズ）:**
- GeminiProvider・逐次レンダリング化・`ocr_scale` デフォルト 1.5 化 → Phase 6（OCR-API-02 / OCR-PERF-02/05）
- OCR モックテストの本格整備（`tests/test_ocr.py`）→ Phase 6（OCR-QA-01）※Phase 5 のリファクタを守る最小テストは計画時に検討余地あり
- TesseractProvider・PluginManager 登録フック・本格的な多言語文言整備・README/開発履歴更新 → Phase 7（OCR-EXT / OCR-QA-02）
- OS キーストア連携（Windows Credential Manager）によるキー永続化 → 次マイルストーン（Out of Scope）

**絶対条件:**
- **`pagefolio_settings.json` に APIキー相当のフィールドが一切書き込まれない**（最優先・成功基準1）。`_save_settings()` は `settings` 辞書をそのまま JSON 化するため、キーが `settings` 辞書へ一度でも入れば漏洩する点が設計の急所。
- LM Studio の既存挙動・後方互換を壊さない（Phase 4 の成功基準1を維持）。

</domain>

<decisions>
## Implementation Decisions

### セキュリティ／APIキーの持ち方（OCR-SEC-01/02/03 — 最優先）
- **D-01:** セッション中の API キーは **App の専用一時属性**（例: `self._session_api_keys`）に保持する。`settings` 辞書とは **別オブジェクト** とし、`_save_settings()` は `settings` のみを保存するため構造的にキーが混入しない。属性はプロセス終了で消滅する。
- **D-02:** キー解決の優先順位は **環境変数優先**。`ANTHROPIC_API_KEY` があればそれを使い、**未設定時のみ** セッション入力欄の値を使う。「環境変数が正＝チーム共有設定」という自然なメンタルモデル。
- **D-03:** セッションキー入力欄は **実行時ダイアログ内** に出す。**クラウドプロバイダ選択かつキー未設定時のみ** 表示する（必要な時だけ出る動線）。OCR 実行前（コスト確認ダイアログ等）の段で入力させる。
- **D-04:** 入力欄は **マスク表示**（`show="*"`）。キー値を **ログ・OCR結果・エラーメッセージに一切出さない**。
- **D-05:** `os.environ` への書き込みも行わない（セッション属性のみ・OCR-SEC-03 明記事項）。キーは `build_provider` 経由で Provider に注入する（環境変数 or セッション属性の解決結果を渡す）。
- **D-06:** キー未設定でクラウド OCR を実行しようとした場合、**実行前に明示エラー**を表示し処理を開始しない（OCR-SEC-02・`OCRAPIKeyError` が既に Phase 4 で定義済み・環境変数名を保持）。

### プロバイダ選択とモデル一覧（OCR-UI-01/02 + OCR-API-03）
- **D-07:** プロバイダ選択 UI は **`dialogs/llm_config.py` に集約**する（既存の OCR 設定欄と同居）。先頭に provider ドロップダウン（off / gemini / claude / lmstudio / tesseract）を置き、**選択に応じて下位欄**（URL / モデル / temperature / effort 等）を切り替える。
- **D-08:** モデル一覧は **各 Provider に推奨モデルの静的リスト**を持たせ（STACK.md の `claude-haiku-4-5` / `claude-sonnet-4-6` / `claude-opus-4-8` 等）、**「モデル更新」ボタン押下時のみ** `list_models` で API 取得して上書きする。キー未設定・オフラインでも選択肢が出る（黙って空リストにならない）。
- **D-09:** `ocr_provider: "off"`（既定）のとき **OCR 関連ボタンを `disabled` 化**し、ツールチップ/ステータスで「設定でプロバイダを選択」へ誘導する。off では外部送信・課金が一切発生しない（OCR-UI-02）。

### コスト確認ダイアログ（OCR-UI-03）
- **D-10:** 概算コストは **ページ数 × モデル別概算単価の粗い範囲表示**（「約 $X 程度」）。STACK.md の MTok 価格表（Claude: haiku $1/$5・sonnet $3/$15・opus $5/$25）を根拠に、画像入力トークン + 想定出力トークンの粗い見積もりで算出する。具体的な見積もり係数は Claude 裁量。
- **D-11:** 「今後表示しない」オプションは **設けない**。クラウド実行のたびに **毎回確認**する（コスト事故・誤送信の確実な防止を優先）。
- **D-12:** プライバシー注記は **3点を明示**: ① 送信先ホスト名（例: `api.anthropic.com`）② 「ページ画像が外部 API に送信される」 ③ 「従量課金が発生する」。
- **D-13:** ダイアログは **クラウド（claude / gemini）のみ**。lmstudio / tesseract / off には表示しない（OCR-UI-03）。**キャンセルで中止**できる（成功基準5）。

### バックオフとモデル別パラメータ防御（OCR-PERF-04 + OCR-UI-04）
- **D-14:** 429/5xx の指数バックオフは **`run_parallel` 共通層**で行う。Provider は「リトライ可（`retry_after` 付き）」を **型付き例外**（例: `OCRRetryableError`、`OCRProvider` の例外規約に追加）で伝え、`run_parallel` が sleep / 回数管理（**最大3回**）/ 進捗表示を一元管理する。Phase 6 の Gemini でそのまま再利用できる。`Retry-After` ヘッダがあれば優先。
- **D-15:** 「待機中」UI は **既存 `on_progress` コールバック**で該当ページを「待機中（リトライ n/3）」と表示する。既存 OCRDialog の進捗 UI に乗せるだけで追加実装を最小化（成功基準8）。
- **D-16:** effort/temperature の送信判定は **Provider 内の能力判定**（モデル ID のプレフィックス / 能力マップ）で持つ。非対応モデル（**Haiku は `effort` 非対応**）には effort を送らない。payload 構築責任を Provider に集約する。**注意:** STACK.md 確定事項 — `temperature` は全モデルで利用可（仕様書 §3「Opus 不可」は誤り）。`effort` は `output_config.effort`（トップレベルの兄弟フィールド）として送る。
- **D-17:** effort パラメータは **effort 対応モデル選択時のみ** UI に effort 欄（`low`/`medium`/`high`/`xhigh`/`max`）を表示し、非対応時は temperature 欄に切り替える（OCR-UI-04「effort を提示」に合致）。OCR 用途では `effort: "low"` を既定推奨。

### Claude's Discretion
- セッションキー属性の具体的なデータ構造（プロバイダ別 dict か単一値か・D-01）
- コスト見積もりの係数・トークン換算の粗さ（D-10）
- `OCRRetryableError` の正確な型名・`run_parallel` への組み込み方（既存の fatal/error 区別構造との統合・D-14）
- モデル能力マップの実装形（プレフィックス判定 vs 明示 dict・D-16）
- effort/temperature 欄の UI 切替の具体的なウィジェット実装（D-17）
- Claude payload の `max_tokens` 既定値（STACK.md は 4096 を例示）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 設計の正典・API 仕様
- `.planning/research/STACK.md` — **Phase 5 の最重要参照**。Claude messages API（エンドポイント・ヘッダー `x-api-key`/`anthropic-version: 2023-06-01`・base64 画像フォーマット・レスポンス解析・`/v1/models` の `capabilities.image_input`）、`temperature`/`effort` の正しい仕様（**仕様書 §3 の「Opus は temperature 不可」は誤り・全モデル可**／`effort` は `output_config.effort`・Haiku 非対応）、モデル ID・価格表（コスト見積もりの根拠）、urllib 直叩き共通骨格 `_post_json`、環境変数規約。
- `docs/OCRプロバイダ化_見積もり仕様.md` — v1.4.0 全体の確定スコープ。Phase 5 該当: §2.2 Claude Provider・§2.3 セキュリティ（キーガード）・コスト確認ダイアログ・セッションキー入力欄。**ただし §3 の Claude パラメータ記述は STACK.md で上書きする**（temperature/effort）。
- `.planning/research/PITFALLS.md` — Pitfall #2/#3（メモリ・並列度）はクラウド並列度抑制（OCR-PERF-03）の根拠。429 レート制限の扱い。
- `.planning/research/ARCHITECTURE.md` — `OCRMixin` / `ocr_providers.py` 統合設計・`run_parallel()` 一般化の位置づけ（バックオフ共通層 D-14 の土台）。

### 要件・ロードマップ・前フェーズ
- `.planning/ROADMAP.md` §Phase 5 — Goal・Success Criteria（1〜8）・依存（Phase 4 完了済み）。
- `.planning/REQUIREMENTS.md` — Phase 5 担当の 11 要件（OCR-SEC-01/02/03・OCR-API-01/03・OCR-UI-01/02/03/04・OCR-PERF-03/04）・Out of Scope（settings.json 平文保存禁止・SDK 不採用）。
- `.planning/phases/04-provider-abstraction/04-CONTEXT.md` — Phase 4 確定事項（D-04 base64 入力契約・D-10 並列度クラス属性・例外規約・`build_provider` 拡張点）。

### 既存コード（拡張・リファクタ対象）
- `pagefolio/ocr_providers.py` — `OCRProvider` 抽象基底（`ocr_image()`/`list_models()`・例外規約・`default_concurrency`/`max_concurrency`）・`OCRAPIKeyError`（環境変数名保持）・`LMStudioProvider`（payload 構築・urllib 呼び出しの実装パターン）。**ClaudeProvider をここに追加**。
- `pagefolio/ocr.py` — `build_provider(settings)`（179行・`claude` 分岐を追加する拡張点）・`run_parallel`（83行・バックオフ共通層 D-14 の組込先）・`OCRMixin._start_ocr`（226行・provider 生成・concurrency クランプ・キー解決の結合点）・定数 `DEFAULT_OCR_CONCURRENCY=2`/`MAX_OCR_CONCURRENCY=8`。
- `pagefolio/ocr_dialog.py` — `OCRDialog`・`_worker`（API 段の `run_parallel` 委譲）・`on_progress` 連携（「待機中」表示 D-15 の組込先）・コスト確認/セッションキー入力欄（D-03/D-10〜D-13）の追加先。
- `pagefolio/settings.py` — `load_settings`（DEFAULT_SETTINGS・`ocr_provider: "off"` 既定）・`_save_settings`（**キーガードの観点で重要**: `settings` 辞書をそのまま JSON 化する。D-01 の「別オブジェクト保持」が前提）。
- `pagefolio/dialogs/llm_config.py` — 既存 OCR 設定欄（`ocr_scale`/`ocr_max_tokens`/`ocr_temperature`/`ocr_concurrency` の各 Var とクランプ保存）。**provider ドロップダウン・モデル選択・effort 欄切替（D-07/D-08/D-17）の追加先**。
- `pagefolio/dialogs/settings.py` — `SettingsDialog`（上位ダイアログ）。
- `pagefolio/lang.py` — 文言辞書（`ocr_provider_unsupported` 等の既存キー）。Phase 5 で必要な最小文言（キー未設定エラー・コスト注記・待機中）を追加。本格的な多言語整備は Phase 7。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OCRAPIKeyError(env_var)`（ocr_providers.py）: Phase 4 で先行定義済み。環境変数名を保持。OCR-SEC-02 の明示エラーにそのまま使える。
- `LMStudioProvider`（ocr_providers.py）: `__init__` での設定注入・`_build_payload`・`ocr_image`・`list_models` の実装テンプレート。ClaudeProvider は同じ形（ヘッダー・payload・レスポンス解析だけ差し替え）で書ける。
- STACK.md の `_post_json(endpoint, payload, headers, timeout)` 共通骨格: 3プロバイダ共通の urllib POST + 例外正規化（HTTPError→RuntimeError / socket.timeout→TimeoutError / URLError→ConnectionError）。ClaudeProvider と将来の Gemini で共用できる。
- `run_parallel`（ocr.py:83）: ThreadPoolExecutor 駆動・concurrency クランプ・`on_progress`/`is_cancelled` コールバック・fatal/error 区別。バックオフ共通層（D-14）はこの fatal/error 区別に「retryable」を一段追加する形で組み込める。
- `build_provider`（ocr.py:179）: `name in ("lmstudio","","off")` 分岐 + `raise ValueError(未対応)`。`claude` 分岐をここに追加。`_start_ocr` 側は ValueError を既に try/except 済み（Phase 4 CR-01）。
- `dialogs/llm_config.py` の Var + クランプ保存パターン（`ocr_scale_var` 等を `max(min(...))` で clamp して `llm_settings[...]` に格納）: provider/effort 欄も同パターンで追加できる。

### Established Patterns
- Provider クラス属性で並列度宣言（D-10・Phase 4）: ClaudeProvider は `default_concurrency=2 / max_concurrency=2` を宣言（OCR-PERF-03 の Claude=2）。`run_parallel` がクランプ。
- スレッド安全パターン: 背景スレッド → `self.after(0, ...)` でメインスレッドへ UI 更新を委譲。「待機中」進捗（D-15）もこの作法に乗せる。
- 設定永続化は `pagefolio_settings.json`（`_save_settings`）が `settings` 辞書全体を JSON 化。**キーを settings に入れない（D-01）が唯一かつ最重要のガード手段**。テストで「保存後の JSON にキー文字列が含まれない」ことを機械的に確認できる状態が望ましい（成功基準1）。
- 関数内 import で循環 import を回避（`build_provider` / `_start_ocr` の前例）。

### Integration Points
- `OCRMixin._start_ocr`（ocr.py:226）/ `build_provider`（ocr.py:179）: provider 選択・キー解決（環境変数 or セッション属性）・provider へのキー注入の主たる結合点。
- `OCRDialog`（ocr_dialog.py）: コスト確認ダイアログ・セッションキー入力欄（クラウド選択かつ未設定時のみ）の表示位置。実行直前にキャンセル可能なゲートを設ける。
- `OCRDialog._worker` → `run_parallel(provider, ...)`: バックオフ共通層（D-14）と「待機中」進捗（D-15）の組込点。
- `dialogs/llm_config.py`: provider ドロップダウン・モデル更新ボタン・effort/temperature 欄切替（D-07/D-08/D-17）の UI 結合点。

</code_context>

<specifics>
## Specific Ideas

- 成功基準1の検証観点: 「保存された `pagefolio_settings.json` にキー文字列が一切含まれない」を grep / テストで機械的に確認できる状態をゴールにする（D-01 の構造的ガードがあれば自然に満たせる）。
- ClaudeProvider の payload は STACK.md §Claude の base64 画像フォーマット（`type: image` / `source.type: base64` / `media_type: image/png`）に厳密に従う。レスポンスは `content[]` の `type=="text"` ブロックを走査して結合。
- effort は `output_config: {effort: "low"}` をトップレベルに並べる（`generationConfig` の中ではない・STACK.md 確認済み）。
- バックオフ共通層は Phase 6 Gemini（並列度1・同じ 429 リスク）での再利用を前提に、プロバイダ非依存の `OCRRetryableError(retry_after)` 契約で設計する。
- コスト確認は「クラウドのみ」「毎回」。off/local/tesseract では一切のゲート・送信が発生しないことをテスト観点に。

</specifics>

<deferred>
## Deferred Ideas

- **GeminiProvider・逐次レンダリング化・`ocr_scale` デフォルト 1.5 化** → Phase 6（OCR-API-02 / OCR-PERF-02 / OCR-PERF-05）。バックオフ共通層（D-14）と Provider テンプレートを Gemini が再利用する。
- **OCR モックテストの本格整備（`tests/test_ocr.py`）** → Phase 6（OCR-QA-01）。Phase 5 では「キー非永続化」「コスト確認ゲート」「ClaudeProvider payload/レスポンス」を守る最小テストの追加余地を計画時に検討。
- **TesseractProvider・PluginManager 登録フック（`register_ocr_provider`）・本格的な多言語文言整備・README/開発履歴更新** → Phase 7（OCR-EXT-01/02 / OCR-QA-02）。
- **OS キーストア連携（Windows Credential Manager）によるキー永続化** → 次マイルストーン（Out of Scope）。Phase 5 はセッションメモリ + 環境変数のみ。
- **セッションキーの複数プロバイダ間での保持構造の細部**（単一値 vs プロバイダ別 dict）→ Claude 裁量（D-01）。Claude のみ実装する Phase 5 では単一でも足りるが、Gemini を見越して dict 設計にする余地。

None beyond the above — discussion stayed within phase scope.

</deferred>

---

*Phase: 5-claude-provider-ui*
*Context gathered: 2026-06-06*
