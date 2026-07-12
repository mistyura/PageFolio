---
phase: 05
slug: claude-provider-ui
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-07
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Phase 05 は Anthropic Claude API による OCR を追加し、API キーの安全な取り扱い・クラウド送信ゲート・コスト確認を実装した。API キーが平文でディスク/ログ/外部へ漏洩しないこと、ユーザー無確認の課金送信が起きないことが本フェーズのセキュリティ中核。

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| アプリ → Anthropic API (api.anthropic.com) | ページ画像 base64 と API キーが外部ホストへ送信される | ページ画像（機密度: 中〜高）・API キー（高） |
| API キー → ログ / 例外 / レスポンス | キー値が二次的に漏洩しうる経路 | API キー（高） |
| settings 辞書 → pagefolio_settings.json | 機密キーが平文でファイルへ流出しうる最大の境界 | API キー（高） |
| 環境変数 / セッションキー → build_provider → ClaudeProvider | キーがアプリ内部を流れ Provider へ注入される | API キー（高） |
| LLMConfigDialog / OCRDialog 入力 → settings / 画面表示 | UI 入力値が永続化・表示される（マスク要） | API キー（高） |
| OCRDialog → Anthropic API（実行ゲート） | クラウド送信の最終ゲート（コスト確認・キャンセル） | ページ画像・課金 |
| run_parallel → 外部 API（リトライループ） | レート制限・過負荷・コスト暴走への耐性境界 | API リクエスト（コスト） |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-01 | Information Disclosure | ClaudeProvider.ocr_image の例外/ログ | mitigate | api_key を例外メッセージ・ログに含めない。HTTPError 本文はサーバ応答のみ（`ocr_providers.py:342-345,351`） | closed |
| T-05-02 | Information Disclosure | レスポンス解析（content 走査） | mitigate | 不正レスポンスは `body[:500]` のみエラーに含める。OCR 結果にキー混入なし（`ocr_providers.py:370,373`） | closed |
| T-05-03 | Tampering / DoS | 429/5xx の無制限リトライ | mitigate | Provider は OCRRetryableError 通知のみ。回数管理は run_parallel が MAX_RETRIES=3 で制御（`ocr_providers.py:342-345` / `ocr.py:179-212`） | closed |
| T-05-04 | Spoofing / Information Disclosure | anthropic-version ヘッダー欠落 | mitigate | `ANTHROPIC_VERSION = "2023-06-01"` 定数を全リクエストに付与（`ocr_providers.py:213,325`） | closed |
| T-05-05 | Information Disclosure | _save_settings の JSON 書込 | mitigate | `_SENSITIVE_KEYS` を保存前に除外コピー。保存後 JSON にキー文字列が出ない（`settings.py:16,71-79`） | closed |
| T-05-06 | Information Disclosure | _save_settings の logger | mitigate | キー混入時もキー値は出さずキー名のみ警告（`settings.py:73-76`） | closed |
| T-05-08 | Information Disclosure | build_provider のキー扱い | mitigate | api_key は引数注入のみ。settings に書かない・読まない（`ocr.py:273-284`） | closed |
| T-05-09 | Information Disclosure | _resolve_api_key の os.environ 操作 | mitigate | `os.environ.get()` 読み取りのみ。`os.environ[` 代入 grep 0 件（`ocr.py:77`） | closed |
| T-05-10 | DoS / Cost | run_parallel のリトライ | mitigate | MAX_RETRIES=3 で打ち切り・Retry-After 優先 sleep・無限ループなし（`ocr.py:49,179-212`） | closed |
| T-05-11 | Information Disclosure | キー未設定時のクラウド送信（`_start_ocr` での return） | accept | 宣言緩和（`_start_ocr` で return し OCRDialog 非生成）は 05-05 のセッションキー入力欄導入で T-05-19 へ移行。外部送信ブロックは T-05-19 が担保（下記 Accepted Risks Log 参照） | closed |
| T-05-12 | Information Disclosure | LLMConfigDialog._apply の保存 | mitigate | api_key 系を llm_settings に入れない。設定ダイアログにキー入力欄を置かない（`dialogs/llm_config.py:598-645`） | closed |
| T-05-13 | Information Disclosure | モデル更新の env 読取 | mitigate | `os.environ.get()` 読み取りのみ。settings 書込なし・ステータスにキー値を出さない（`dialogs/llm_config.py:566`） | closed |
| T-05-14 | Tampering / Cost | off 時の意図しないクラウド送信 | mitigate | off で OCR ボタン 2 件を disabled 化（`app.py:134-145` / `ui_builder.py:538,545,553,563`） | closed |
| T-05-15 | Spoofing | effort 非対応モデルへの effort 送信 | mitigate | 多層防御: UI 非表示（`dialogs/llm_config.py:476-491`）+ payload 制御（`ocr_providers.py:258-266`） | closed |
| T-05-16 | Information Disclosure | セッションキー入力欄の表示 | mitigate | `show="*"` マスク Entry。キー値をログ・結果・エラーに渡さない（`ocr_dialog.py:358-368`） | closed |
| T-05-17 | Information Disclosure | セッションキーの保持先 | mitigate | `_session_api_keys["claude"]` にのみ格納。settings と分離した別オブジェクト（`ocr_dialog.py:729` / `app.py:71`） | closed |
| T-05-18 | Tampering / Cost / Privacy | クラウドへの無確認・大量ページ送信 | mitigate | クラウド時のみ `_confirm_cost`（送信先・ページ数・概算・プライバシー3点）を毎回表示・キャンセル可（`ocr_dialog.py:679-701,714,731-734`） | closed |
| T-05-19 | Information Disclosure | キー未設定でのクラウド送信 | mitigate | env 未設定 + 入力欄空で `ocr_api_key_missing` を showerror し return。run_parallel に到達しない（`ocr_dialog.py:716-727`） | closed |
| T-05-20 | DoS | 待機中表示時のスレッド安全 | mitigate | waiting 進捗更新は `self.after(0, ...)` 経由でメインスレッドへ委譲（`ocr_dialog.py:877-886`） | closed |
| T-05-SC | Tampering | npm/pip/cargo installs | accept | 新規 pip 依存ゼロ（urllib/os/tkinter 等 stdlib のみ）。requirements.txt に新規追加なし | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-11 | 05-03 当時の宣言緩和は「`_start_ocr` がキー未解決時に return し OCRDialog を生成しない」だったが、05-05 で OCRDialog にマスク付きセッションキー入力欄（成功基準3）を追加したため、早期 return すると入力欄を表示できず機能矛盾となる。緩和は T-05-19（`OCRDialog._on_run` の空入力チェック → `ocr_api_key_missing` で実行中止）へ正しく移行した。T-05-19 は CLOSED（`ocr_dialog.py:716-727` で検証済み）であり、キー未設定時の外部送信ゼロという本来のセキュリティ目的は完全に担保される。実リスクなし・文言ドリフトのみ。 | mistyura | 2026-06-07 |
| AR-05-02 | T-05-SC | 新規パッケージインストールなし（stdlib のみ）。サプライチェーンリスクは構造的に発生しない。 | mistyura | 2026-06-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-07 | 21 | 19 | 1 | gsd-security-auditor (sonnet) |
| 2026-06-07 | 21 | 21 | 0 | mistyura（T-05-11 を AR-05-01 として受容） |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-07
