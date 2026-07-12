---
phase: 6
slug: gemini-provider
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-09
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| アプリ → Gemini API (generativelanguage.googleapis.com) | `GeminiProvider.ocr_image` / `list_models` が urllib で HTTPS POST/GET。`x-goog-api-key` ヘッダー認証。URL クエリ `?key=` 不使用 | base64 PNG 画像（非機密・OCR 用）+ プロンプト文字列 + API キー（ヘッダー内） |
| Gemini API → アプリ（レスポンス JSON） | candidates 構造・SAFETY/RECITATION ブロック。信頼できない外部入力として扱う | OCR テキスト（結果辞書のみ。logger・例外メッセージに非混入） |
| 環境変数（GEMINI_API_KEY / GOOGLE_API_KEY）→ Provider | `_resolve_api_key` 読み取りのみ。settings への書き込み禁止 | API キー（読み取り専用。settings/os.environ への書き込みなし） |
| OCRDialog プロデューサー → ワーカースレッド（キュー） | `queue.Queue(maxsize=concurrency+1)` 経由で base64 文字列を受け渡し。fitz/Tkinter オブジェクトはワーカーへ渡さない | base64 PNG 文字列のみ（送信後 `del b64` で即時破棄） |
| セッションキー（_session_api_keys）→ Provider 再生成 | `_session_api_keys["gemini"]` に格納。settings/os.environ への書き込みなし | API キー（メモリのみ・永続化禁止） |

---

## Threat Register

