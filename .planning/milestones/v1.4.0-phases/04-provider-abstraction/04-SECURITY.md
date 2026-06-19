---
phase: 4
slug: provider-abstraction
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-06
---

# Phase 4 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| アプリ → LM Studio (localhost:1234) | `LMStudioProvider.ocr_image` / `list_models` が urllib で HTTP POST。接続先 URL は settings (`lm_studio_url`, 既定 localhost:1234) 由来。新規外部接続先は追加なし | base64 PNG 画像 + プロンプト（非機密・ローカル LAN） |
| メインスレッド (fitz/Tkinter) ↔ ワーカースレッド (HTTP IO) | fitz.Document / Tkinter ウィジェットはメインスレッド専用。ワーカーへ渡すのは base64 文字列と provider のみ | base64 文字列・provider 参照（fitz オブジェクトは渡さない） |
| fitz.Page → has_embedded_text / get_text | 埋め込みテキスト抽出はローカル処理のみ。外部送信なし（むしろ送信を減らす方向） | 抽出テキスト（アプリ内のみ・logger/例外に混入させない） |
| settings の ocr_provider 値 → build_provider | 未対応値は ValueError。`_start_ocr` が捕捉しグレースフルなエラー表示に変換 | プロバイダ名・URL・model・数値パラメータ（秘密情報なし） |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-04-01 | Information Disclosure | `OCRAPIKeyError` / Provider 属性 | accept | APIキー秘密情報を扱わない。`OCRAPIKeyError` は env_var 名のみ保持（キー値なし）。`ocr_providers.py:58-63`。`pagefolio/` 全体で `os.environ`/`getenv` 0 件 | closed |
| T-04-02 | Spoofing / SSRF | `LMStudioProvider.ocr_image` / `list_models` urllib 接続先 | accept | 接続先 URL は settings `lm_studio_url` 由来（コンストラクタ経由）。新規外部接続先・任意 URL なし。`# noqa: S310` は既存方針 V14-D-01 継承。`ocr_providers.py:86,130,173,133,140,174,176` | closed |
| T-04-03 | Information Disclosure | 例外メッセージ / logger 出力 | mitigate | 例外メッセージは `body[:500]` で切り詰め、秘密を含めない。base64 は HTTP body のみで logger に出さない。`ocr_providers.py:160,191,103,131`・`ocr.py:143` | closed |
| T-04-04 | Tampering / Crash | run_parallel 並列実行と fitz スレッド境界 | mitigate | executor target `_call` に fitz/get_pixmap なし。文字列辞書のみ受領。`ocr.py:129-144` | closed |
| T-04-05 | Information Disclosure | has_embedded_text の page.get_text() 抽出テキスト | mitigate | bool のみ返却。抽出テキストを logger に出さない。`ocr.py:59-80`（line 79 は例外のみログ） | closed |
| T-04-06 | Information Disclosure | build_provider が読む settings | accept | APIキー非取り扱い（lmstudio のみ）。URL/model/数値パラメータのみ読む。`ocr.py:198-202` | closed |
| T-04-07 | Tampering / Crash | `_worker` のスレッド境界（fitz 並行アクセス） | mitigate | `_worker` 本体に fitz/`self.doc[` なし。レンダリング・get_text は `_render_next_page`（メインスレッド）に集約。`ocr_dialog.py:545-592,496-538` | closed |
| T-04-08 | Denial of Service / Crash | ワーカーからの Tkinter ウィジェット直接操作 | mitigate | 進捗・スキップ・結果更新はすべて `self.after(0, ...)` 経由。`ocr_providers.py` に Tkinter 参照 0 件。`ocr_dialog.py:556-591` | closed |
| T-04-09 | Information Disclosure | スキップページの get_text() テキストの扱い | mitigate | 抽出テキストは結果辞書/結果テキスト領域のみで使用、logger/例外に混入なし。`ocr_dialog.py:524-526` | closed |
| T-04-10 | Information Disclosure | settings の ocr_provider 永続化 | accept | 追加は `ocr_provider:"off"` のみで秘密情報なし。APIキーを settings に書かない。`settings.py:45` | closed |
| T-04-11 | Denial of Service / Crash | `_start_ocr` の未捕捉 ValueError（未対応プロバイダ名） | mitigate | `build_provider` を `try/except ValueError` で囲み、`messagebox.showerror`+`logger`+`return`。Tkinter コールバックへの例外伝播を遮断。`ocr.py:241-251` | closed |
| T-04-12 | Tampering / Crash | CR-02 provider 再生成のスレッド境界 | mitigate | provider 再生成は `_on_run`（メインスレッド）のみ。ワーカー開始前に実行。`ocr_dialog.py:459-489,540` | closed |
| T-04-13 | Information Disclosure | ダイアログ UI 値（model/max_tokens/temperature/URL） | accept | すべてローカル OCR 用の非機密パラメータ。APIキー非取り扱い。`dialogs/llm_config.py:80-419`・`ocr_dialog.py:57-63` | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-01 | 本フェーズは APIキー秘密情報を一切扱わない内部リファクタ。クラウド Provider・キー流入は Phase 5（V14-D-02）。`os.environ` 読み出しの追加なし（grep 0 件で確認） | mistyura | 2026-06-06 |
| AR-04-02 | T-04-02 | 接続先はローカル LM Studio（既定 localhost:1234）のみ。settings 由来 URL を踏襲し新規外部接続先・任意 URL は追加なし。`# noqa: S310` は既存方針 V14-D-01 継承 | mistyura | 2026-06-06 |
| AR-04-03 | T-04-06 | build_provider は lmstudio のみ生成し URL/model/数値パラメータのみ読む。claude/gemini と APIキーは Phase 5/6 | mistyura | 2026-06-06 |
| AR-04-04 | T-04-10 | settings 追加は `ocr_provider:"off"` のみ。APIキーは settings に書かない（V14-D-02 ガードは Phase 5 直前タスク） | mistyura | 2026-06-06 |
| AR-04-05 | T-04-13 | ダイアログ UI 値はローカル LM Studio OCR リクエスト用の非機密パラメータのみ。APIキーは扱わない | mistyura | 2026-06-06 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-06 | 13 | 13 | 0 | gsd-security-auditor (sonnet) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-06
