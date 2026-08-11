# Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

プロバイダメタデータ（キー・表示名・クラウド種別・環境変数・既定モデル・送信先ホスト・フォールバック可否）が単一の情報源（`catalog.py`）から解決される基盤を整備し、その上に OpenAI(ChatGPT) を既存 5 プロバイダと同等の安全境界（セッション限定キー・送信先確認・コスト確認・明示設定型フォールバック）で OCR・バッチ OCR へ追加する。

**対象要件（15件）:** V190-CAT-01, V190-CAT-02, V190-OAI-01, V190-OAI-02, V190-OAI-03, V190-OAI-04, V190-OAI-05, V190-OAI-06, V190-OAI-07, V190-OAI-08, V190-OAI-09, V190-OAI-10, V190-OAI-11, V190-OAI-12, V190-OAI-13

**このフェーズに含まれないもの:**
- Tkinter 実行環境修復・保存トースト再試行時の上書き確認再表示・human-verify/UAT（Phase 3）
- OpenAI Responses API への移行・公式 SDK 導入・organization 自動検出（REQUIREMENTS.md Out of Scope / v2）
- `BatchOCRDialog` から `OCRDialog` へのロジック共通化（継承・メソッド import）— 独立性は意図的な設計判断（Out of Scope）
- `dialogs/llm_config/dialog.py` のセッション API キー同期ループの完全動的化（V190-F-03・v2）

</domain>

<decisions>
## Implementation Decisions

### catalog 一元化の範囲と移行（V190-CAT-01 / V190-CAT-02）

- **D-01:** `pagefolio/ocr_providers/catalog.py` を新設し、**プロバイダ単位のメタデータをすべて集約**する。研究提案の `ProviderMeta`（frozen dataclass・`name` / `display_name_key` / `is_cloud` / `model_setting_key` / `default_model` / `host` / `fallback_eligible`）に加え、**API キー欠落エラーの LANG キー**（現状 `ocr_dialog.py:1298-1301` と `batch_ocr.py:548-551` に同一 dict が二重定義）も 1 フィールドとして持たせる。いずれも「プロバイダ 1 件につき 1 値」で粒度が揃うため。
- **D-02:** `OCR_PRICE_TABLE`（モデル名 → 入力/出力単価）は **catalog に入れない**。プロバイダ単位ではなくモデル単位のデータであり、粒度の異なるものを 1 モジュールへ混在させると catalog の「プロバイダ 1 件 = 1 エントリ」という単純さが崩れるため。`ocr_dialog.py` / `batch_ocr.py` の二重定義は現状維持（Deferred 参照）。
- **D-03:** 既存 6 参照面（`sections.py` の一覧リスト 2 箇所 / `ocr_dialog.py` の表示名・クラウド判定・host 分岐 / `batch_ocr.py` の同型分岐 / `ocr.py` の `_cloud_providers`）の catalog 移行を**本フェーズで完走**する。手順は「catalog.py 単体追加（既存コードから未参照・動作変化ゼロ）→ 1 ファイルずつ置換」の段階移行とし、**一括置換はしない**（表示順や既定値が 1 つズレたときの原因切り分けを可能にするため）。各ステップ完了時点で常に動作する状態を保つ。 — **Reversibility:** costly — 6 ファイルの参照経路を catalog 経由へ切り替えるため、戻すには全ファイルの再修正が必要。以降に追加されるプロバイダもこの契約の上に載る。
- **D-04:** catalog に登録のないプロバイダ（`PluginManager.register_ocr_provider` 経由のサードパーティ製）は `catalog.is_cloud_provider()` が **False（非クラウド）を返す**。あわせて `ocr_dialog.py:905-926` の **isinstance 判定（`ClaudeProvider` 等の継承チェック）をフォールバックとして維持**する。プラグインが既存クラウドプロバイダを継承している場合にコスト確認・送信先確認が消えると、外部送信の明示同意方針が弱まるため。判定経路が 2 本残ることは承知のうえで、安全側を優先する。
- **D-05:** `catalog.py` は **Provider クラス（`ocr_providers/claude.py` 等）を import しない**。`default_model` は catalog 側が自前の値として持ち、`catalog.default_model_for(name)` が対応 Provider の `RECOMMENDED_MODELS` に含まれることを**新設テストで機械保証**する。catalog は `registry.py` の隣に置く「軽量なデータモジュール」という性格を保ち、重い import 連鎖を背負わせない。
- **D-06:** `registry.py` は**一切変更しない**（OpenAI の環境変数追加を除く）。`catalog.py` → `registry.py` の一方向 import のみとし、逆方向は発生させない。環境変数名の解決は `registry.env_vars_for()` へ委譲し catalog では再定義しない（V180-D-01 の独立性制約を将来にわたり守るため、責務を 1 モジュールに混在させない）。

