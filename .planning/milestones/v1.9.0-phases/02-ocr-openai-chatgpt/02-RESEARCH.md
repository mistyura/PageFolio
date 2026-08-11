# Phase 2: OCR プロバイダ基盤整理 + OpenAI(ChatGPT) プロバイダ追加 - Research

**Researched:** 2026-08-11
**Domain:** 既存 Python/Tkinter デスクトップアプリ（PageFolio）の OCR プロバイダ層リファクタ + 新規クラウドプロバイダ追加
**Confidence:** HIGH（設計判断は実コード読解に基づく。OpenAI API 仕様の一部＝MEDIUM）

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `pagefolio/ocr_providers/catalog.py` を新設し、**プロバイダ単位のメタデータをすべて集約**する。研究提案の `ProviderMeta`（frozen dataclass・`name` / `display_name_key` / `is_cloud` / `model_setting_key` / `default_model` / `host` / `fallback_eligible`）に加え、**API キー欠落エラーの LANG キー**（現状 `ocr_dialog.py` と `batch_ocr.py` に同一 dict が二重定義）も 1 フィールドとして持たせる。いずれも「プロバイダ 1 件につき 1 値」で粒度が揃うため。
- **D-02:** `OCR_PRICE_TABLE`（モデル名 → 入力/出力単価）は **catalog に入れない**。プロバイダ単位ではなくモデル単位のデータであり、粒度の異なるものを 1 モジュールへ混在させると catalog の「プロバイダ 1 件 = 1 エントリ」という単純さが崩れるため。`ocr_dialog.py` / `batch_ocr.py` の二重定義は現状維持（Deferred 参照）。
- **D-03:** 既存 6 参照面（`sections.py` の一覧リスト 2 箇所 / `ocr_dialog.py` の表示名・クラウド判定・host 分岐 / `batch_ocr.py` の同型分岐 / `ocr.py` の `_cloud_providers`）の catalog 移行を**本フェーズで完走**する。手順は「catalog.py 単体追加（既存コードから未参照・動作変化ゼロ）→ 1 ファイルずつ置換」の段階移行とし、**一括置換はしない**（表示順や既定値が 1 つズレたときの原因切り分けを可能にするため）。各ステップ完了時点で常に動作する状態を保つ。 — **Reversibility: costly** — 6 ファイルの参照経路を catalog 経由へ切り替えるため、戻すには全ファイルの再修正が必要。以降に追加されるプロバイダもこの契約の上に載る。
- **D-04:** catalog に登録のないプロバイダ（`PluginManager.register_ocr_provider` 経由のサードパーティ製）は `catalog.is_cloud_provider()` が **False（非クラウド）を返す**。あわせて `ocr_dialog.py` の **isinstance 判定（`ClaudeProvider` 等の継承チェック）をフォールバックとして維持**する。プラグインが既存クラウドプロバイダを継承している場合にコスト確認・送信先確認が消えると、外部送信の明示同意方針が弱まるため。判定経路が 2 本残ることは承知のうえで、安全側を優先する。
- **D-05:** `catalog.py` は **Provider クラス（`ocr_providers/claude.py` 等）を import しない**。`default_model` は catalog 側が自前の値として持ち、`catalog.default_model_for(name)` が対応 Provider の `RECOMMENDED_MODELS` に含まれることを**新設テストで機械保証**する。catalog は `registry.py` の隣に置く「軽量なデータモジュール」という性格を保ち、重い import 連鎖を背負わせない。
- **D-06:** `registry.py` は**一切変更しない**（OpenAI の環境変数追加を除く）。`catalog.py` → `registry.py` の一方向 import のみとし、逆方向は発生させない。環境変数名の解決は `registry.env_vars_for()` へ委譲し catalog では再定義しない（V180-D-01 の独立性制約を将来にわたり守るため、責務を 1 モジュールに混在させない）。
- **D-07:** `GET /v1/models` の応答は**モデル ID の命名規則によるヒューリスティックフィルタ**で絞る（チャット/vision 系のみを採用し、embedding・tts・whisper・dall-e・moderation 等を除外）。OpenAI の `/v1/models` には Anthropic のような vision 対応フラグが無く、Claude 方式の自動フィルタが再現できないため。**フィルタは Tk/ネットワーク非依存の純関数に切り出し**、除外パターンを単体テストで固定する。
- **D-08:** フィルタ結果が **0 件になった場合は静的フォールバック一覧（`RECOMMENDED_MODELS`）を返す**。取得失敗時（V190-OAI-03 の「取得に失敗した場合」）と同一経路に合流させ、失敗時パスを 1 本に集約する。将来 OpenAI の命名規則が変わってフィルタが陳腐化しても、ユーザーは常に何かを選べる。
- **D-09:** `RECOMMENDED_MODELS`（静的フォールバック）と `default_model` の**具体的なモデル名は、実装時に実 API キーで `GET /v1/models` を叩いて目視確認してから確定**する。プラン側にこの確認を明示タスクとして含めること。リサーチ時点の推定値をベタ書きすると、存在しないモデル名が既定値になり初回実行が失敗するリスクがある。実キーが用意できない場合は OpenAI 公式ドキュメントを二次ソースとする。
- **D-10:** モデル別パラメータ非互換は「**常に新形式を送り、非対応パラメータは省略する**」安全側方式を採る。`max_completion_tokens` を常用し、`max_tokens` は使わない。既存 `GeminiProvider._is_legacy_gemini`（新世代には省略＝省略は全世代で合法）と同型のパターンであり、**未知の新モデルが出ても 400 にならない**。モデル名の完全一致許可リスト（Claude の `EFFORT_MODELS` 方式）は、未知モデルが常に「非対応」判定になり集合の永続的な保守が発生するため不採用。400 応答を見て再送する適応方式も、失敗経路が増えて既存の 429/5xx リトライ基盤と相互作用が複雑になるため不採用。
- **D-11:** `temperature` は「**推論系モデルと判定できたものには送らない**」。判定はモデル ID の命名規則で行い、それ以外へは従来どおり `ocr_temperature` を送る。判定は D-13 と同じ純関数へ集約する。
- **D-12:** エラーマッピングは既存 `pagefolio/ocr_providers/errors.py` の `_raise_mapped_http_error` を**そのまま流用**し、errors.py は原則未変更とする（既に「OpenAI 互換: context_length_exceeded」マーカーを実装済み）。OpenAI 固有のエラー文字列で既存マッピングが不十分と実測で判明した場合のみ `_CONTEXT_ERROR_MARKERS` 等へマーカーを追記する。OpenAI 専用のエラー分岐経路は新設しない（共通基盤の外に 6 本目の分岐を作らない）。
- **D-13:** 「推論系モデルか否か」の判定は**単一の純関数に集約**し、`temperature` の省略（D-11）と reasoning effort 欄の有効化（D-15）の**両方をこの 1 つの判定で駆動**する（推論系 = temperature 省略 + effort 有効）。Phase 1 の D-18（判定経路を 1 本にする）と同じ方針であり、2 つの判定がずれる同型バグを構造的に防ぐ。
- **D-14:** `OpenAIProvider` の並列度は **`default_concurrency = 2` / `max_concurrency = 2`**（Claude 相当）とする。OpenAI のレート制限は tier 依存で、低 tier ユーザーでは 429 が頻発しかねないため保守的な既定にし、超過分は既存の指数バックオフ・`Retry-After` 尊重リトライ基盤に任せる。
- **D-15:** reasoning effort 相当パラメータは **OpenAI 専用のウィジェットと専用 settings キー**（例: `openai_reasoning_effort`）で実装する。Claude の `ocr_effort` / `effort_frame` は流用しない。OpenAI の `reasoning_effort` と Anthropic の `effort` は意味論が異なり取りうる値域も別であるため、共有すると一方の値域変更が他方を壊す。表示条件は D-13 の純関数で駆動する。
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

### Deferred Ideas (OUT OF SCOPE)