> **注**: Plan 03（UI 層）と Plan 04（並列処理層）で T-06-10〜T-06-13 が重複採番されたため、`-UI` / `-CONC` サフィックスで区別する。

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Information Disclosure | `GeminiProvider` 認証 | mitigate | `x-goog-api-key` ヘッダー方式採用、URL `?key=` クエリ不使用（D-05）。`ocr_providers.py:523,585` / grep 検証済み | closed |
| T-06-02 | Information Disclosure | `_resolve_api_key` / `build_provider` | mitigate | api_key は `os.environ` 読み取りのみ。settings への書き込みなし（D-01/D-05）。`_SENSITIVE_KEYS` ガード（`settings.py:17-26`）。テスト検証済み | closed |
| T-06-03 | Tampering / Spoofing | Gemini レスポンス解析 (`_parse_response`) | mitigate | `candidates` 空チェック → `promptFeedback.blockReason` 含む `RuntimeError`（Pitfall-D）。`ocr_providers.py:488-495`。テスト `TestGeminiProviderOcrImage` で検証 | closed |
| T-06-04 | Information Disclosure | 例外メッセージ / logger 出力 | mitigate | HTTP エラー本文は `body[:500]` で切り詰め。api_key・b64_png をメッセージに含めない設計。`ocr_providers.py:563` | closed |
| T-06-05 | Repudiation | 誤 env var による意図しない課金 | accept | `GEMINI_API_KEY` 名で `OCRAPIKeyError` を投げ、主 env var 名を明示。実コスト確認は Plan 03 UI ゲート（コスト確認ダイアログ）で担保。API 層のみでは完全防止不可 | closed |
| T-06-06 | Denial of Service / リソース枯渇 | `OCRDialog` / `_run_parallel_ocr` 画像メモリ | mitigate | `queue.Queue(maxsize=concurrency+1)` で同時保持制限（`ocr_dialog.py:876`, `ocr.py:183`）。`del b64` で送信後即時破棄（`ocr_dialog.py:1060`, `ocr.py:303`）。`TestProducerConsumerMemory` で機械検証 | closed |
| T-06-07 | Tampering | ワーカースレッド内 fitz アクセス排除 | mitigate | `_worker` 内に `fitz`/`get_pixmap`/`page_to_png_b64`/`self.doc[` 不在。fitz はプロデューサー（メインスレッド）専属（D-04）。コードレビュー・grep で確認 | closed |
| T-06-08 | Denial of Service | キャンセル時デッドロック | mitigate | `put` は `timeout=0.1` ループで Full 時に cancel 確認（Pitfall-B）。`get` は `timeout=1.0` で Empty 時に cancel 確認。`None` 終了シグナルでワーカー終了（Pitfall-E）。`TestProducerConsumerMemory` でデッドロック非発生検証 | closed |
| T-06-09 | Information Disclosure | 進捗・エラー表示 | mitigate | progress / error 文言に b64 画像データ・api_key を含めない設計ガード（T-04-09 踏襲）。SUMMARY 06-02 で確認 | closed |
| T-06-10-UI | Information Disclosure | `llm_config._apply` / `_save_settings` | mitigate | `_apply` は `gemini_model` のみ収集、api_key 系キーの収集ゼロ（D-01）。`dialogs/llm_config.py`。grep 検証済み | closed |
| T-06-11-UI | Information Disclosure | `ocr_dialog` セッションキー格納 | mitigate | gemini セッションキーは `_session_api_keys["gemini"]` のみに格納、settings / os.environ への書き込みなし（D-03）。`ocr_dialog.py`。grep 検証済み | closed |
| T-06-12-UI | Repudiation / 意図しない課金 | クラウド送信コスト確認ダイアログ | mitigate | gemini もコスト確認ダイアログ（送信先 `generativelanguage.googleapis.com`・ページ数・概算コスト）を毎回表示しキャンセル可能（Pitfall-F・OCR-UI-03 拡張）。`ocr_dialog.py` `_confirm_cost` | closed |
| T-06-13-UI | Spoofing | gemini モデル一覧取得 | accept | モデル更新ボタンは GEMINI_API_KEY/GOOGLE_API_KEY 読み取りのみ。失敗時は静的 `RECOMMENDED_MODELS` へフォールバック（D-08）。OCR 用途・モデル名のみで改ざんリスク低 | closed |
| T-06-10-CONC | Tampering | 複数ワーカー共有カウンタ（`_done` / `_workers_remaining` / `_fatal_msg`） | mitigate | `threading.Lock`（`_done_lock`）配下で全カウンタを読み書き（CR-01）。`ocr_dialog.py:83,996,1009,1015`。`TestWorkerConcurrency` で取りこぼし/二重計上なし検証 | closed |
| T-06-11-CONC | Denial of Service / リソース枯渇 | 複数ワーカーのデッドロック・飢餓 | mitigate | 終了シグナル `None` を `self.concurrency` 本送信し全ワーカーを確実終了（Pitfall-E）。`ocr_dialog.py:963-964`。`put`/`get` タイムアウトループでデッドロック防止 | closed |
| T-06-12-CONC | Repudiation / 表示整合性 | キャンセル時の結果二重挿入 | mitigate | `_finish_cancelled` / `_finish_complete` / `_finish_error` 冒頭の `if self._done: return` 冪等ガード（CR-02）。`ocr_dialog.py:1125,1142,1154`。`TestFinishIdempotent` で 1 回のみ実行を検証 | closed |
| T-06-13-CONC | Information Disclosure | `GOOGLE_API_KEY` 系の平文保存 | mitigate | `_SENSITIVE_KEYS` に `google_api_key`・`GOOGLE_API_KEY`・`GEMINI_API_KEY`・`ANTHROPIC_API_KEY` 大文字バリアントを追加（WR-03）。`settings.py:17-26`。`_save_settings` フィルタで JSON 書き込み禁止 | closed |
| T-06-14 | Denial of Service | Python 3.8 環境での OCR 機能全停止 | mitigate | `executor.shutdown` の `cancel_futures` を `sys.version_info >= (3, 9)` 分岐でガード（WR-02）。`ocr.py:321-324,448-451`。3.8 の `TypeError` 回避 | closed |
| T-06-SC | Tampering | 外部 pip/npm/cargo パッケージ追加 | accept | 本フェーズは外部 pip パッケージ追加ゼロ。標準ライブラリ（`queue`, `threading`, `urllib`, `sys`）のみ追加。依存関係汚染リスクなし（Package Legitimacy Audit: 該当なし） | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-05 | API 層単独では誤 env var による意図しない課金を完全防止できない。主 env var 名（`GEMINI_API_KEY`）で明示 `OCRAPIKeyError` を投げることで誤認を最小化。実際のコスト制御は Plan 03 UI コスト確認ダイアログ（T-06-12-UI）と組み合わせて担保済み | mistyura | 2026-06-09 |
| AR-06-02 | T-06-13-UI | gemini モデル一覧取得（`list_models`）は GEMINI_API_KEY/GOOGLE_API_KEY 読み取りのみで OCR 用途のモデル名文字列のみを扱う。API 応答が改ざんされても最悪ケースは不正モデル名での OCR 失敗（RuntimeError）であり、機密情報漏洩・コード実行には至らない | mistyura | 2026-06-09 |
| AR-06-03 | T-06-SC | 外部 pip パッケージ追加ゼロのため、サプライチェーン汚染リスクは本フェーズでは発生しない。標準ライブラリのみ追加（`queue`, `threading`, `urllib`, `sys`） | mistyura | 2026-06-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-09 | 19 | 19 | 0 | gsd-secure-phase (sonnet) — plan-time register 全件 CLOSED 確認。実装コードスポット検証: T-06-01/02/03/06/10-CONC/12-CONC/13-CONC/14 をコード直接確認。残はSUMMARY Threat Model Coverage 節で検証済み |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-09
