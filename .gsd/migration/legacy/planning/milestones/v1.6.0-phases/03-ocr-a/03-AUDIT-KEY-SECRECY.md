---
phase: 03
slug: ocr-a
status: draft
created: 2026-06-19
---

# Phase 3 — API キー秘匿監査チェックリスト（V16-QUAL-02 / H2・D-10）

> API キーが「設定ファイル / ソースコード / ログ」の 3 経路に平文露出しないことを再確認する監査文書。
> 各経路は対応する自動回帰テストへ相互参照し、将来の退行を CI で構造的に検出する。
> 本フェーズは `pagefolio/` ソースを一切改変しない（H2 は監査＝検証）。

---

## 経路 1: 設定ファイル（pagefolio_settings.json）

| 確認項目 | 内容 | 自動テスト | 結果 |
|----------|------|------------|------|
| `_SENSITIVE_KEYS` ガード | 機密キーを `_save_settings` が JSON へ書き込まない（除外コピーを保存・入力 dict 非破壊） | `tests/test_settings_keyguard.py::TestSaveSettingsKeyGuard` | ☐ pass |
| 機密キー集合の網羅 | `claude_api_key`/`anthropic_api_key`/`gemini_api_key`/`google_api_key`/`api_key` + 大文字バリアントを含む | `tests/test_settings_keyguard.py::TestSensitiveKeysConstant` | ☐ pass |

`_SENSITIVE_KEYS` の定義: `pagefolio/settings.py`（機密キー集合・WR-03 で dual env var 大文字バリアントも追加済）。

---

## 経路 2: ソースコード（誤コミット防止）

| 確認項目 | 内容 | 自動テスト | 結果 |
|----------|------|------------|------|
| 実キーパターン不在 | `pagefolio/` の全 `.py` に `sk-ant-…` / `AIza…` 実キー形式が存在しない | `tests/test_source_keyguard.py::test_no_real_api_keys_in_source` | ☐ pass |
| 誤検知回避 | スキャンは `pagefolio/` 限定（`tests/` のダミーキーを誤検知しない・Pitfall 5） | 同上（`rglob` スコープ） | ☐ pass |

---

## 経路 3: ログ出力（平文露出防止）

| 確認項目 | 内容 | 自動テスト | 結果 |
|----------|------|------------|------|
| 設定保存時のキー値非出力 | `_save_settings` はキー**名**のみ `logger.error`、キー**値**は出さない（Pitfall 4） | `tests/test_settings_keyguard.py::TestSaveSettingsKeyGuard::test_api_key_value_not_logged` | ☐ pass |
| プロバイダのキー値非出力 | Claude/Gemini `ocr_image` が API キー値をログへ出さない | `tests/test_ocr_providers.py::TestProviderKeyNotLogged` | ☐ pass |

---

## 経路 4（補強）: 環境変数 / セッションメモリ限定

| 確認項目 | 内容 | 確認方法 | 結果 |
|----------|------|----------|------|
| キー取得は読み取り専用 | `_resolve_api_key` は `os.environ.get` のみ（書き込み禁止・D-05） | `pagefolio/ocr.py` `_resolve_api_key` の目視 + 既存テスト | ☐ pass |
| セッションキー非永続化 | セッション入力キーは `app._session_api_keys` のみに保持し settings へ流入しない | `pagefolio/ocr_dialog.py` セッションキー経路 + `_SENSITIVE_KEYS` ガード | ☐ pass |

---

## 監査結果

| 項目 | 記入 |
|------|------|
| 監査実施日 | |
| 実施者 | |
| 自動テスト全緑 | ☐ `pytest tests/test_settings_keyguard.py tests/test_source_keyguard.py tests/test_ocr_providers.py -q` |
| 総合判定 | ☐ 3 経路すべて秘匿担保 / ☐ 要対応 |
