---
phase: 02
slug: ocr-openai-chatgpt
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-11
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

**Register origin:** `register_authored_at_plan_time: true` — 4 つの PLAN（02-01 / 02-02 / 02-03 / 02-04）すべてが `<threat_model>` ブロックを持ち、脅威レジスタは計画時に作成済み。本監査は「緩和策の実在検証」であり新規脅威探索ではない。

**Verification depth:** ASVS L1（grep 深度）。`workflow.security_asvs_level: 1` かつ `threats_open: 0` かつ計画時レジスタ済みのため、短絡規則によりオーケストレータが直接検証（auditor サブエージェント spawn は不要）。

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| アプリメモリ（`_session_api_keys`）→ ディスク（`pagefolio_settings.json`） | 機密が永続化層を越える地点。`_SENSITIVE_KEYS` が唯一のガード | OpenAI API キー（機密） |
| ローカルアプリ → `api.openai.com`（第三者・TLS） | ページ画像と API キーがプロセス外・組織外へ出る地点 | ページ画像 base64・API キー（機密・個人情報を含み得る） |
| ユーザー入力（settings 値）→ HTTP リクエスト | `organization` / `project` / `reasoning_effort` / `detail` が API リクエストへ埋め込まれる地点 | 任意文字列（信頼されない入力） |
| 手編集された `pagefolio_settings.json` → HTTP リクエスト | UI 検証を迂回して値が入る地点（多層防御が必要な理由） | 任意文字列（信頼されない入力） |
| サードパーティプラグイン → クラウド判定の安全境界 | `PluginManager.register_ocr_provider` 経由のコードが同意ゲートを迂回し得る地点 | 実行コード（信頼されない） |
| 表示（確認ダイアログ）→ 実際の送信先・実際の課金 | ユーザーが同意した対象・量と実態が一致していることが同意の前提 | 送信先ホスト・概算コスト |
| フォールバック連鎖 → 第三者への課金付きリクエスト | 最初に同意した送信先と異なる先へ切り替わる地点 | ページ画像 base64・API キー |
| バックグラウンドスレッド → Tk メインスレッド | `_fetch_models_async` の `after(0)` 越境 | モデル一覧（非機密） |
| 能力マトリクス（計画成果物）→ 実装定数 | 誤ったモデル能力・単価が既定値になると同意の前提が壊れる地点 | モデル ID・単価 |
| 実機確認の操作 → ログ / 画面録画 / SUMMARY | 実 API キーが記録媒体へ漏れ得る地点 | OpenAI API キー（機密） |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Information Disclosure | `settings.py:_save_settings` / `registry.sensitive_keys()` / `dialog.py:_apply` | critical | mitigate | `registry.py:23` に `"openai": ("OPENAI_API_KEY",)` を追加し `sensitive_keys()` が 3 バリアントを自動導出。`settings.py:29` で `_SENSITIVE_KEYS = sensitive_keys()`、`:318` で漏洩検出ログ、`:325` で保存対象から除外。`_apply` はキーを `llm_settings` へ入れずセッション同期のみ。テスト: `TestCatalogSensitiveKeyGuard`（tests/test_ocr_provider_catalog.py）・`TestApiKeyNotInSettings`（tests/test_provider_ui.py）。実機 Task 3A で再起動後のキー欄空・JSON 非永続化を人手確認済み | closed |
| T-02-02 | Information Disclosure | `openai_provider.py:_headers` / `_post_chat` の例外パス | high | mitigate | 例外メッセージはレスポンス body 先頭 500 文字のみ（`openai_provider.py:413,430,449,510`）でリクエストヘッダを含まない。`_post_chat` の HTTPError は共有 `_raise_mapped_http_error` へ委譲。`model_fetch.py` の `_on_error` はテンプレート + 例外オブジェクトのみをログへ渡す。テスト: `TestProviderKeyNotLogged`（tests/test_ocr_providers.py） | closed |
| T-02-03 | Information Disclosure | ページ画像の `api.openai.com` への送信（`ocr.py:_start_ocr` / `ocr_dialog.py` / `batch_ocr.py`） | high | mitigate | `catalog.py:115-122` の `ProviderMeta("openai", is_cloud=True, host="api.openai.com")` により単発・バッチ両経路で同意ゲート対象。「今後表示しない」抑止オプションは非実装。テスト: `TestConfirmDenialStopsSend`（tests/test_provider_ui.py）が「いいえ」で `build_provider` にも HTTP にも到達しないことを固定。実機 Task 3B で確認ダイアログの実描画・拒否時の非送信を人手確認済み | closed |
| T-02-04 | Spoofing | 確認ダイアログの表示ホスト vs `OpenAIProvider.CHAT_ENDPOINT` | high | mitigate | 表示ホストの情報源を `catalog.host_for`（`catalog.py:145`）の 1 箇所へ統合。`CHAT_ENDPOINT`（`openai_provider.py:221`）/ `MODELS_ENDPOINT`（`:222`）は同ホストの固定 https 定数。テスト: `TestConfirmedHostMatchesProviderEndpoint`（tests/test_ocr_providers.py）が openai / claude / gemini の 3 者を機械保証 | closed |
| T-02-05 | Tampering | `dialog.py:_apply` / `openai_provider.py:_headers`（org / project のヘッダ埋め込み） | high | mitigate | 2 層防御。入力境界: `_validate_openai_id`（`dialog.py:34`）が印字可能 ASCII（`\x21`–`\x7E`）・長さ 1〜`_OPENAI_ID_MAX_LEN`(128) 以外を拒否。ヘッダ境界: `_sanitize_header_value`（`openai_provider.py:107`）が制御文字を含む値を空へ倒し、`_headers`（`:274-292`）は真値のときだけヘッダを付与 | closed |
| T-02-06 | Denial of Service（第三者への増幅） | リトライ・バックオフ + フォールバック連鎖 | medium | mitigate | `openai_provider.py` に独自の待機・再送を実装せず、既存 `clamp_retry_after`（60 秒上限）/ `interruptible_sleep` / `MAX_RETRIES` / サーキットブレーカーのみを経路とする。フォールバック連鎖は各段でユーザー同意を要求し自動続行しない（`_fallback_tried` で同一候補を再試行しない）。テスト: `TestOpenAIProviderNoLocalRetryOrInsecureTLS`（tests/test_ocr_providers.py）の AST 検査 | closed |
| T-02-07 | Elevation of Privilege | プラグインプロバイダのクラウド判定迂回（`ocr_dialog.py` / `batch_ocr.py`） | medium | mitigate | `catalog.is_cloud_provider()` は未登録プロバイダに False を返すが、既知クラウド Provider クラスを継承したインスタンスは `ocr_dialog.py:973-976` の isinstance ガードで True へ倒す（D-04・意図的な二重経路の安全側設計） | closed |
| T-02-08 | Information Disclosure | TLS 検証の無効化 | high | mitigate | `urllib.request.urlopen`（`openai_provider.py:379,493`）を既定 SSL コンテキストで呼び、`ssl` の import と `context=` 指定を行わない（`:367-369` に契約を明記）。テスト: `TestOpenAIProviderNoLocalRetryOrInsecureTLS` の AST 検査 | closed |
| T-02-09 | Repudiation | 同意記録の欠如 | low | accept | R-02-01 参照。PageFolio はローカル単一ユーザーアプリで監査ログ機構を持たず、同意は「毎回ダイアログを出す」ことで担保する設計 | closed |
| T-02-10 | Information Disclosure | `ocr_dialog.py:_propose_fallback` のフォールバック連鎖での確認スキップ | high | mitigate | `_propose_fallback`（`ocr_dialog.py:2449-2455`）が各段で `messagebox.askyesno` による送信先再確認を必須化し、抑止パラメータを持たない。確認本文に OpenAI 表示名と `api.openai.com` が両方出ることをテストで固定。実機 Task 3C で `ConnectionError` 誘発によるフォールバック発動と送信先再提示を人手確認済み | closed |
| T-02-11 | Information Disclosure | `api.openai.com/v1/models` へのキー送信 | medium | accept | R-02-02 参照。V190-OAI-03 が要求する機能そのもの。明示的なボタン押下時のみ発火し、`GET /v1/models` は課金対象外・ページ画像を含まない | closed |
| T-02-12 | Denial of Service | モデル更新ボタン連打によるスレッド増殖 | low | mitigate | `_fetch_models_async` の `_model_fetch_running` ガード（`model_fetch.py:142-160`）で二重起動しない。`_refresh_openai_models` が独自 `threading.Thread` を起動しないことを AST アサーションで固定 | closed |
| T-02-13 | Tampering | プロバイダ combobox への未知プロバイダ名の混入 | medium | mitigate | `provider_combo`（`sections.py:97-101`）は `state="readonly"` を維持し、values は `catalog.provider_names() + plugin_extras` のみ。フォールバック候補は `_fallback_known_providers` のホワイトリスト検証を維持 | closed |
| T-02-14 | Information Disclosure | 実機確認（Task 3A/3B/3C）でのキー取り扱い | medium | mitigate | 3 つの checkpoint すべての `<what-built>` 冒頭にキー非記録を明記し `<acceptance_criteria>` にも「返信・SUMMARY に API キー文字列が含まれていない」を設定。02-04-SUMMARY.md の実機確認記録に API キー文字列は含まれていない | closed |
| T-02-15 | Repudiation | detail=low によるコスト削減とユーザー期待の乖離 | low | accept | R-02-03 参照。`detail` 既定を `high` に固定（`dialog.py:528-530`）し「読み取り精度優先」を既定とする。実コスト差の計測は v2 の Deferred 項目 | closed |
| T-02-16 | Tampering | 能力マトリクスの誤り（存在しないモデル / 誤った単価が既定値になる） | high | mitigate | `02-CAPABILITY-MATRIX.md` を Stage A（ID 実在）/ Stage B（能力・価格）へ分割し `evidence` 列で根拠種別を明示。`inferred` 行の既定採用を禁止し、単価は出典 URL と参照日を必須化。実機 Task 3B の単価突き合わせで差し戻しに値する不一致は報告されず | closed |
| T-02-17 | Spoofing | 送信先を解決できないクラウドプロバイダで送信先不明のまま同意を取る | high | mitigate | `_resolved_host_text`（`batch_ocr.py:132-152` および `ocr_dialog.py` の同型実装）が空ホストを検出したとき LANG キー `ocr_host_unknown`（`lang.py:539` ja / `:1325` en）を返す。テスト: `TestResolvedHostTextUnknown`（tests/test_provider_ui.py） | closed |
| T-02-18 | Tampering | 誤った単価による同意の質の毀損 | medium | mitigate | `OPENAI_PRICE_SOURCE`（url / retrieved / unit / currency）を `ocr_dialog.py:65` と `batch_ocr.py:98` の両方へ持たせる。テスト: `TestOpenAIPriceProvenance`（tests/test_provider_ui.py）の 4 層で形式妥当性・両ファイル一致・実世界不変条件を検証 | closed |
| T-02-19 | Tampering | 画像入力非対応モデルを選んだまま同意し課金だけ発生する | medium | mitigate | `VERIFIED_VISION_MODELS` 外のモデル選択時に確認ダイアログへ注記（`ocr_dialog.py:1322` / `batch_ocr.py:586`）。UI 側は `order_models_for_display` で確認済みモデルを先頭・既定に据え（`sections.py:638`）、`llm_openai_model_unverified_note`（`lang.py:701`）を常時表示（`sections.py:649`） | closed |
| T-02-20 | Tampering | 遅延到達したモデル一覧がユーザーの新しい選択を上書きする | low | mitigate | `_fetch_models_async` の直列化ガード（`model_fetch.py:142`）と、コールバックが `combo["values"]` にしか触れない設計（`model_fetch.py:293`）で構造的に防ぐ。テスト: `TestRefreshOpenaiModels`（tests/test_provider_ui.py）が `openai_model_var.set` の非呼び出しを固定 | closed |
| T-02-21 | Tampering | 許容値域外の `reasoning_effort` が API へ届き 400 になる | high | mitigate | 3 層防御。UI: readonly Combobox + `effort_values_for_model()`（`openai_provider.py:82-104`）由来の候補のみ。`_apply`: 許容集合外を空へ倒す。プロバイダ: `_apply_gen_params`（`:293`）が「is_reasoning_model かつ真値かつ許容集合内」の 3 条件を満たすときだけ payload へ入れる。手編集された設定ファイル由来の値もここで止まる。テスト: `TestOpenAIEffortValueGuard`（tests/test_ocr_providers.py） | closed |
| T-02-22 | Denial of Service（ユーザーへの） | ユーザー入力の無言破棄 | medium | mitigate | `_validate_openai_id` は `(ok, cleaned)` を返し、`_apply`（`dialog.py:547-565`）は `ok is False` で `messagebox.showerror` を出して中断する。入力欄の値は書き換えない。テスト: `TestOpenAiApplyAbortsOnInvalidId`（tests/test_provider_ui.py） | closed |
| T-02-SC | Tampering | npm/pip/cargo installs（供給網） | low | accept | R-02-04 参照。本フェーズは新規パッケージを一切インストールしていない（`urllib.request` 標準ライブラリのみ）。`git diff --stat requirements.txt pyproject.toml` が空であることを検証済み | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (`high`) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-02-01 | T-02-09 | PageFolio はローカル単一ユーザーのデスクトップアプリで監査ログ機構を持たない。クラウド送信への同意は「毎回確認ダイアログを出す（抑止オプションなし）」ことで担保する設計であり、同意ログの永続化は本フェーズのスコープ外。severity: low | 計画時決定（02-02-PLAN.md `<threat_model>`） | 2026-08-11 |
| R-02-02 | T-02-11 | モデル一覧取得は OCR とは別に API キーを OpenAI へ送るが、これは V190-OAI-03 が要求する機能そのもの。「モデル更新」ボタンの明示的な押下時のみ発火し、`GET /v1/models` は課金対象外でページ画像を含まない。ページ画像送信（T-02-03）とは別リスクとして受容する。severity: medium（block_on=high 未満） | 計画時決定（02-03-PLAN.md `<threat_model>`） | 2026-08-11 |
| R-02-03 | T-02-15 | `detail` の既定を `high` にすることで「読み取り精度優先」を既定とし、コスト削減はユーザーが明示的に `low` を選ぶ操作に委ねる。既定値の意味は `llm_openai_detail_hint` と `docs/CONFIGURATION.md` に明記するが、実際のコスト差の計測は行わない（実コスト計測は v2 の Deferred 項目）。severity: low | 計画時決定（02-04-PLAN.md `<threat_model>`・D-16） | 2026-08-11 |
| R-02-04 | T-02-SC | 本フェーズは新規パッケージを一切インストールしない（V190-OAI-11・`urllib.request` 標準ライブラリのみ）。02-RESEARCH.md「Package Legitimacy Audit」も該当なしと判定済みのため、供給網リスクは現状維持で受容する。severity: low | 計画時決定（4 PLAN 共通 `<threat_model>`） | 2026-08-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-11 | 23 | 23 | 0 | /gsd-secure-phase 02（オーケストレータ・ASVS L1 短絡） |

### Security Audit 2026-08-11

| Metric | Count |
|--------|-------|
| Threats found | 23 |
| Closed | 23 |
| Open | 0 |
| Open at or above `high`（ブロッキング） | 0 |

**検証方法:** 4 つの PLAN の `<threat_model>` を統合してレジスタを構築（重複 ID は最も厳しい severity / disposition を採用）。各 mitigate 脅威について、実装ファイル内の緩和コードと、計画で指名された自動テストクラスの実在を grep（ASVS L1 深度）で確認。accept 脅威は Accepted Risks Log へ転記。SUMMARY 側に `## Threat Flags` セクションは存在せず、追加の脅威フラグはなし。

**補足観察（脅威ではないが記録）:** 02-04 の実機確認（Task 3B）で `ocr_dialog.py` の `_apply_llm_settings` / `_on_run` の 2 分岐に `elif name == "openai":` が欠落し API キーが送信されない不具合が発見・修正された（`36e7cc2`）。これは可用性の不具合であり機密漏洩方向ではないが、「catalog 未到達の分岐が安全境界の網から漏れる」パターンとして今後の新プロバイダ追加時のチェック項目に該当する。

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-11
