---
last_mapped_commit: fb41c422035fa9d4fac753920909da56e068555c
---

# PageFolio — 外部サービス連携 (Integrations)

このアプリケーションは、外部 LLM API およびローカル OCR / 推論エンジンと連携して、PDF ページからの画像ベース OCR やドキュメント要約生成を行うことができます。

## OCR / LLM 連携プロバイダ一覧

| プロバイダ名 | クラス名 | 通信先 / 依存ツール | 認証・環境変数 | テキスト補完対応 |
| :--- | :--- | :--- | :--- | :--- |
| **Claude** | `ClaudeProvider` | Anthropic Claude API (`https://api.anthropic.com`) | `ANTHROPIC_API_KEY` | あり |
| **Gemini** | `GeminiProvider` | Google Gemini API (`https://generativelanguage.googleapis.com`) | `GEMINI_API_KEY` | あり |
| **RunPod** | `RunPodProvider` | RunPod Serverless API エンドポイント | `RUNPOD_API_KEY` | あり |
| **LM Studio** | `LMStudioProvider` | ローカル起動サーバ (`http://localhost:1234`) | 不要 (URL 変更可) | あり |
| **Ollama** | `OllamaProvider` | ローカル起動サーバ (`http://localhost:11434`) | 不要 (URL 変更可) | あり |
| **Tesseract** | `TesseractProvider` | ローカル `tesseract` 実行ファイル (CLI) | 不要 (パス指定要) | なし |

---

## 認証情報とセキュリティポリシー

### 1. API キーの非保存ガード (Keyguard)
セキュリティ上の重大リスクを防止するため、クラウドサービス用の API キー（`ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `RUNPOD_API_KEY`）は、**設定ファイル `pagefolio_settings.json` には一切保存されません**。
- **読み込み経路**: アプリ起動時に環境変数から取得されます。
- **セッション保持**: アプリの LLM 設定ダイアログ等でユーザーが入力したキーは、実行中のメモリ辞書（`self._session_api_keys`）にのみ保持され、アプリ終了時に破棄されます。
- **自動テスト**: `tests/test_settings_keyguard.py` および `tests/test_source_keyguard.py` によって、キーが誤って設定ファイルに書き込まれたり、ソースコード中にプレースホルダー等がハードコードされていないかチェックされます。

### 2. URL スキーム制限 (L-6e・D-13)
ユーザー定義のエンドポイントを指定可能なプロバイダ（LM Studio, Ollama, RunPod）に対して、悪意あるローカルファイル読み込みや偽装スキームの実行を防止するセキュリティ対策が適用されています。
- リクエスト送信（API 接続・モデル一覧取得）の直前で、URL のスキームが `http` または `https` に限定されているか検証されます (`_require_http_scheme` 関数)。
- `file://` など、非対応のスキームが入力された場合は `RuntimeError` を送出してリクエストをブロックします。

---

## 通信制御と例外ハンドリング

### 1. タイムアウト設定
モデル一覧の動的取得におけるフリーズを防止するため、プロバイダごとにタイムアウト値 (`model_list_timeout`) が設定されています。
- ローカルプロバイダ (LM Studio / Ollama): 即応するため **10 秒**
- クラウドプロバイダ (Claude / Gemini): ネットワーク遅延を考慮し **30 秒**
- RunPod: サーバーレスのコールドスタートを許容するため **90 秒**

### 2. リトライとレート制限 (429/5xx)
一時的な API 障害やレート制限（HTTP 429 / 5xx）への対策として、リトライ機構が備わっています。
- `urllib.request` から取得した `Retry-After` ヘッダーを解析し、最大 60 秒にクランプして待機します。
- 待機処理 (`interruptible_sleep`) は 0.5 秒単位で分割実行され、待機中であってもユーザーによる UI キャンセルを即時検出します。

---

## データ形式
- **OCR 送信**: レンダリングされた PDF の各ページ画像は、PNG 形式の Base64 文字列として API ペイロードに埋め込まれ送信されます。
- **テキスト応答の途切れ**: Claude / Gemini は、レスポンスの `finish_reason` または `stop_reason` を監視し、トークン上限超過などによる途切れを検出します (`ocr_image_ex` 戻り値の `truncated: bool` 警告フラグ)。