- **`OCR_PRICE_TABLE` の一元化** — `ocr_dialog.py` と `batch_ocr.py` に同一の価格表が二重定義されている。モデル単位のデータであり catalog（プロバイダ単位）とは粒度が違うため今回は対象外（D-02）。
- **`dialogs/llm_config/dialog.py` のセッション API キー同期ループの完全動的化** — ウィジェット変数のカタログ駆動化。V190-F-03 として v2 に登録済み。今回は OpenAI 分の 1 行追記に留める。
- **プラグインプロバイダが catalog へメタデータを登録できる API** — `register_ocr_provider` と対になる登録フック。プラグイン API の拡張は本フェーズのスコープ外。D-04 の isinstance フォールバックで当面をしのぐ。
- **`ocr_dialog.py` の isinstance フォールバック判定の撤去** — catalog へのプラグイン登録 API が入れば判定経路を 1 本にできる。それまでは D-04 のまま維持。
- OpenAI Responses API へのフル移行・公式 SDK 導入・organization 自動検出・`detail=high` 常時強制・`BatchOCRDialog`→`OCRDialog` のロジック共通化・OAuth 接続・OS キーストア連携（REQUIREMENTS.md Out of Scope 表を参照）。

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| V190-CAT-01 | プロバイダのキー・表示名・クラウド種別・環境変数・既定モデル・送信先ホスト・フォールバック可否が単一の情報源から解決される | §「重複マップ」で6箇所の重複実測を再確認済み。§「Architecture Patterns」に `catalog.py` 設計・7参照面の段階移行手順あり |
| V190-CAT-02 | 一元化後も `registry.py` の独立性制約が維持され循環 import が発生しない | `registry.py` 実物確認済み（標準ライブラリ `os` のみ import・D-06 で一方向 import を明記） |
| V190-OAI-01 | OCR プロバイダとして OpenAI(ChatGPT) を選択できる | `sections.py` の `_base_providers` リスト（catalog 移行対象）に追加するだけの構造を確認 |
| V190-OAI-02 | セッション限定 API キー入力・`_SENSITIVE_KEYS` ガード | `registry.py`/`settings.py` を実読し、`PROVIDER_ENV_KEYS` 1行追加で自動波及することを確認 |
| V190-OAI-03 | モデル一覧を API から取得・取得失敗時は静的フォールバック | `claude.py`/`gemini.py` の `list_models()` パターンを確認。OpenAI は vision フラグ欠如のためヒューリスティックフィルタが必要（D-07/D-08） |
| V190-OAI-04/05/06 | 送信先確認・コスト確認・バッチOCR組み込み | `ocr_dialog.py`/`batch_ocr.py` の `_confirm_cost`/`_is_cloud_provider` を実読し、追加パターンを確認 |
| V190-OAI-07 | フォールバック候補・再確認 | `ocr_fallback.py`/`ocr_dialog.py:_propose_fallback` を実読 |
| V190-OAI-08 | detail レベル選択・永続化 | STACK.md の画像入力形状調査 + D-16 |
| V190-OAI-09 | reasoning effort・対応モデルのみ有効化 | `claude.py:EFFORT_MODELS`/`dialog.py:_model_supports_effort` を対比対象として実読。D-13/D-15 |
| V190-OAI-10 | organization/project ID 任意入力・指定時のみヘッダ | `sections.py` の Claude セクション構成を雛形として実読（D-17） |
| V190-OAI-11 | `urllib.request` 直叩き・新規 pip 依存ゼロ | `lmstudio.py`/`claude.py`/`gemini.py` の実装を実読、全て urllib 直叩き確認済み |
| V190-OAI-12 | モデル別パラメータ非互換の分岐 | `gemini.py:_is_legacy_gemini`/`claude.py:_apply_gen_params` を実読しD-10/D-11の設計根拠を確認 |
| V190-OAI-13 | 429/5xx リトライ基盤の適用 | `errors.py:_raise_mapped_http_error`/`parse_retry_after` を実読、OpenAI 固有コード不要と確認 |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **リント必須**: 編集した `.py` ファイルは `ruff check . && ruff format .` が通ること（`pyproject.toml` の `[tool.ruff]` 設定を確認済み: `line-length=88`、`select=["E","F","W","I","S","B"]`、`tests/**` のみ `S101` 除外）
- **テスト必須**: コミット前に `pytest` を通す（`pyproject.toml` の `[tool.pytest.ini_options]`: `testpaths=["tests"]`）
- **禁止事項**: `pyproject.toml` の編集／裸の `except:`／`# type: ignore` の無断使用
- **`pagefolio/ocr_providers/registry.py` の独立性制約**: Python 標準ライブラリ（`os`）のみに依存し pagefolio 内部モジュールを import しない（`registry.py` 実物で確認済み・import 文は `import os` のみ）
- **API キーの扱い**: 設定ファイルに保存されず、環境変数またはセッションメモリ（`app._session_api_keys`）のみ
- **ボタンスタイル**: 通常操作→`"TButton"`、主要アクション→`"Accent.TButton"`、破壊的操作→`"Danger.TButton"`
- **フォントサイズ**: `self._font(delta)` ヘルパー使用（新規 OpenAI セクション UI でも踏襲）
- **i18n**: LANG 新規キーは ja/en 両方に同一キーで追加しキー数の左右一致を維持（既存の未使用キー検出回帰テストが常設）
- **1タスクずつ完了させてから次のタスクへ**
- **`開発履歴.md`/`APP_VERSION` 更新**: Phase 1 の先例（01-05/01-06/01-07 SUMMARY）に倣い、このマイルストーンでは Phase 3（リリースゲート）へ更新を委譲する運用が確立している。Phase 2 のプラン内では必須としない

## Summary

Phase 2 は「プロバイダメタデータの一元化（catalog.py 新設・V190-CAT-01/02）」と「OpenAI(ChatGPT) プロバイダのフル実装（V190-OAI-01〜13）」の2階建て構成である。本セッションでは `.planning/research/{ARCHITECTURE,SUMMARY,PITFALLS,STACK,FEATURES}.md`（2026-08-10 作成・discuss-phase の土台）を一次情報として継承しつつ、Phase 1 完了後の現行コード（`pagefolio/ocr_providers/*.py`・`pagefolio/ocr.py`・`pagefolio/ocr_dialog.py`・`pagefolio/dialogs/batch_ocr.py`・`pagefolio/dialogs/llm_config/*.py`）を今回のセッションで直接読解し、行番号・重複箇所を再検証した。

**catalog 一元化の核心**: `_is_cloud_provider` 相当の集合 `{"claude", "gemini", "runpod"}` は最低 4 箇所（`ocr.py:_start_ocr` 内・`ocr_dialog.py:_is_cloud_provider`・`batch_ocr.py:_is_cloud_provider`・`batch_ocr.py:_build_provider_once`）に手書きされている。表示名解決は `ocr_dialog.py` 内に 2 実装（`_provider_display_name` の if 連鎖と `_provider_key_to_display_name` の dict）が存在し、送信先ホスト分岐（`api.anthropic.com`/`generativelanguage.googleapis.com`）は `ocr_dialog.py` 内 3 箇所 + `batch_ocr.py` 内 2 箇所の計 5 箇所、API キー欠落エラーの LANG キーマップは `ocr_dialog.py`/`batch_ocr.py` に同一 dict が 2 回定義されている。この状態で OpenAI を追加すると、いずれかの分岐への追加漏れがほぼ確実に発生する。

**OpenAI プロバイダ実装の核心**: `pagefolio/ocr_providers/lmstudio.py` は既に「OpenAI 互換 Vision API」形状（`/v1/chat/completions`・`image_url` + base64 data URI・`choices[0].message.content`・`finish_reason=="length"`）で実装されており、OpenAI 本家の Chat Completions API と実質同一のリクエスト/レスポンス契約を持つ。`errors.py` は既に「OpenAI 互換: context_length_exceeded」マーカーを実装済みで、429/5xx の指数バックオフ・`Retry-After` 尊重リトライ基盤も無改修で流用できる。新規実装が必要なのは固定エンドポイント・`Authorization: Bearer` 認証・`max_completion_tokens`／推論系モデルの `temperature` 省略・`reasoning_effort`／画像 `detail`／org・project ヘッダの各分岐のみである。

Phase 1（`OCRDisabledError`・`build_provider` の `off` 拒否）は既に完了しており（`errors.py`/`ocr.py` で実装確認済み）、Phase 2 はこの安全網の上に載る。Phase 2 内の依存順序は「catalog.py 新設（動作変化ゼロ）→ 6参照面の段階移行 → OpenAI プロバイダ実装 → UI/バッチ/フォールバック統合」であり、catalog が OpenAI 追加の技術的前提（catalog 未完成のまま OpenAI を先に足すと、6 箇所の手書き分岐にさらに 1 プロバイダ分の追記が発生し二度手間になる）。

**Primary recommendation:** `catalog.py` を先に完成させ（D-03 の段階移行）、`OpenAIProvider` は `LMStudioProvider` を土台に固定エンドポイント・認証・パラメータ分岐を追加する形で実装する。UI 統合は `sections.py` の Claude セクション（411〜510行）をほぼそのまま複製し、モデル一覧取得は `model_fetch.py:_refresh_claude_models`（206〜243行）を同型で複製する。