### OpenAI モデル一覧の取得とフィルタ（V190-OAI-03）

- **D-07:** `GET /v1/models` の応答は**モデル ID の命名規則によるヒューリスティックフィルタ**で絞る（チャット/vision 系のみを採用し、embedding・tts・whisper・dall-e・moderation 等を除外）。OpenAI の `/v1/models` には Anthropic のような vision 対応フラグが無く、Claude 方式の自動フィルタが再現できないため。**フィルタは Tk/ネットワーク非依存の純関数に切り出し**、除外パターンを単体テストで固定する。
- **D-08:** フィルタ結果が **0 件になった場合は静的フォールバック一覧（`RECOMMENDED_MODELS`）を返す**。取得失敗時（V190-OAI-03 の「取得に失敗した場合」）と同一経路に合流させ、失敗時パスを 1 本に集約する。将来 OpenAI の命名規則が変わってフィルタが陳腐化しても、ユーザーは常に何かを選べる。
- **D-09:** `RECOMMENDED_MODELS`（静的フォールバック）と `default_model` の**具体的なモデル名は、実装時に実 API キーで `GET /v1/models` を叩いて目視確認してから確定**する。プラン側にこの確認を明示タスクとして含めること。リサーチ時点の推定値をベタ書きすると、存在しないモデル名が既定値になり初回実行が失敗するリスクがある（研究 Gap「OpenAI モデルラインナップの陳腐化」への回答）。実キーが用意できない場合は OpenAI 公式ドキュメントを二次ソースとする。

### パラメータ非互換とエラー処理（V190-OAI-11 / V190-OAI-12 / V190-OAI-13）

- **D-10:** モデル別パラメータ非互換は「**常に新形式を送り、非対応パラメータは省略する**」安全側方式を採る。`max_completion_tokens` を常用し、`max_tokens` は使わない。既存 `GeminiProvider._is_legacy_gemini`（新世代には省略＝省略は全世代で合法）と同型のパターンであり、**未知の新モデルが出ても 400 にならない**。モデル名の完全一致許可リスト（Claude の `EFFORT_MODELS` 方式）は、未知モデルが常に「非対応」判定になり集合の永続的な保守が発生するため不採用。400 応答を見て再送する適応方式も、失敗経路が増えて既存の 429/5xx リトライ基盤と相互作用が複雑になるため不採用。
- **D-11:** `temperature` は「**推論系モデルと判定できたものには送らない**」。判定はモデル ID の命名規則で行い、それ以外へは従来どおり `ocr_temperature` を送る。判定は D-13 と同じ純関数へ集約する。
- **D-12:** エラーマッピングは既存 `pagefolio/ocr_providers/errors.py` の `_raise_mapped_http_error` を**そのまま流用**し、errors.py は原則未変更とする（既に「OpenAI 互換: context_length_exceeded」マーカーを実装済み）。OpenAI 固有のエラー文字列で既存マッピングが不十分と実測で判明した場合のみ `_CONTEXT_ERROR_MARKERS` 等へマーカーを追記する。OpenAI 専用のエラー分岐経路は新設しない（共通基盤の外に 6 本目の分岐を作らない）。
- **D-13:** 「推論系モデルか否か」の判定は**単一の純関数に集約**し、`temperature` の省略（D-11）と reasoning effort 欄の有効化（D-15）の**両方をこの 1 つの判定で駆動**する（推論系 = temperature 省略 + effort 有効）。Phase 1 の D-18（判定経路を 1 本にする）と同じ方針であり、2 つの判定がずれる同型バグを構造的に防ぐ。
- **D-14:** `OpenAIProvider` の並列度は **`default_concurrency = 2` / `max_concurrency = 2`**（Claude 相当）とする。OpenAI のレート制限は tier 依存で、低 tier ユーザーでは 429 が頻発しかねないため保守的な既定にし、超過分は既存の指数バックオフ・`Retry-After` 尊重リトライ基盤に任せる。

