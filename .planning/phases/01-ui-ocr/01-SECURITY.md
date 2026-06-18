---
phase: 01-ui-ocr
type: security
asvs_level: 1
block_on: high
threats_total: 5
threats_closed: 5
threats_open: 0
unregistered_flags: 0
verdict: SECURED
audited: 2026-06-18
---

# Phase 01 (01-ui-ocr) セキュリティ検証

## 概要

| 項目 | 値 |
|------|-----|
| フェーズ | 01 — ui-ocr（OCR パラメータ一元化 + サムネイルスライダー移設） |
| ASVS レベル | 1（ローカル Tkinter デスクトップアプリの UI リファクタ） |
| ブロック閾値 | high |
| 宣言済み脅威 | 5（T-01-01 〜 T-01-05） |
| CLOSED | 5 / 5 |
| OPEN（BLOCKER） | 0 |
| 未登録フラグ（WARNING） | 0 |
| 判定 | **SECURED** |

> このフェーズは完全にローカルな UI リファクタである。新規ネットワーク I/O・新規資格情報処理・新規外部アタックサーフェスを一切導入しない。クラウド OCR（Claude / Gemini）の base64 https 送信は前フェーズから不変。UAT で削除された OCR 画面のモデル取得（`list_models()` ネットワーク呼び出し）はアタックサーフェスを **減少** させた。

## 脅威検証結果

| 脅威 ID | カテゴリ | 処置 | 状態 | 根拠（ファイル:行） |
|---------|---------|------|------|--------------------|
| T-01-01 | Information Disclosure | mitigate | CLOSED | `pagefolio/ocr_dialog.py:861-873` — `_sync_param_vars_from_settings` は `.set()` のみで `logger`/`print`/`_save_settings` 呼び出しを一切含まない（値のログ出力なし） |
| T-01-02 | Tampering | mitigate | CLOSED | `pagefolio/settings.py:17-26, 79-98` — `_SENSITIVE_KEYS` ガード健在（書込前に機密キー除去）。`pagefolio/ocr_dialog.py:454-464` — `api_key_var` Entry に `state` 引数なし＝編集可能を維持 |
| T-01-03 | Information Disclosure | accept | CLOSED | 表示数値（scale/timeout 等）は非機密のローカル表示値。読み取り専用化は露出を増やさない（下記「受容リスク台帳」に記録） |
| T-01-04 | Tampering | accept | CLOSED | thumb_zoom は非機密の表示倍率。保存経路（`_on_thumb_zoom_release`→`_save_settings`）は不変、pack 構造変更のみ（下記台帳に記録） |
| T-01-05 | Information Disclosure | accept | CLOSED | バージョン番号・フェーズ変更の公開テキストのみ。機密情報を含まない（下記台帳に記録） |

## 検証詳細

### T-01-01（mitigate）— 数値同期パスで値をログ/永続化しない

- `pagefolio/ocr_dialog.py:861-873` `_sync_param_vars_from_settings`: 本体は `self.scale_var.set(...)` / `timeout_var.set(...)` / `max_tokens_var.set(...)` / `temperature_var.set(...)` の 4 行のみ。`logger` 呼び出し・`print`・`_save_settings` を含まない。docstring に「値はログに出力しない（情報露出回避・T-01-01）」と明記。
- `pagefolio/ocr_dialog.py` の全 `logger.*` 呼び出し（857/1245/1364/1585/1606 行）を確認 — いずれも例外メッセージ・ステータス更新失敗のみで、OCR パラメータ値や API キーを出力しない。857 行 `logger.error("provider 再生成に失敗しました: %s", e)` は例外オブジェクトのみ。
- 同期は `_apply_llm_settings`（780 行）の provider if/elif 分岐の **外**（796 行）で呼ばれ、全プロバイダ共通で実行される（PLAN の D-03 要件と一致）。

### T-01-02（mitigate）— `_SENSITIVE_KEYS` 非永続化ガード健在 / `api_key_var` 編集可能維持

- `pagefolio/settings.py:17-26` `_SENSITIVE_KEYS` 集合に claude/gemini/google/anthropic 各キー名（大小バリアント含む）が定義済み。
- `pagefolio/settings.py:79-98` `_save_settings`: 機密キー混入時はキー名のみ警告ログ（値は出さない）し、機密キーを除去したコピーを JSON へ書き込む。入力 dict を破壊的変更しない。本フェーズで非接触。
- `pagefolio/ocr_dialog.py:454-464` `api_key_entry` は素の `tk.Entry`（`show="*"`）で `state` 引数を持たない＝読み取り専用化の対象外で編集可能を維持（PLAN の D-06 要件と一致）。
- `pagefolio/ocr_dialog.py:780-791` `_apply_llm_settings`: docstring に「llm_settings に api_key 系キーは含まれず T-05-12 ガードは維持される」と明記。settings 更新（787）→ `_save_settings`（791）の経路でガードが最後の砦として機能。

### T-01-03 / T-01-04 / T-01-05（accept）— 受容リスク

3 件はいずれも非機密の表示値・公開テキストに関する露出リスク増分なしの受容判断であり、下記「受容リスク台帳」に記録した。

## 補足検証（UAT 修正のリグレッション確認）

- **読み取り専用化（display-only）**: `pagefolio/ocr_dialog.py` の `state=` 出現 6 箇所を確認 — 267（url_var readonly）/295（model_combo disabled）/336・359・382・412（4 数値 Spinbox disabled）。`api_key_var` Entry には付与されていない。いずれも表示専用化で挙動・データフローを変えない。
- **モデル取得ボタン削除**: `pagefolio/ocr_dialog.py` に `_fetch_models` / `list_models` の参照は **0 件**。OCR 画面からのネットワーク `list_models()` 呼び出しは撤去済み（アタックサーフェス減少）。モデル取得のネットワーク能力は `pagefolio/dialogs/llm_config.py`（編集面の一元化先）にのみ残存し、これは意図どおり。
- **`_dialog_w` 初期化順序（UAT 修正）**: `pagefolio/dialogs/llm_config.py:71-84` — `_dialog_w` を `_build()` より前に初期化し `_resize_to_fit()` の参照クラッシュを解消。ジオメトリ計算（ウィンドウ幅/高さ）のみで資格情報・ネットワーク・ファイル I/O に無関係。**セキュリティ影響なし**。

## 受容リスク台帳（Accepted Risks）

| 脅威 ID | 内容 | 受容理由 |
|---------|------|---------|
| T-01-03 | model_combo / 読み取り専用 Spinbox の数値表示 | OCR 解像度・タイムアウト等の非機密設定値。元々ローカル画面に表示されていた値で露出リスク増分なし。 |
| T-01-04 | thumb_zoom 設定の保存経路 | 非機密の表示倍率値。保存ロジック不変、pack 構造変更のみで改ざんリスク増分なし。 |
| T-01-05 | README / 開発履歴.md / constants のバージョンテキスト | バージョン番号とフェーズ変更内容の公開テキストのみ。API キー等の機密情報を含まない。 |

## 未登録フラグ（Unregistered Flags）

なし。両 SUMMARY.md（01-01 / 01-02）に `## Threat Flags` セクションは存在せず、実装中に新規アタックサーフェスは検出されていない。本フェーズはネットワーク I/O・資格情報処理・外部入力を新設していない。

## 判定

**SECURED** — 全 5 脅威が CLOSED（mitigate 2 件をコードで検証、accept 3 件を台帳に記録）。high 重大度の OPEN 脅威 0 件。`threats_open: 0`。ブロック閾値 high に対しブロッカーなし。出荷可。