## Architectural Responsibility Map

PageFolio は単一プロセスの Tkinter デスクトップアプリであり、Web の Browser/SSR/API/CDN/DB 階層は存在しない。代わりに「UI/ダイアログ層」「プロバイダ（ネットワーククライアント）層」「永続化層」「外部サービス」の4階層で捉える。

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| プロバイダメタデータ解決（表示名・クラウド判定・host・既定モデル） | `catalog.py`（新設・データ層） | — | プロバイダ 1 件 = 1 エントリの単純な参照テーブル。UI/バッチいずれからも同一データを引く単一情報源にする（V190-CAT-01） |
| 機密キー名解決（env var 名・sensitive keys 集合） | `registry.py`（既存・独立データ層） | `catalog.py`（host_for等は catalog 側で完結、機密解決は registry へ委譲） | V180-D-01 の独立性制約により機密解決の責務はこの1モジュールに固定 |
| OpenAI OCR/サマリ HTTP 呼び出し・レスポンスパース・パラメータ分岐 | `ocr_providers/openai_provider.py`（新設・プロバイダ層） | `ocr_providers/errors.py`（例外変換の共有） | 既存5プロバイダと同型のクラス単位カプセル化。Tk/UI 非依存 |
| OCR/バッチOCR実行時のクラウド判定・送信先確認・コスト確認 UI | `ocr_dialog.py` / `dialogs/batch_ocr.py`（UI/ダイアログ層） | `catalog.py`（判定に使うデータ源） | Tkinter ウィジェット依存のロジックは独立実装のまま（意図的な非共有・1.7節参照）。データのみ catalog 経由に統一 |
| LLM 設定 UI（プロバイダ選択・OpenAI 固有欄・APIキー入力・モデル取得） | `dialogs/llm_config/{sections,dialog,model_fetch}.py`（UI/ダイアログ層） | `catalog.py`（プロバイダ一覧・フォールバック候補一覧） | 既存 Claude/Gemini セクションと同型の Mixin 構成に OpenAI セクションを追加 |
| セッション API キー保持・非永続化ガード | `app._session_api_keys`（アプリ層メモリ） + `settings.py:_SENSITIVE_KEYS`（永続化層ガード） | `registry.py:sensitive_keys()` | `registry.PROVIDER_ENV_KEYS` に1行追加するだけで自動導出（V190-OAI-02） |
| フォールバック候補選択（次候補決定） | `ocr_fallback.py`（純ロジック層・Tk/fitz非依存） | `ocr_dialog.py:_propose_fallback`（UI再確認オーケストレーション） | 既存の純関数 `next_fallback_candidate`/`next_summary_candidate` に「openai」を候補として加えるだけで対応可能（ロジック変更不要） |
| 429/5xx リトライ・バックオフ | `ocr_providers/errors.py`（共有）+ `ocr.py:run_parallel`（並列実行制御） | — | OpenAI 固有コード不要。`_raise_mapped_http_error`/`clamp_retry_after`/`interruptible_sleep` をそのまま適用 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `urllib.request`（標準ライブラリ） | Python 3.14.6 同梱 | OpenAI Chat Completions / `/v1/models` への HTTP 呼び出し | 既存5プロバイダ（Claude/Gemini/LMStudio/Ollama/RunPod）が全て urllib 直叩きで実装済み（本セッションで `claude.py`/`gemini.py`/`lmstudio.py` を実読し確認）。V14-D-01（新規 pip 依存ゼロ）を継続 [VERIFIED: pagefolio/ocr_providers/claude.py, gemini.py, lmstudio.py — 全て `import urllib.request` のみでHTTP実装] |

**このフェーズで新規 pip 依存は一切追加しない**（V190-OAI-11）。`pip install` を伴うタスクは発生しない。

### Supporting

該当なし（標準ライブラリのみで完結）。

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Chat Completions API | Responses API | OpenAI 公式は新規プロジェクトに Responses API を推奨するが、既存 `RunPodProvider`/`LMStudioProvider` が既に Chat Completions 互換形状で実装済みのため統合コストが最小。Responses API は agentic/ステートフル機能が主眼で PageFolio のステートレス単発呼び出しには不要（REQUIREMENTS.md Out of Scope で明示除外） |
| 名前ベース除外フィルタ（`list_models`） | 静的 `RECOMMENDED_MODELS` のみ返す | 実装コストは下がるが、新モデル追加時の追従性が失われる。D-07 で名前ベースフィルタを採用 |

**Installation:** 不要（新規パッケージなし）。

**Version verification:** 該当なし（新規パッケージインストールなし）。既存 `requirements.txt` の固定バージョン（`PyMuPDF==1.28.0` / `Pillow==12.3.0` / `tkinterdnd2==0.6.2` / `pytest==9.1.1` / `ruff==0.15.20`）は変更不要。

## Package Legitimacy Audit

**該当なし。本フェーズは新規外部パッケージを一切インストールしない**（V190-OAI-11・`urllib.request` 標準ライブラリのみで実装）。Package Legitimacy Gate はスキップする。

## Architecture Patterns

### System Architecture Diagram

```
[ユーザー操作]
   │
   ├─▶ LLMConfigDialog（sections.py/dialog.py/model_fetch.py）
   │      │  プロバイダ選択 "openai" ─▶ catalog.provider_names() から一覧取得
   │      │  OpenAI固有欄表示（APIキー・モデル・org/project・detail・effort）
   │      │  モデル一覧更新ボタン ─▶ _refresh_openai_models()
   │      │        └─▶ OpenAIProvider(api_key, model="").list_models()
   │      │               └─▶ GET https://api.openai.com/v1/models
   │      │                      ├─ 成功 ─▶ ヒューリスティックフィルタ(D-07)
   │      │                      │            ├─ 0件以上 ─▶ フィルタ結果を返す
   │      │                      │            └─ 0件 ─▶ RECOMMENDED_MODELS(D-08)
   │      │                      └─ 失敗/キー未設定 ─▶ RECOMMENDED_MODELS(D-08)
   │      └─▶ Apply ─▶ settings["ocr_provider"]="openai" 等を永続化
   │             （API キーは _session_api_keys のみ・settings.json 非永続）
   │
   ├─▶ 通常OCR実行（ocr.py:_start_ocr → OCRDialog）
   │      │  catalog.is_cloud_provider("openai") == True
   │      │  ─▶ APIキー事前解決（_resolve_api_key）
   │      │  ─▶ build_provider(settings, api_key) ─▶ elif name=="openai": OpenAIProvider(...)
   │      │  OCRDialog._on_run
   │      │    ─▶ _is_cloud_provider() True ─▶ _check_cloud_api_key()
   │      │    ─▶ _confirm_cost()（catalog.host_for("openai")="api.openai.com" を表示）
   │      │    ─▶ run_parallel(provider, images, ...) ── 並列度 2（D-14）
   │      │           └─▶ provider.ocr_image(b64, prompt)
   │      │                  └─▶ POST /v1/chat/completions
   │      │                         ├─ 成功 ─▶ choices[0].message.content
   │      │                         ├─ 429/5xx ─▶ OCRRetryableError
   │      │                         │      └─▶ run_parallel の指数バックオフ・Retry-After待機
   │      │                         └─ 4xx ─▶ RuntimeError / OCRContextLengthError
   │      └─▶ フォールバック発動時 ─▶ _propose_fallback ─▶ next_fallback_candidate
   │             （openai がチェーンに含まれれば候補に上がる。送信先確認を再提示）
   │
   └─▶ バッチOCR実行（dialogs/batch_ocr.py:BatchOCRDialog）
          │  独立実装（OCRDialogを継承しない・1.7節）
          │  _is_cloud_provider / _confirm_cost / _check_cloud_api_key の同型独立コピー
          └─▶ _build_provider_once() ─▶ build_provider(...) ─▶ 同一 OpenAIProvider 経路
```

### Recommended Project Structure