### OpenAI 固有設定の UI（V190-OAI-08 / V190-OAI-09 / V190-OAI-10）

- **D-15:** reasoning effort 相当パラメータは **OpenAI 専用のウィジェットと専用 settings キー**（例: `openai_reasoning_effort`）で実装する。Claude の `ocr_effort` / `effort_frame` は流用しない。OpenAI の `reasoning_effort` と Anthropic の `effort` は意味論が異なり取りうる値域も別であるため（研究が「機械的流用は不可」と明記）、共有すると一方の値域変更が他方を壊す。表示条件は D-13 の純関数で駆動する。
- **D-16:** 画像 detail レベルの既定値は **`high`**。OCR 用途では文字の読み取り精度が最優先であり、コスト制御はユーザーが `low` へ下げることで行う（`detail=high` の常時強制は Out of Scope＝選択可能にすることが要件）。設定は永続化する。
- **D-17:** organization / project ID は **OpenAI セクション内の通常項目**（モデル欄・API キー欄の下）として任意入力の 2 欄を置く。既存 5 プロバイダのセクション構成と揃え、折りたたみ UI という新しいパターンをこのフェーズで導入しない。**空のときはリクエストヘッダを一切付与しない**（V190-OAI-10）。
- **D-18:** OpenAI の API キーは既存のセッション限定機構（`_session_api_keys`・`registry.sensitive_keys()` 由来の `_SENSITIVE_KEYS` ガード）に載せる。`registry.PROVIDER_ENV_KEYS` へ `"openai": ("OPENAI_API_KEY",)` を 1 行追加するのみで、`sensitive_keys()` が `openai_api_key` / `OPENAI_API_KEY` / `openai_api_key`(lower) を自動導出する（V190-OAI-02）。org/project ID は機密ではない通常設定として永続化してよい。

### Claude's Discretion

- 新規プロバイダ実装ファイルの名前（`openai_provider.py` / `openai.py`）。研究は前者を推奨（grep・エディタ検索時の紛らわしさ回避）だが技術的な差はない
- `ProviderMeta` の具体的なフィールド名・`catalog.py` の公開関数シグネチャ（`provider_names()` / `fallback_candidate_names()` / `is_cloud_provider()` / `host_for()` / `default_model_for()` 等、研究の設計イメージが叩き台）
- D-07 のヒューリスティックフィルタと D-13 の推論系判定を置くモジュール（`catalog.py` / `openai_provider.py` / 新規純関数モジュールのいずれか）
- `ocr.py:build_provider` の OpenAI 分岐における `max_tokens <= 0`（LM Studio 専用の -1 委譲値）のクランプ値（claude/gemini は 4096 で揃えている）
- catalog 移行の段階（D-03）をどうプラン分割するか（1 ファイル 1 プランか、リスクの近い面をまとめるか）
- OpenAI モデルの `OCR_PRICE_TABLE` 単価エントリの粒度と、未知モデル時の部分一致フォールバックの扱い
- 新設テストのファイル配置（`tests/test_ocr_provider_catalog.py` 新規 / 既存 `tests/test_ocr_providers.py` への追加）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 要件・スコープの一次情報
- `.planning/REQUIREMENTS.md` — V190-* 全 27 要件の定義。Phase 2 は CAT-01/02 + OAI-01〜13 の 15 件。**Out of Scope 表**（公式 SDK 導入・Responses API フル移行・`detail=high` 常時強制・プロバイダ「ロジック」の共通化・OAuth・OS キーストア連携）は必読
- `.planning/ROADMAP.md` §「Phase 2」 — Goal と 5 つの Success Criteria（何が TRUE になれば完了か）
- `.planning/notes/2026-08-10-v1.9.0-existing-feature-review.md` §V190-REV-08 — catalog 一元化要件の出典

