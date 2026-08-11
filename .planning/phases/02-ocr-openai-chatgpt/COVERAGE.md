# API Coverage — OpenAI (ChatGPT) HTTP API

> Full coverage by default. Opt-outs are explicit, reasoned decisions.
>
> **再判定の宣言:** OpenAI は PageFolio にとって 6 番目の OCR プロバイダだが、
> Gemini / Claude / RunPod / LM Studio / Ollama の opt-out 集合を継承していない。
> 下表の全行を OpenAI 単独の全面被覆（full-coverage）ベースラインから再決定した
> （first-class / fallback の非対称が暗黙に蓄積するのを防ぐため）。
>
> **Phase:** 02-ocr-openai-chatgpt / **Decided:** 2026-08-11 / **ASVS level:** 1

## Chat / Vision（本フェーズの主経路）

| capability | decision | reason |
|---|---|---|
| `POST /v1/chat/completions` — 画像入力（`image_url` + base64 data URI）| INTEGRATE | |
| `POST /v1/chat/completions` — テキストのみ（全ページ統合サマリ）| INTEGRATE | |
| `image_url.detail` = `low` / `high` / `auto` | INTEGRATE | V190-OAI-08・既定 `high`（D-16）|
| `max_completion_tokens` | INTEGRATE | D-10・常用する新形式 |
| `max_tokens`（Chat Completions 旧形式）| OPT-OUT | OpenAI が非推奨化し o-series では 400。D-10 により常に新形式のみ送る |
| `temperature`（非推論系モデル）| INTEGRATE | D-11 |
| `temperature`（推論系 o-series）| OPT-OUT | API が拒否する。D-11/D-13 の単一判定で省略する |
| `reasoning_effort` | INTEGRATE | V190-OAI-09・D-15（OpenAI 専用ウィジェット / 専用 settings キー）|
| `finish_reason == "length"` による途切れ検出 | INTEGRATE | 既存 `ocr_image_ex` / `complete_text_ex` 契約に合わせる |
| `stream: true`（ストリーミング応答）| OPT-OUT | PageFolio の OCR は 1 ページ 1 リクエストの完了待ちで、部分描画 UI を持たない。既存 5 プロバイダも非ストリーミング |
| `tools` / function calling | OPT-OUT | OCR・要約はテキスト生成のみでツール実行を必要としない |
| `response_format` / structured outputs | OPT-OUT | 出力は Markdown/プレーンテキストで、スキーマ拘束の要件が無い（`ocr_prompt_preset` が表示形式を担う）|
| `n` / `top_p` / `seed` / `logprobs` / `stop` | OPT-OUT | 既存 5 プロバイダのいずれも露出しておらず、UI に対応する設定項目が無い |
| `user`（不正検知用エンドユーザー ID）| OPT-OUT | 単一ユーザーのローカルデスクトップアプリで、送出できる安定した ID を持たない。送ると匿名性を下げる |

## Models / 認証 / ヘッダ

| capability | decision | reason |
|---|---|---|
| `GET /v1/models` — モデル一覧取得 | INTEGRATE | V190-OAI-03 |
| モデル一覧のヒューリスティックフィルタ（embedding / tts / whisper / dall-e / moderation 除外）| INTEGRATE | D-07（OpenAI には vision 対応フラグが無い）|
| フィルタ 0 件・取得失敗時の静的フォールバック | INTEGRATE | D-08・V190-OAI-03 |
| `Authorization: Bearer <key>` | INTEGRATE | V190-OAI-02 |
| `OpenAI-Organization` ヘッダ | INTEGRATE | V190-OAI-10・空なら非付与（D-17）|
| `OpenAI-Project` ヘッダ | INTEGRATE | V190-OAI-10・空なら非付与（D-17）|
| organization / project の自動検出（`GET /v1/organizations` 等）| OPT-OUT | REQUIREMENTS.md Out of Scope（V190-F-02・v2 登録済み）|
| OAuth / API キー以外の認証 | OPT-OUT | REQUIREMENTS.md Out of Scope。API キー方式で既存 5 プロバイダと安全境界を揃える |
| 公式 Python SDK（`openai` pip パッケージ）| OPT-OUT | V190-OAI-11 / V14-D-01（新規 pip 依存ゼロ・`urllib.request` 直叩き）|

## エラー / レート制限

| capability | decision | reason |
|---|---|---|
| 429 レート制限 + `Retry-After` 尊重 | INTEGRATE | V190-OAI-13（既存 `errors.py` 基盤を流用）|
| 5xx の指数バックオフ再試行 | INTEGRATE | V190-OAI-13 |
| `context_length_exceeded` のマッピング | INTEGRATE | D-12（`_CONTEXT_ERROR_MARKERS` に既存）|
| その他 4xx → `RuntimeError` | INTEGRATE | D-12 |
| レート制限ヘッダ（`x-ratelimit-*`）の UI 表示 | OPT-OUT | 実コスト計測・課金トラッキングは v2 の Deferred 項目（STATE.md Deferred Items）。既存 5 プロバイダも未表示 |

## 本フェーズが触れない OpenAI API 面

| capability | decision | reason |
|---|---|---|
| `POST /v1/responses`（Responses API）| OPT-OUT | REQUIREMENTS.md Out of Scope（V190-F-01）。PageFolio の OCR/要約はステートレス単発呼び出しで agentic 機能を必要としない |
| Batch API（`POST /v1/batches`）| OPT-OUT | PageFolio のバッチ OCR は対話的な進捗表示・中止操作を伴うローカル並列実行で、24 時間非同期バッチの UX と噛み合わない |
| Files API（`POST /v1/files`）| OPT-OUT | 画像は base64 data URI でインライン送信する（既存 5 プロバイダ共通の `page_to_png_b64` 経路）。ファイル永続化は外部保存を増やすだけで利点が無い |
| Assistants API / Threads | OPT-OUT | ステートフルな会話継続を必要としない（Responses API と同じ理由）|
| Embeddings（`/v1/embeddings`）| OPT-OUT | 本アプリに検索・類似度機能が無い |
| Audio（`/v1/audio/*` — whisper / tts）| OPT-OUT | PDF ページ画像の OCR が対象で音声入出力を扱わない |
| Images（`/v1/images/*` — dall-e）| OPT-OUT | 画像生成の機能要件が無い |
| Moderation（`/v1/moderations`）| OPT-OUT | ローカル単一ユーザーの自分の文書を自分で読むユースケースで、投稿モデレーションの対象が存在しない |
| Fine-tuning（`/v1/fine_tuning/*`）| OPT-OUT | 汎用 vision モデルの OCR 精度で要件を満たす。学習データの外部送信も避ける |
| Usage / Billing API | OPT-OUT | プロバイダ別の詳細な実コスト計測・課金トラッキングは v2（STATE.md Deferred Items）。本フェーズは既存の概算コスト確認ダイアログで統一する |