```
pagefolio/
├── ocr_providers/
│   ├── catalog.py              # 新設: ProviderMeta + PROVIDERS dict（V190-CAT-01/02）
│   ├── openai_provider.py      # 新設: OpenAIProvider（V190-OAI-01〜13）
│   ├── registry.py             # 既存・変更は PROVIDER_ENV_KEYS への1行追加のみ
│   ├── errors.py               # 既存・原則未変更（D-12）
│   ├── lmstudio.py             # 既存・OpenAIProvider実装の土台として参照
│   ├── claude.py                # 既存・EFFORT_MODELS/list_models パターンの対比対象
│   ├── gemini.py               # 既存・_is_legacy_gemini パターンの参照元（D-10/D-11）
│   └── __init__.py             # 既存・OpenAIProvider の re-export を追加
├── ocr.py                       # build_provider に openai 分岐追加・_cloud_providers を catalog 経由へ
├── ocr_dialog.py                # 表示名/クラウド判定/host分岐/APIキー欠落マップを catalog 経由へ
├── ocr_fallback.py              # 変更不要（純関数はプロバイダ名非依存）
└── dialogs/
    ├── batch_ocr.py             # 同型の catalog 移行 + openai 分岐（ロジックは独立のまま）
    └── llm_config/
        ├── sections.py          # _base_providers/_base_fallback_providers を catalog 経由へ + OpenAIセクションUI新設
        ├── dialog.py            # _on_provider_change に openai 分岐 + APIキー同期ループへ追加
        └── model_fetch.py       # _refresh_openai_models 新設（_refresh_claude_models と同型）

tests/
├── test_ocr_provider_catalog.py # 新規（Claude's Discretion: 新規ファイル案）
└── test_ocr_providers.py        # OpenAIProvider の単体テストを既存パターンで追加
```

### Pattern 1: `catalog.py` によるプロバイダメタデータ一元化

**What:** `ProviderMeta`（frozen dataclass）を要素とする `PROVIDERS: dict[str, ProviderMeta]` を新設し、表示名・クラウド判定・既定モデル・host・フォールバック可否・APIキー欠落 LANG キーを1箇所で解決する。

**When to use:** 新規プロバイダ追加時、または既存プロバイダのメタデータを参照する全箇所（`sections.py`/`ocr_dialog.py`/`batch_ocr.py`/`ocr.py`）。

**Example（設計イメージ・CONTEXT.md D-01の叩き台を踏襲）:**
```python
# pagefolio/ocr_providers/catalog.py（新設）
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderMeta:
    name: str                     # settings["ocr_provider"] の値と一致
    display_name_key: str         # LANG のキー名
    is_cloud: bool                # 外部送信あり = コスト確認/送信先確認/APIキー欄が必要
    model_setting_key: str | None # settings 内のモデルキー
    default_model: str | None     # モデル未設定時の既定値
    host: str | None              # 固定送信先ホスト。ユーザー設定URL依存なら None
    fallback_eligible: bool       # フォールバック候補一覧に出すか
    api_key_missing_lang_key: str | None  # D-01: APIキー欠落エラーの LANG キー


PROVIDERS: "dict[str, ProviderMeta]" = {
    "off": ProviderMeta("off", "ocr_provider_name_off", False, None, None, None, False, None),
    "lmstudio": ProviderMeta("lmstudio", "ocr_provider_name_lmstudio", False, "lm_studio_model", "", None, True, None),
    "ollama": ProviderMeta("ollama", "ocr_provider_name_ollama", False, "ollama_model", "", None, True, None),
    "runpod": ProviderMeta("runpod", "ocr_provider_name_runpod", True, "runpod_model", "", None, True, "ocr_api_key_missing_runpod"),
    "claude": ProviderMeta("claude", "ocr_provider_name_claude", True, "claude_model", "claude-sonnet-4-6", "api.anthropic.com", True, "ocr_api_key_missing"),
    "gemini": ProviderMeta("gemini", "ocr_provider_name_gemini", True, "gemini_model", "gemini-2.5-flash", "generativelanguage.googleapis.com", True, "ocr_api_key_missing_gemini"),
    "tesseract": ProviderMeta("tesseract", "ocr_provider_name_tesseract", False, None, None, None, True, None),
    "openai": ProviderMeta("openai", "ocr_provider_name_openai", True, "openai_model", "<D-09で実キー確認後に確定>", "api.openai.com", True, "ocr_api_key_missing_openai"),
}


def provider_names(include_off: bool = True) -> list:
    return [n for n in PROVIDERS if include_off or n != "off"]


def fallback_candidate_names() -> list:
    return [n for n, m in PROVIDERS.items() if m.fallback_eligible]


def is_cloud_provider(name: str) -> bool:
    m = PROVIDERS.get(name)
    return bool(m and m.is_cloud)


def host_for(name: str, settings: dict) -> str:
    m = PROVIDERS.get(name)
    if m is None:
        return ""
    if m.host:
        return m.host
    if name == "runpod":
        return settings.get("runpod_url", "")
    return ""


def default_model_for(name: str) -> str:
    m = PROVIDERS.get(name)
    return (m.default_model or "") if m else ""
```
`env_vars_for`/`sensitive_keys` は re-export せず、呼び出し側が `from pagefolio.ocr_providers.registry import env_vars_for` を直接使う（既存 `sections.py`/`model_fetch.py` の慣習を踏襲）。

**独立性制約の検証**: `catalog.py` は `registry.py` のみを import し、`registry.py` は `catalog.py` を import しない（一方向）。`registry.py` 自体は `PROVIDER_ENV_KEYS` への1行追加以外変更しない（D-06）。[VERIFIED: pagefolio/ocr_providers/registry.py:1-73 — `import os` のみで他モジュール非依存を確認]

### Pattern 2: OpenAI プロバイダ実装（`LMStudioProvider` を土台にした差分実装）

**What:** `LMStudioProvider` の `_build_payload`/`_post_chat`/`ocr_image`/`complete_text_ex`/`list_models` の構造をほぼそのまま流用し、固定エンドポイント・`Authorization: Bearer` 認証・`max_completion_tokens`・推論系モデル判定によるパラメータ省略・org/project ヘッダを追加する。

**When to use:** `pagefolio/ocr_providers/openai_provider.py` 新設時。

**Example（`lmstudio.py`/`claude.py`/`gemini.py` の実装パターンを合成した設計イメージ）:**
```python
# pagefolio/ocr_providers/openai_provider.py（新設イメージ）
import json
import re
import socket
import urllib.error
import urllib.request

from pagefolio.ocr_providers.base import OCRProvider
from pagefolio.ocr_providers.errors import _raise_mapped_http_error


class OpenAIProvider(OCRProvider):
    """OpenAI Chat Completions API プロバイダ（urllib 直叩き）。"""

    default_concurrency = 2   # D-14: Claude 相当
    max_concurrency = 2       # D-14
    supports_text_prompt = True
    model_list_timeout = 30   # クラウド系共通（Claude/Gemini と同値）

    CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    MODELS_ENDPOINT = "https://api.openai.com/v1/models"
    # D-09: 実キーで /v1/models を確認後に確定させること（プレースホルダ）
    RECOMMENDED_MODELS = ["<実装時に実キーで確認>"]

    # D-13: 推論系モデル判定の単一純関数（temperature省略 + effort有効化を駆動）
    _REASONING_MODEL_RE = re.compile(r"^o\d")  # o1/o3/o4-mini 等のプレフィックス例

    def _is_reasoning_model(self) -> bool:
        """モデルIDが推論系（o-series等）か判定する（D-13・単一判定源）。"""
        return bool(self._REASONING_MODEL_RE.match(self.model or ""))

    def __init__(
        self, api_key, model, timeout=120, max_tokens=4096,
        temperature=0.1, detail="high", reasoning_effort=None,
        organization="", project="",
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.detail = detail
        self.reasoning_effort = reasoning_effort
        self.organization = organization
        self.project = project

    def _headers(self):
        # D-17: org/project は空なら一切ヘッダを付与しない
        h = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        if self.organization:
            h["OpenAI-Organization"] = self.organization
        if self.project:
            h["OpenAI-Project"] = self.project
        return h

    def _apply_gen_params(self, payload):
        # D-10: 常に max_completion_tokens（max_tokens は使わない）
        payload["max_completion_tokens"] = self.max_tokens
        # D-11/D-13: 推論系モデルには temperature を送らない
        if not self._is_reasoning_model():
            payload["temperature"] = self.temperature
        elif self.reasoning_effort:
            # D-15: reasoning_effort は対応モデル判定時のみ付与
            payload["reasoning_effort"] = self.reasoning_effort
        return payload

    def _build_payload(self, b64_png, prompt):
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64_png}",
                        "detail": self.detail,  # D-16: 既定 high
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
        }
        return self._apply_gen_params(payload)

    def _post_chat(self, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            self.CHAT_ENDPOINT, data=data, headers=self._headers(), method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            _raise_mapped_http_error(e)   # D-12: 既存共通変換をそのまま流用
        except socket.timeout as e:
            raise TimeoutError(f"timed out after {self.timeout}s") from e
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if isinstance(reason, socket.timeout):
                raise TimeoutError(f"timed out after {self.timeout}s") from e
            raise ConnectionError(str(reason)) from e

    def ocr_image(self, b64_png, prompt, **kwargs):
        body = self._post_chat(self._build_payload(b64_png, prompt))
        try:
            result = json.loads(body)
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(f"Unexpected response format: {body[:500]}") from e

    def list_models(self):
        if not self.api_key:
            return list(self.RECOMMENDED_MODELS)   # D-08: キー未設定は静的リスト
        # ... GET /v1/models 呼び出し（claude.py の list_models と同型のHTTP処理）...
        # D-07: ヒューリスティックフィルタを適用し、0件なら RECOMMENDED_MODELS へ合流（D-08）
```