### 設計の一次情報（本フェーズの設計はこれを土台にしている）
- `.planning/research/ARCHITECTURE.md` — **最重要**。§1 プロバイダメタデータ重複マップ（クラウド判定 5 箇所・表示名 2 箇所・既定モデル各 5 箇所・host 4 箇所・一覧リスト 2 箇所・API キー欠落キー 2 箇所の具体的なファイル:行）、§2 catalog.py 設計と 7 参照面の段階移行手順、§3 OpenAI 統合ポイント（新規ファイル・修正ファイル一覧）、§7 アンチパターン 3 件
- `.planning/research/SUMMARY.md` — 4 次元リサーチの統合。§Gaps to Address（OpenAI モデルラインナップの実キー確認・モデル一覧フィルタ方式未決定）は D-07/D-09 の背景
- `.planning/research/PITFALLS.md` — 特に **monkeypatch 名前空間断絶リスク**（v1.8.0 Phase 1 の実際の回帰事例。リファクタ後に意図的なバグ注入でテストの検知力を確認すること）
- `.planning/research/STACK.md` / `.planning/research/FEATURES.md` — Chat Completions 採用理由・OpenAI プロバイダの table stakes 一覧

### アーキテクチャ制約（違反すると壊れる）
- `CLAUDE.md` §「既知の制限・注意事項」— **`ocr_providers/registry.py` の独立性制約**（標準ライブラリのみ・pagefolio 内部モジュール非 import）。§「変更時のチェックリスト」— ruff / pytest / 開発履歴.md / APP_VERSION
- `pagefolio/CLAUDE.md` §「OCR・LLM の注意事項」— API キーの扱い・リトライ制御・fitz スレッド制約・外部プロンプトファイル連動・Gemini のパラメータ制限（D-10 の前例）・モデル一覧取得の非同期化とプロバイダ別 `model_list_timeout`
- `.planning/PROJECT.md` §「Key Decisions」— V14-D-01（urllib 直叩き・新規 pip 依存ゼロ）、V14-D-02（API キー非永続）、V14-D-03（既定 `off`）、V180-D-01（registry.py 独立性）、V180-D-02（明示設定型フォールバック）
- `.planning/codebase/CONCERNS.md` — Fragile Areas / OCRDialog LLM Settings Callback Consistency
- `.planning/phases/01-safety-rollback/01-CONTEXT.md` §D-06 — `build_provider()` は `off` を `OCRDisabledError` で拒否する（Phase 1 で確立済みの契約。OpenAI 分岐もこの上に載る）