**根拠となる既存実装**: `LMStudioProvider._build_payload`（`pagefolio/ocr_providers/lmstudio.py:42-63`）が `image_url`+base64 data URI 構造の一次実装。`ClaudeProvider._apply_gen_params`（`pagefolio/ocr_providers/claude.py:114-130`）が「モデル種別に応じてパラメータを出し分ける」設計の直接の前例。`GeminiProvider._is_legacy_gemini`/`_model_generation`（`pagefolio/ocr_providers/gemini.py:107-126`）が「世代判定→パラメータ省略」の安全側パターンの前例（D-10/D-11 の設計根拠）。[VERIFIED: 上記3ファイルを本セッションで実読]

### Pattern 3: LLM設定UIへのOpenAIセクション追加（Claudeセクションの複製）

**What:** `sections.py` の Claude セクション（`self.claude_section_frame` 構築ブロック）をほぼそのまま複製し、OpenAI 固有欄（APIキー・モデル・org/project・detail・reasoning_effort）を追加する。

**When to use:** `pagefolio/dialogs/llm_config/sections.py` に `openai_section_frame` を新設する際。

**Example（実物からの抜粋・雛形として利用）:**
```python
# pagefolio/dialogs/llm_config/sections.py:411-510（Claude セクション実物）を雛形にする
self.claude_section_frame = tk.Frame(body, bg=C["BG_DARK"])
# ... モデル combobox（RECOMMENDED_MODELS を values に）...
self.claude_model_var = tk.StringVar(
    value=self.current_settings.get("claude_model", "claude-sonnet-4-6"),
)
self.claude_model_combo = ttk.Combobox(
    claude_model_row, textvariable=self.claude_model_var,
    font=self._font(-1), values=ClaudeProvider.RECOMMENDED_MODELS,
)
self.claude_model_combo.bind("<<ComboboxSelected>>", self._on_model_change)

# APIキー欄（セッション限定・マスク表示切替あり）
self.claude_api_key_var = tk.StringVar(
    value=self._session_api_keys.get("claude", ""),
)
self.claude_api_key_entry = tk.Entry(
    claude_key_row, show="*", textvariable=self.claude_api_key_var, ...
)
# トグルボタン（表示/非表示切替）・env設定時の注記ラベル・モデル更新ボタン
```
OpenAI セクションはこの構造を複製し、加えて org/project 2欄（D-17・空可）・detail レベル combobox（D-16・既定`high`）・reasoning_effort 欄（D-15・専用 settings キー・D-13 判定関数で表示切替）を追加する。[VERIFIED: pagefolio/dialogs/llm_config/sections.py:411-510 実読]

`_on_provider_change`（`dialog.py:175-271`）に `elif provider == "openai":` 分岐を追加し、`claude_section_frame`/`gemini_section_frame` と同様に `openai_section_frame.pack(...)` / `pack_forget()` を切り替える。effort 欄の表示切替は `_on_model_change`（`dialog.py:274-291`）と同型の `_on_openai_model_change` を新設し、D-13 の推論系判定関数を呼ぶ。[VERIFIED: pagefolio/dialogs/llm_config/dialog.py:175-291 実読]

### Pattern 4: モデル一覧取得（`_refresh_claude_models` の複製）

**What:** `model_fetch.py:_refresh_claude_models`（206-243行）を同型でコピーし `_refresh_openai_models` を新設する。

**Example（実物）:**
```python
# pagefolio/dialogs/llm_config/model_fetch.py:206-243（実物・雛形として利用）
def _refresh_claude_models(self):
    self._set_lm_status(self._L["llm_fetching_claude_models"], kind="info")
    api_key = self.claude_api_key_var.get().strip() or _env_fallback("claude")
    provider = ClaudeProvider(api_key=api_key, model="")

    def _on_success(models):
        self.claude_model_combo["values"] = models
        ...
    def _on_error(e):
        self.claude_model_combo["values"] = ClaudeProvider.RECOMMENDED_MODELS
        ...
    self._fetch_models_async(provider.list_models, _on_success, _on_error)
```
`_env_fallback("openai")` は `registry.env_vars_for("openai")` が `("OPENAI_API_KEY",)` を返すことで自動対応する（D-06/D-18 で `registry.py` へ1行追加するだけで完結）。[VERIFIED: pagefolio/dialogs/llm_config/model_fetch.py:17-32, 206-243 実読]

### Anti-Patterns to Avoid

- **`BatchOCRDialog` から `OCRDialog` のメソッドを継承/import して DRY 化しようとする:** `pagefolio/dialogs/batch_ocr.py` の冒頭コメント（4-16行目）が明示的にこれを否定している（04-02-PLAN.md Review Incorporation 懸念5）。OpenAI 追加時も `_is_cloud_provider`/`_confirm_cost`/`_check_cloud_api_key` は独立実装のまま維持し、**catalog 経由で共有するのはデータのみ**とする。[VERIFIED: pagefolio/dialogs/batch_ocr.py:1-16 実読]
- **`registry.py` へ非機密メタデータ（表示名・RECOMMENDED_MODELS等）を混在させる:** V180-D-01 の独立性制約を破壊する。`catalog.py` を新設して分離すること。
- **`OCR_PRICE_TABLE` を catalog.py に混在させる:** モデル単位データとプロバイダ単位データの粒度が異なる（D-02）。
- **カタログ移行を一括置換する:** 表示順や既定値のズレが起きたときの原因切り分けが困難になる。段階移行（D-03）を厳守する。
- **`max_tokens` を送信する:** OpenAI は非推奨化しており o-series では 400 エラーになる。常に `max_completion_tokens` を使う（D-10）。
- **未知モデルへ `temperature`/`reasoning_effort` を機械的に両方送る:** D-13 の単一判定関数で「推論系＝temperature省略+effort有効」「非推論系＝temperature送信+effort省略」の二値分岐を徹底する。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| 429/5xx リトライ・指数バックオフ | OpenAI 専用のリトライループ | `pagefolio/ocr_providers/errors.py:_raise_mapped_http_error` + `ocr.py:run_parallel` の既存バックオフ | 既に `Retry-After` 汎用パース・60秒上限クランプ・キャンセル確認付き待機まで実装済み。OpenAI 固有コード不要（V190-OAI-13） |
| コンテキスト長超過検出 | OpenAI 専用の 400 body 判定 | `errors.py:_CONTEXT_ERROR_MARKERS`（既に "context_length_exceeded" マーカー実装済み） | 既存の汎用マーカー判定に既に OpenAI 形式が含まれている |
| APIキーの機密判定・env var 解決 | OpenAI 専用の env var 参照コード | `registry.py:env_vars_for`/`primary_env_var`/`sensitive_keys` へ1行追加 | 1エントリ追加で `_resolve_api_key`（ocr.py）・`_check_cloud_api_key`（ocr_dialog.py/batch_ocr.py）・`_SENSITIVE_KEYS`（settings.py）すべてに自動波及する |
| モデル一覧のバックグラウンド非同期取得 | OpenAI 専用のスレッド管理 | `model_fetch.py:_fetch_models_async`（既存共有インフラ） | Claude/Gemini/RunPod と同型で使い回せる |
| Vision画像のbase64 data URI組み立て | OpenAI 専用の画像エンコード | `ocr.py:page_to_png_b64`（プロバイダ非依存の共通ユーティリティ） | 既存の全プロバイダが共有 |

**Key insight:** OpenAI は「OpenAI互換 Vision API」を既に実装している `LMStudioProvider`/`RunPodProvider` の形状にほぼ収まるため、新規実装が必要なのは「固定エンドポイント・認証・パラメータ名の差分」のみである。既存の共有インフラ（リトライ・エラーマッピング・非同期モデル取得・機密キー管理）を作り直す必要は一切ない。

## Common Pitfalls

### Pitfall 1: カタログ移行時に monkeypatch 対象の名前空間が断絶する（v1.8.0 で実際に発生済み）

**What goes wrong:** `dialog.py`/`sections.py`/`ocr_dialog.py`/`batch_ocr.py` の各所が catalog 経由の呼び出しに変わると、テストの `monkeypatch.setattr("旧モジュールパス", fake)` が実体の無い箇所をパッチすることになり、パッチが静かに効かなくなる（テストは green のまま、本番バグを検知できなくなる最悪パターン）。

**Why it happens:** v1.8.0 Phase 1 の `llm_config.py` → `llm_config/` サブパッケージ分割時に実際に発生した既知パターン。`dialog.py:_apply()` に残る「分割前は同一モジュール内の名前空間で monkeypatch が効いていたため、分割後も遅延 import 経由で同じ差し替え可能性を保つ」というコメント（本セッションで実物確認済み・`dialog.py:454-458`相当の記述箇所は今回は import 部の設計として反映）が対策の記録。

**How to avoid:** catalog 移行後、既存の全テストを実行するだけでなく、**意図的に本番コードへバグを1つ注入してテストが落ちることを確認する**（ミューテーションテスト的検証）。特に APIキー未設定時のエラーメッセージ・送信先確認ダイアログの表示内容など monkeypatch 依存のテストを重点確認する。

**Warning signs:** `pytest -q` は全件パスするが、本番コードを一時的に壊してもテストが依然パスする。

**Phase to address:** catalog 移行の各段階（D-03の6ステップ）完了時に都度確認する。

### Pitfall 2: OpenAI `/v1/models` に vision 対応フラグが無い（Claude/Geminiとの非対称性）

**What goes wrong:** `ClaudeProvider.list_models()`（`claude.py:304-341`）は `capabilities.image_input.supported` で vision対応モデルのみへ絞り込む。`GeminiProvider.list_models()`（`gemini.py:275-323`）は `supportedGenerationMethods` に `"generateContent"` を含むかで絞り込む。**OpenAI の `/v1/models` にはこれに相当するフィールドが無い**ため、同じ実装方式が再現できない。

**Why it happens:** OpenAI API の設計上の制約であり、コード側の見落としではない。

**How to avoid:** D-07 のとおり、モデル ID の命名規則によるヒューリスティックフィルタ（embedding/tts/whisper/dall-e/moderation 等の除外パターン）を採用し、**Tk/ネットワーク非依存の純関数**に切り出してテストで固定する。フィルタ結果が0件なら D-08 のとおり `RECOMMENDED_MODELS` へ合流させる。

**Warning signs:** フィルタを実装せず生の一覧をそのまま Combobox に出すと、embedding/tts系モデルがOCR用途のモデル選択肢に混入する。

**Phase to address:** V190-OAI-03（本フェーズ）。実装時に D-09 のとおり実キーで `GET /v1/models` を1回叩き、実在するモデル名の命名パターンを確認してからフィルタの正規表現を確定する。

### Pitfall 3: 推論系モデル判定がずれると `temperature` 送信と `reasoning_effort` 表示が食い違う

**What goes wrong:** 「`temperature` を省略する判定」と「`reasoning_effort` 欄を表示する判定」を別々のロジックで実装すると、モデル名の判定基準がわずかにずれたときに「temperature は省略されたのに effort 欄は非表示（何も送られない）」「temperature は送られているのに effort 欄が表示される（400になる）」という不整合が起こり得る。

**Why it happens:** UI側（`dialog.py`）とプロバイダ側（`openai_provider.py`）で判定ロジックを別々に書いてしまうと発生する典型的な「判定経路が2本になる」バグ。

**How to avoid:** D-13 のとおり単一の純関数（例: `_is_reasoning_model(model)`）に集約し、UI側とプロバイダ側の両方がこの同じ関数を参照する（Claude の `EFFORT_MODELS`+`_supports_effort()` と `dialog.py:_model_supports_effort()` が二重実装になっている現状パターンを反面教師にする — `claude.py:69-75`と`dialog.py:294-`が同じロジックを2箇所に持つ既存の技術的負債を、OpenAIでは繰り返さない）。

**Warning signs:** UI で effort 欄が表示されているのに実際のリクエストには反映されない、またはその逆。

**Phase to address:** V190-OAI-09/11/12（本フェーズ）。

### Pitfall 4: org/project ヘッダーを常に付与してしまう

**What goes wrong:** 単一組織・個人利用のユーザーには `OpenAI-Organization`/`OpenAI-Project` ヘッダーは不要であり、空文字を誤って送信すると API 側で無効な値としてエラーになる可能性がある。

**Why it happens:** Claude の `x-api-key` ヘッダーのように「常に付与する」設計を機械的に踏襲すると発生しやすい。

**How to avoid:** D-17 のとおり「空のときはリクエストヘッダを一切付与しない」を徹底する（`if self.organization: headers["OpenAI-Organization"] = ...` のガード）。

**Phase to address:** V190-OAI-10（本フェーズ）。

### Pitfall 5: OpenAI モデルのラインナップは変動が速い（本セッションのWebSearchでも再確認）

**What goes wrong:** リサーチ時点（2026-08-10 の STACK.md）で言及された `gpt-4o`/`gpt-4.1` 系は、本セッション（2026-08-11）の WebSearch では既に `gpt-5.x` 系が「ChatGPT の既定」として言及されており、わずか1日でも情報が古くなっている可能性がある。

**Why it happens:** OpenAI のモデルリリースサイクルは他プロバイダより速い。

**How to avoid:** D-09 のとおり、`RECOMMENDED_MODELS`・`default_model` の確定は**必ず実装時に実 API キーで `GET /v1/models` を叩いて目視確認**する。本 RESEARCH.md ではモデル名を確定値として記載しない（プレースホルダのまま）。

**Warning signs:** 存在しないモデル名を既定値にすると初回 OCR 実行が 400/404 で必ず失敗する。

**Phase to address:** V190-OAI-03（本フェーズ・実装時タスクとして明示的に含めること）。

## Code Examples

### 既存 `build_provider` の分岐パターン（OpenAI分岐の追加箇所・実物）

```python
# pagefolio/ocr.py:468-499（実物・claudeとgemini分岐）
elif name == "claude":
    from pagefolio.ocr_providers import ClaudeProvider

    mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
    mt = 4096 if mt <= 0 else mt  # H-1: -1はLM Studio専用の委譲値
    return ClaudeProvider(
        api_key=api_key or "",
        model=settings.get("claude_model", "claude-sonnet-4-6"),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
        max_tokens=mt,
        temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
        effort=settings.get("ocr_effort", "low"),
    )
elif name == "gemini":
    from pagefolio.ocr_providers import GeminiProvider
    mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
    mt = 4096 if mt <= 0 else mt
    return GeminiProvider(
        api_key=api_key or "",
        model=settings.get("gemini_model", "gemini-2.5-flash"),
        timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
        max_tokens=mt,
        temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
    )
# 追加イメージ:
# elif name == "openai":
#     from pagefolio.ocr_providers import OpenAIProvider
#     mt = int(settings.get("ocr_max_tokens", DEFAULT_OCR_MAX_TOKENS))
#     mt = 4096 if mt <= 0 else mt  # Claude's Discretion: クランプ値
#     return OpenAIProvider(
#         api_key=api_key or "",
#         model=settings.get("openai_model", catalog.default_model_for("openai")),
#         timeout=int(settings.get("ocr_timeout", DEFAULT_OCR_TIMEOUT)),
#         max_tokens=mt,
#         temperature=float(settings.get("ocr_temperature", DEFAULT_OCR_TEMPERATURE)),
#         detail=settings.get("openai_detail", "high"),
#         reasoning_effort=settings.get("openai_reasoning_effort") or None,
#         organization=settings.get("openai_organization", ""),
#         project=settings.get("openai_project", ""),
#     )
```
`OCRDisabledError` の "off" 分岐（`ocr.py:454-458`）は既に Phase 1 で完成済みであり、OpenAI 分岐追加時も改修不要。[VERIFIED: pagefolio/ocr.py:429-546 全文実読]

### `registry.py` への1行追加（実物の該当箇所）