### 実装対象コード
- `pagefolio/ocr_providers/registry.py` — `PROVIDER_ENV_KEYS` に `"openai"` を 1 行追加（D-18）。それ以外は変更しない（D-06）
- `pagefolio/ocr_providers/lmstudio.py` — **OpenAI 実装の土台**（OpenAI 互換 Vision API を実装済み。payload/response 処理をほぼ流用できる）
- `pagefolio/ocr_providers/claude.py` — `list_models` / `RECOMMENDED_MODELS` / `EFFORT_MODELS` / `model_list_timeout` のクラウド系実装パターン（D-09/D-14/D-15 の対比対象）
- `pagefolio/ocr_providers/gemini.py` — `_is_legacy_gemini` による「新世代にはパラメータを省略する安全側」パターン（D-10 の前例）
- `pagefolio/ocr_providers/errors.py` — `_raise_mapped_http_error` / `_CONTEXT_ERROR_MARKERS`（D-12・原則未変更）
- `pagefolio/ocr_providers/__init__.py` — 新プロバイダの re-export
- `pagefolio/ocr.py:429-500`（`build_provider`）— OpenAI 分岐の追加。`ocr.py:566-570`（`_cloud_providers`）— catalog 移行対象
- `pagefolio/ocr_dialog.py:829-838, 905-926, 1223-1266, 1298-1301, 2303-2350` — 表示名・クラウド判定・host 分岐・API キー欠落マップ（catalog 移行対象 + OpenAI 分岐）
- `pagefolio/dialogs/batch_ocr.py:63, 70-110, 496, 515-522, 548-551, 963-969` — 同型（**ロジック共有はしない・データのみ catalog 経由で共有**）
- `pagefolio/dialogs/llm_config/sections.py:87-95, 413-513, 1024-1031` — 一覧リスト 2 箇所（catalog 移行対象）と Claude セクション（OpenAI セクションの雛形）
- `pagefolio/dialogs/llm_config/dialog.py:229-305, 407-420, 520-524` — `_on_provider_change` / `_model_supports_effort` / API キー同期ループ
- `pagefolio/dialogs/llm_config/model_fetch.py:206-243`（`_refresh_claude_models`）— OpenAI モデル取得の雛形
- `pagefolio/ocr_fallback.py` — フォールバック候補の解決（V190-OAI-07）
- `pagefolio/lang.py` — ja/en 同一キーで追加（キー数の左右一致・未使用キー回帰テストが常設）

### 既存テスト（拡張対象）
- `tests/test_ocr_providers.py` — 既存プロバイダの単体テストパターン。`OpenAIProvider` の payload 構築・レスポンスパース・エラーマッピング・モデル一覧を同型で追加
- `tests/test_provider_ui.py` — プロバイダ選択 UI・combobox の values 検証（catalog 移行時の動作無変更保証）
- `tests/test_ocr_engine.py` — OCR→サマリ E2E モックテスト

### ドキュメント
- `docs/OCR-PROVIDERS.md` / `docs/CONFIGURATION.md` — OpenAI セクションの追記（`OPENAI_API_KEY` 説明含む）

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `LMStudioProvider`（`ocr_providers/lmstudio.py`）: OpenAI 互換 Vision API（`/v1/chat/completions`・`image_url` + base64 data URI・`choices[0].message.content`・`finish_reason == "length"` での途切れ検出）を実装済み。**接続先・認証ヘッダ・モデル一覧取得を差し替えるだけ**で OpenAI 本家に対応できる
- `errors.py:_raise_mapped_http_error` / `_CONTEXT_ERROR_MARKERS`: 既に「OpenAI 互換: context_length_exceeded」を見込んだ実装。429/5xx の指数バックオフ・`Retry-After` 尊重（`clamp_retry_after` / `interruptible_sleep`）ごと流用できる（V190-OAI-13 はほぼ既存基盤の再利用で満たせる）
- `registry.sensitive_keys()`: `PROVIDER_ENV_KEYS` から `{provider}_api_key` / 環境変数名 / その小文字を自動導出。**1 行追加で OpenAI の機密キーガードが完成**する（V190-OAI-02）
- `model_fetch.py:_fetch_models_async`: モデル一覧取得のバックグラウンド実行基盤（UI フリーズ回避）。`_refresh_claude_models` と同型で `_refresh_openai_models` を追加できる
- `GeminiProvider._is_legacy_gemini`: 「新世代にはパラメータを送らない安全側」判定の前例（D-10/D-11 の設計根拠）
- `ClaudeProvider.EFFORT_MODELS` / `dialog._model_supports_effort`: effort 欄の表示制御パターン（D-15 では流用せず**対比対象**として参照）