```python
# pagefolio/ocr_providers/registry.py:19-23（実物）
PROVIDER_ENV_KEYS = {
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "runpod": ("RUNPOD_API_KEY",),
    # 追加: "openai": ("OPENAI_API_KEY",),
}
```
この1行追加のみで `env_vars_for`/`primary_env_var`/`resolve_env_key`/`sensitive_keys` の4関数すべてが OpenAI に自動対応する。[VERIFIED: pagefolio/ocr_providers/registry.py:19-73 全文実読]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `max_tokens`（Chat Completions） | `max_completion_tokens` | OpenAI が非推奨化（時期不明・複数情報源で確認） | o-series 推論モデルでは `max_tokens` は使用不可。全モデルで `max_completion_tokens` に統一することが安全 |
| gpt-4o/gpt-4.1 系がOpenAIの主力（STACK.md記載時点=2026-08-10） | gpt-5.x 系が ChatGPT の既定（本セッション WebSearch=2026-08-11） | 数週間〜数ヶ月単位で高速に変化 | RECOMMENDED_MODELS/default_model はコード内に確定値をベタ書きせず、D-09 のとおり実装時の実キー確認に委ねる |
| Responses API が新規プロジェクト向けにOpenAI公式推奨 | 本プロジェクトは意図的に Chat Completions を選択 | — | PageFolio の OCR/サマリはステートレス単発呼び出しでありResponses APIのagentic機能は不要（REQUIREMENTS.md Out of Scope） |

**Deprecated/outdated:**
- `max_tokens`（Chat Completions API）: `max_completion_tokens` に置き換え済み。特に o-series 推論モデルでは必須。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OpenAI の推論系モデル（o-series）は正規表現 `^o\d` のようなプレフィックスパターンで判定できる | Pattern 2（Code Example） | モデル命名規則が変わると誤判定し、temperature/reasoning_effortの送信が誤る。D-10のとおり「新形式を常に送り非対応は省略」の安全側設計のため、誤判定してもHTTP 400にはなりにくいが、reasoning_effort欄の表示/非表示は誤り得る。実装時に実際のモデルID一覧（D-09で取得）を見て正規表現を再確定すること |
| A2 | RECOMMENDED_MODELS/default_modelの具体的なモデル名（プレースホルダ扱い） | Pattern 1（catalog.py）・Pattern 2（openai_provider.py） | D-09で意図的に未確定。実装時に実キーで`GET /v1/models`を確認しないと、存在しないモデル名が既定値になり初回実行が失敗する |
| A3 | `Authorization: Bearer`ヘッダーのみで認証が完結し、追加のクエリパラメータや別ヘッダーは不要 | Pattern 2 | STACK.md（2026-08-10リサーチ・developers.openai.com複数クエリでクロス確認）が根拠だが、本セッションでは公式ドキュメントへの再アクセスは行っていない。認証方式が変わっていた場合、実装時のHTTP 401で早期発覚するため実害は限定的 |
| A4 | OpenAIの429応答は`Retry-After`ヘッダーを返す | Don't Hand-Roll節 | STACK.md記載の既存リサーチに基づく（WebSearchクロス確認・MEDIUM confidence）。返さない場合でも既存の指数バックオフ（Retry-After無しの場合の分岐）が代替として機能するため実害は限定的 |

## Open Questions (RESOLVED)

> 2026-08-11 更新: 両問とも Phase 2 の計画側で決着済み（cross-AI レビュー 02-REVIEWS.md 反映時）。
> 以下の Recommendation は**当時のもの**であり、Q2 については後述のとおりプラン側が上書きしている。
> 実行時に従うべき契約は PLAN.md 側であり、この節ではない。

1. **OpenAIの正確なモデルラインナップ・vision対応モデルID** — **RESOLVED（運用面）**
   - What we know: `gpt-4o`系が確実にvision対応、本セッションのWebSearchでは`gpt-5.x`系が現行の主力という言及あり
   - What's unclear: `/v1/models`から実際に返るモデルIDの正確な命名規則・どのモデルがvision対応か
   - Recommendation（当時）: D-09のとおり実装時に実APIキーで`GET /v1/models`を1回呼び出し、結果を見てから`RECOMMENDED_MODELS`とヒューリスティックフィルタの正規表現を確定する。プランにこの確認を明示タスクとして含める
   - **Resolution:** 02-01 Task 1 の `checkpoint:decision`（D-09）で確定する。ただしレビュー HIGH-1 の指摘どおり **`GET /v1/models` はモデル ID の存在しか返さず能力確認にはならない**ため、Task 1 は Stage A（ID 実在確認）と Stage B（vision / `max_completion_tokens` / `temperature` / `reasoning_effort` 値域 / 単価を公式ドキュメントまたは最小実リクエストで確認）に分割された。成果物は新設の `02-CAPABILITY-MATRIX.md`（`evidence` 列で根拠種別を記録し、`inferred` 行は既定値に採用しない）で、02-02 / 02-03 / 02-04 がこれを単一情報源として消費する。

2. **`reasoning_effort`の値域はモデル世代ごとに異なる可能性** — **RESOLVED（プランが本節の Recommendation を上書き）**
   - What we know: 本セッションのWebSearchでは`none`/`minimal`/`low`/`medium`/`high`/`xhigh`/`max`という値域言及があった
   - What's unclear: 全ての推論系モデルが全ての値をサポートするか、モデル世代で値域が変わるか
   - Recommendation（当時・**採用されなかった**）: D-10と同じ「常に新形式を送り、非対応パラメータは省略する」安全側方針に従い、UIでは許可リストではなく自由入力または広めのcombobox選択肢を提供し、値の妥当性検証はAPI側のエラー応答に委ねる（未知の値を送っても400になるだけで、既存のエラーマッピングで捕捉可能）
   - **Resolution:** レビュー HIGH-4 が「未知値を API の 400 に委ねる設計は『パラメータ非互換でエラーにならない』という Phase 成功条件（V190-OAI-12）と矛盾する」と指摘したため、**自由入力は撤回**。02-04 は readonly Combobox + `effort_values_for_model()`（`02-CAPABILITY-MATRIX.md` 由来）で、選択中モデルに対して記録された値のみを提示する。値域未記録のモデルでは欄を無効化し `reasoning_effort` を送信しない。プロバイダ側 `_apply_gen_params` にも許容集合ガードを置く多層防御とする。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python標準ライブラリ`urllib.request` | OpenAI HTTP通信全般 | ✓ | Python 3.14.6同梱 | — |
| インターネット接続（api.openai.com疎通） | OCR/モデル一覧取得の実機テスト | 未確認（開発機依存） | — | 接続不可時はモック/monkeypatchベースの単体テストのみで進める（既存Claude/Geminiテストと同型） |
| OpenAI実APIキー | D-09のモデルラインナップ確認・実機動作確認 | 未確認（ユーザー提供が必要） | — | 実キーが無い場合はOpenAI公式ドキュメントを二次ソースとする（D-09に明記済み） |

**Missing dependencies with no fallback:** なし。

**Missing dependencies with fallback:** OpenAI実APIキー（D-09の確認手順に代替方針が既に明記されている）。

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1（`pyproject.toml`固定バージョン） |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`（`testpaths=["tests"]`） [VERIFIED: pyproject.toml:11-13] |
| Quick run command | `pytest tests/test_ocr_providers.py -x -q` |
| Full suite command | `pytest -q`（既知の環境フレーキー: STATE.md記載のTcl/Tkセットアップエラー・test_ocr_pipeline.py関連クラッシュが既知事象として存在。Phase 3で切り分け予定） |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| V190-CAT-01 | catalogの`PROVIDERS`内容が固定内容と一致 | unit | `pytest tests/test_ocr_provider_catalog.py -x` | ❌ Wave 0（新規） |
| V190-CAT-01 | `default_model_for(name)`がProviderの`RECOMMENDED_MODELS`に含まれる（D-05の機械保証） | unit | `pytest tests/test_ocr_provider_catalog.py -x` | ❌ Wave 0（新規） |
| V190-CAT-02 | `registry.py`が`os`以外の内部モジュールをimportしない | unit（静的解析ベース） | `pytest tests/test_ocr_provider_catalog.py -k independence -x` | ❌ Wave 0（新規・既存パターンなし） |
| V190-OAI-01/02 | `build_provider(settings, api_key="...")`が`name=="openai"`でOpenAIProviderを返す | unit | `pytest tests/test_ocr_providers.py -k openai -x` | ❌（既存`TestClaudeProviderBasic`等と同型で追加） |
| V190-OAI-02 | `registry.sensitive_keys()`が`openai_api_key`/`OPENAI_API_KEY`を含む | unit | `pytest tests/test_ocr_providers.py -k sensitive -x` | 既存パターンあり（`TestProviderKeyNotLogged`等）に追加 |
| V190-OAI-03 | ヒューリスティックフィルタが embedding/tts/whisper 等を除外・0件時にRECOMMENDED_MODELSへ合流 | unit | `pytest tests/test_ocr_providers.py -k list_models -x` | ❌（`TestClaudeProviderListModels`と同型で追加） |
| V190-OAI-04/05/06 | クラウド判定・送信先確認・コスト確認にopenaiが含まれる | unit | `pytest tests/test_provider_ui.py -k openai -x` / `pytest tests/test_batch_ocr_dialog.py -k openai -x` | ❌（既存フィクスチャに追加） |
| V190-OAI-11 | 新規pip依存が追加されていない | manual-only | `pip freeze`差分確認 / `requirements.txt`のgit diff確認 | — |
| V190-OAI-12 | 推論系モデルで`temperature`省略・`max_completion_tokens`送信 | unit | `pytest tests/test_ocr_providers.py -k reasoning -x` | ❌（`TestGeminiProviderNewGenerationPayload`と同型で追加） |
| V190-OAI-13 | 429/5xxが`OCRRetryableError`にマップされる | unit | `pytest tests/test_ocr_providers.py -k RetrySymmetry -x` | 既存パターンあり（`TestLMStudioRetrySymmetry`/`TestOllamaRetrySymmetry`）に`TestOpenAIRetrySymmetry`を追加 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_ocr_providers.py tests/test_ocr_provider_catalog.py -q`
- **Per wave merge:** `pytest -q`（既知フレーキーを除外する場合は `pytest -q --ignore=tests/test_ocr_pipeline.py` + 個別実行の分割方式、STATE.md記載の運用に倣う）
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ocr_provider_catalog.py` — catalog の `PROVIDERS`内容固定・`default_model_for`とProvider `RECOMMENDED_MODELS`の一致機械保証・独立性制約の静的検証（V190-CAT-01/02）
- [ ] `tests/test_ocr_providers.py` への `TestOpenAIProviderBasic`/`TestOpenAIProviderBuildPayload`/`TestOpenAIProviderOcrImage`/`TestOpenAIProviderListModels`/`TestOpenAIRetrySymmetry`（既存Claude/Gemini/LMStudioの各テストクラスと同型パターンで追加。テストファイル自体は既存＝Wave 0ギャップではなくクラス追加のみ）
- [ ] `tests/test_provider_ui.py`/`tests/test_batch_ocr_dialog.py` への openai 選択時のUI回帰テスト追加

*(catalogテストファイルのみ新規。既存テストファイルへのクラス/メソッド追加は各実装プランのTDDタスクに含める)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OpenAI APIキーは `Authorization: Bearer` ヘッダーのみで送信。セッション限定保持（`_session_api_keys`）・`pagefolio_settings.json` への非永続化を`_SENSITIVE_KEYS`ガードで構造的に強制（`registry.sensitive_keys()`から自動導出） |
| V3 Session Management | 該当薄 | デスクトップアプリのためWebセッション概念は無し。APIキーの「セッション」はアプリプロセスのメモリ寿命に等しい（既存5プロバイダと同一方針） |
| V4 Access Control | 該当薄 | 単一ユーザーローカルアプリのためロールベースアクセス制御は対象外 |
| V5 Input Validation | yes | org/project ID・detail・reasoning_effort等のユーザー入力値はAPIリクエストへの埋め込み前にstrip()・空文字判定を行う（既存Claude/Geminiセクションと同型パターン）。エンドポイントは固定URL（`api.openai.com`）でありユーザー入力URLではないため`_require_http_scheme`によるスキーム検証は不要（LM Studio/Ollama/RunPodとの違い） |
| V6 Cryptography | 該当薄 | 独自暗号化実装なし。HTTPS通信はurllib.requestの標準TLSに委譲（Claude/Gemini/RunPodと同一方針） |
| V7 Error Handling and Logging | yes | APIキーそのものをログ・エラーメッセージに含めない（既存`TestProviderKeyNotLogged`パターンを踏襲）。既存`errors.py`のエラーボディ切り詰め（500文字上限・L-6d）を継承 |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| APIキーの平文永続化・ログ漏洩 | Information Disclosure | `registry.sensitive_keys()`による構造的ガード（`settings.py:_SENSITIVE_KEYS`）。新規プロバイダ追加時も`PROVIDER_ENV_KEYS`への1行追加で自動的にガード対象に入る（V190-OAI-02） |
| 意図しない外部送信（コスト・プライバシー） | Information Disclosure | 送信先確認ダイアログ（`_confirm_cost`等）を毎回表示・「今後表示しない」を設けない既存方針を継承（V190-OAI-04/05） |
| プラグインプロバイダによるクラウド判定回避 | Elevation of Privilege（安全境界の迂回） | D-04のisinstanceフォールバック判定を維持し、catalog未登録でも既知クラウドプロバイダクラスを継承していればコスト確認を強制する二重判定 |
| フォールバック連鎖での送信先確認スキップ | Information Disclosure | `_propose_fallback`が各段で`messagebox.askyesno`による再確認を必須化（既存実装済み・V180-D-02の明示設定型フォールバック方針を継承） |

## Sources

### Primary (HIGH confidence)

- `pagefolio/ocr_providers/{registry,base,errors,claude,gemini,lmstudio,__init__}.py` — 本セッションで全文実読（HTTP実装パターン・独立性制約・エラーマッピング）
- `pagefolio/ocr.py` — 全文実読（`build_provider`・`_start_ocr`・`_cloud_providers`）
- `pagefolio/ocr_dialog.py`（該当箇所実読: 1-100, 800-940, 1216-1330, 2320-2460行） — 表示名/クラウド判定/コスト確認/フォールバック確認の重複実装確認
- `pagefolio/dialogs/batch_ocr.py`（該当箇所実読: 1-75, 480-620行） — 独立実装方針の設計コメント・同型分岐確認
- `pagefolio/dialogs/llm_config/{sections,dialog,model_fetch}.py`（該当箇所実読） — プロバイダ一覧・Claudeセクション雛形・モデル取得パターン
- `pagefolio/settings.py`（1-35行実読） — `_SENSITIVE_KEYS = sensitive_keys()` の実装確認
- `pagefolio/ocr_fallback.py` — 全文実読
- `pagefolio/lang.py`（grep実読） — LANG辞書のja/en構造確認
- `pyproject.toml` — ruff/pytest設定確認
- `.planning/phases/01-safety-rollback/01-02-SUMMARY.md` — Phase 1でのOCRDisabledError確立を確認
- `.planning/research/{ARCHITECTURE,SUMMARY,PITFALLS,STACK,FEATURES}.md`（2026-08-10作成） — discuss-phase土台の一次リサーチとして継承

### Secondary (MEDIUM confidence)

- WebSearch（本セッション2026-08-11実施・classify-confidence seam経由でMEDIUM判定）: OpenAI `max_completion_tokens`/`reasoning_effort`/`temperature`のo-series制約を再確認。ソース: [OpenAI o1 models require max_completion_tokens instead of max_tokens · Issue #724 · simonw/llm](https://github.com/simonw/llm/issues/724), [Azure OpenAI reasoning models guide](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning), [Create chat completion | OpenAI API Reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- WebSearch（本セッション）: OpenAIモデルラインナップの現況確認（gpt-5.x系が現行主力との言及）。ソース: [GPT-4o Model | OpenAI API](https://developers.openai.com/api/docs/models/gpt-4o), [All models | OpenAI API](https://developers.openai.com/api/docs/models/all)
- `.planning/research/STACK.md`記載のOpenAI公式ドキュメント参照（`developers.openai.com`ドメイン、2026-08-10リサーチ時点でクロス確認済み）

### Tertiary (LOW confidence)

- なし（本フェーズでは低確信度ソースへの依存を避けた）

## Metadata

**Confidence breakdown:**
- catalog一元化の設計: HIGH — 全て実コード読解に基づく重複マップの再検証済み
- OpenAI HTTP実装パターン: HIGH — 既存`LMStudioProvider`/`ClaudeProvider`/`GeminiProvider`の実装を土台にした差分実装であり、パターン自体は実証済み
- OpenAIモデルラインナップ・具体的モデルID: LOW〜MEDIUM — D-09のとおり実装時の実キー確認が必須（本RESEARCH.mdでは確定値を記載していない）
- reasoning_effort値域: MEDIUM — WebSearchクロス確認だが公式ドキュメント一次情報への直接アクセスは限定的

**Research date:** 2026-08-11
**Valid until:** 7日（OpenAIモデルラインナップは変動が速いため短めに設定。catalog設計・既存コードパターンの部分は30日程度安定）