### Established Patterns
- **`registry.py` の独立性制約（V180-D-01）**: 標準ライブラリのみ・内部モジュール非 import。`catalog.py` はこの制約を継承し、`catalog → registry` の一方向 import のみとする
- **`OCRDialog` と `BatchOCRDialog` のロジック独立**（`batch_ocr.py` 冒頭コメントで明示・v1.8.0 Phase 4 懸念 5）: コスト確認系メソッドは同一シグネチャの独立実装。**catalog で共有するのは「データ」だけ**であり、継承・メソッド import による DRY 化は明確なアンチパターン
- **`build_provider` の関数内 import**（循環 import 回避）: OpenAI 分岐でも `from pagefolio.ocr_providers import OpenAIProvider` を関数内で行う
- **API キーは引数注入のみ**（D-01/D-05・`build_provider(settings, api_key=...)`）: settings から読まず settings へ書かない
- **i18n は `lang.py` に ja/en ペアで追加**（未使用キー検出の回帰テストが常設・V171-D-11）
- **クラウド系の `model_list_timeout = 30`**（Claude/Gemini 同値）

### Integration Points
- `catalog.py` ↔ `registry.py`: 一方向 import（catalog → registry）。registry は catalog の存在を知らない
- `catalog.py` ↔ `sections.py` / `ocr_dialog.py` / `batch_ocr.py` / `ocr.py`: catalog は「import される専用」モジュール。settings.py からの循環 import を再発させない
- `ocr.py:build_provider` ↔ `ocr_providers/*`: ファクトリ。Phase 1 で `off` → `OCRDisabledError` の契約が確立済み
- `ocr_fallback.py` ↔ 送信先確認ダイアログ: フォールバック発動時の再提示（V190-OAI-07・V180-D-02）
- `dialogs/llm_config/{sections,dialog,model_fetch}.py` ↔ `_session_api_keys`: セッション API キーの入力・同期経路

</code_context>

<specifics>
## Specific Ideas

- 「**安全側デフォルトを構造に埋め込む**」という Phase 1 から続く判断基準が本フェーズでも一貫して選ばれた: D-10（常に新形式・非対応は省略）、D-08（フィルタ 0 件は静的リストへ合流）、D-04（未登録プロバイダでも isinstance で安全側に倒す）。いずれも「未知の入力が来たときに壊れない側」を選んでいる
- 「**判定経路は 1 本**」も継続（Phase 1 D-18 と同型）。D-13 で推論系判定を単一純関数へ集約し、temperature 省略と effort 有効化の両方を駆動する。2 つの判定が独立に存在すると必ずずれる、という認識が共有されている
- 一方で D-04 だけは意図的に**判定経路 2 本を許容**している。プラグインプロバイダに対する外部送信の明示同意（コスト確認・送信先確認）を落とさないことを、経路の単純さより優先した
- **変更面を広げない**判断も継続: D-02（価格表は catalog に入れない）、D-06（registry.py は触らない）、D-12（errors.py は原則未変更）、D-17（折りたたみ UI という新パターンを導入しない）。planner が親切心でスコープを広げないこと
- D-09（実キーでモデル一覧を確認してから既定値を確定）は**リサーチが Gap として明示的に残した宿題**であり、プランに実行タスクとして落ちていることが必要

</specifics>

<deferred>
## Deferred Ideas

- **`OCR_PRICE_TABLE` の一元化** — `ocr_dialog.py` と `batch_ocr.py` に同一の価格表が二重定義されている。モデル単位のデータであり catalog（プロバイダ単位）とは粒度が違うため今回は対象外（D-02）。将来「モデル単位メタデータ」の置き場を作るなら合わせて検討する
- **`dialogs/llm_config/dialog.py` のセッション API キー同期ループの完全動的化** — ウィジェット変数のカタログ駆動化。V190-F-03 として v2 に登録済み。今回は OpenAI 分の 1 行追記に留める
- **プラグインプロバイダが catalog へメタデータを登録できる API** — `register_ocr_provider` と対になる登録フック。プラグイン API の拡張は新しい能力の追加であり本フェーズのスコープ外。D-04 の isinstance フォールバックで当面をしのぐ
- **`ocr_dialog.py` の isinstance フォールバック判定の撤去** — catalog へのプラグイン登録 API（上記）が入れば判定経路を 1 本にできる。それまでは D-04 のまま維持

</deferred>

---

*Phase: 2-OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加*
*Context gathered: 2026-08-11*
