---
phase: 03-ocr-a
plan: 03
subsystem: security-audit
tags: [security, api-key, caplog, source-scan, lang-parity, verification, docs]

# Dependency graph
requires:
  - phase: 03-ocr-a/02
    provides: lang.py 確定（{sec} 追加・ocr_err_truncated 新規・parity 291）を LANG parity テストの基準に
provides:
  - キー値ログ非出力 caplog 回帰（_save_settings + Claude/Gemini ocr_image・D-11）
  - pagefolio/ ソース実キースキャン回帰（sk-ant-/AIza 不在・D-12）
  - ja/en LANG parity + {sec}/{page} format スモーク回帰（Pitfall 3）
  - 実 API 検証チェックリスト（03-VERIFICATION-REALAPI.md・D-08）
  - 3 経路キー秘匿監査チェックリスト（03-AUDIT-KEY-SECRECY.md・D-10）
  - 開発履歴.md v1.7.0 項へ Phase 3（V16-QUAL-01〜04）追記
affects: [Phase 3 完了ゲート, キー秘匿監査, OCR 検証契約]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ログ秘匿は caplog.at_level でキー値が caplog.text に出ないことのみ assert（キー名は許容・Pitfall 4）"
    - "ソース秘匿は pathlib.rglob('pagefolio/**/*.py') × 実キー正規表現で CI 再発防止（tests/ 除外・Pitfall 5）"
    - "監査=検証フェーズは pagefolio/ ソース無改変・回帰テスト＋チェックリスト文書で証跡化"

key-files:
  created:
    - tests/test_source_keyguard.py
    - tests/test_lang_parity.py
    - .planning/phases/03-ocr-a/03-VERIFICATION-REALAPI.md
    - .planning/phases/03-ocr-a/03-AUDIT-KEY-SECRECY.md
  modified:
    - tests/test_settings_keyguard.py
    - tests/test_ocr_providers.py
    - 開発履歴.md

key-decisions:
  - "D-09: 堅牢化ロジック（clamp/バックオフ/CB/max_tokens クランプ）は既存テスト済み → 自動テストを重複追加せず実 API は手順書方式。"
  - "D-11: caplog はキー値非出力のみアサート、キー名出力は仕様として許容（Pitfall 4）。"
  - "D-12: ソーススキャンは pagefolio/ 限定で tests/ のダミーキーを誤検知しない（Pitfall 5）。"
  - "APP_VERSION は v1.7.0 を維持（Phase 3 は途中フェーズ・バンプは本マイルストーン完了時）。pagefolio/ 完全無改変。"

patterns-established:
  - "新規回帰テストファイルは test_*.py 命名・リポジトリ相対パス解決で CWD 非依存"
  - "GSD verify 文書は front-matter（phase/slug/status/created）+ 結果記入欄表で 02-VALIDATION.md に整合"

requirements-completed: [V16-QUAL-02, V16-QUAL-03]
---

# 03-03 SUMMARY — キー秘匿監査回帰テスト + 実 API 検証チェックリスト

## 概要

V16-QUAL-02（キー秘匿監査）と V16-QUAL-03（max_tokens/429 実機検証）を、回帰テスト＋検証/監査
文書の両立で達成。`pagefolio/` ソースは一切改変せず「監査＝検証＋ギャップ補完」に徹した（D-09/D-10）。

## Task 1: ログ平文露出 caplog 回帰（D-11）

- `tests/test_settings_keyguard.py` に `test_api_key_value_not_logged` を追加。`_save_settings` を
  `caplog.at_level(DEBUG)` 配下で機密キー入り settings に対して呼び、キー**値**が `caplog.text` に
  出ないことのみアサート（キー名出力は仕様として許容・Pitfall 4）。
- `tests/test_ocr_providers.py` に `TestProviderKeyNotLogged`（Claude/Gemini）を追加。urlopen を
  モックしつつ `ocr_image` を caplog 配下で呼び、渡したダミーキー値がログへ出ないことを担保。

## Task 2: ソース実キースキャン + LANG parity（D-12 + Pitfall 3）

- 新規 `tests/test_source_keyguard.py::test_no_real_api_keys_in_source`: `pagefolio/` の全 `.py` を
  `rglob` し `sk-ant-[A-Za-z0-9_-]{20,}` / `AIza[A-Za-z0-9_-]{30,}` 不在を assert。`tests/` 除外で
  ダミーキー誤検知を回避（Pitfall 5）。`Path(__file__).resolve().parent.parent` でリポジトリ相対解決。
- 新規 `tests/test_lang_parity.py::test_lang_keys_parity`: `set(LANG['ja'])==set(LANG['en'])`（291）。
  併せて待機/途切れ文言の `{sec}`/`{page}` format スモークで Pitfall 3（プレースホルダ不整合）を回帰防止。

## Task 3: 検証/監査文書 + フェーズ完了ゲート

- `.planning/phases/03-ocr-a/03-VERIFICATION-REALAPI.md`（D-08）: max_tokens クランプ・429 リトライ・
  A2 実値（stop_reason/finishReason）の実 API 確認手順と結果記入欄。キー未設定時はフェーズを
  ブロックしない旨と自動テストの相互参照を明記。
- `.planning/phases/03-ocr-a/03-AUDIT-KEY-SECRECY.md`（D-10）: 設定/ソース/ログ + 環境変数/セッション
  メモリの 4 区分で確認項目と対応自動テスト ID（`TestSaveSettingsKeyGuard` / `test_no_real_api_keys_in_source`
  / `TestProviderKeyNotLogged` 等）を相互参照。
- `開発履歴.md` の v1.7.0 項へ Phase 3（V16-QUAL-01〜04）を追記（新版番行なし）。`APP_VERSION` は
  v1.7.0 を維持し constants.py / README バッジ / 開発履歴.md の 3 箇所一致を確認のみ（無改変）。

## 検証結果

- caplog（settings + プロバイダ）`-k log` — 3 passed
- ソーススキャン + LANG parity — 3 passed
- 文書存在・版番同期スモーク — `docs+version held at v1.7.0`
- pagefolio/ 配下の変更なし（git status 確認・H2 監査=検証で実装無改変）
- 全テスト `pytest` — 582 passed / `ruff check . && ruff format .` — All checks passed

## Phase 3 全体の完了状況

- 03-01（V16-QUAL-01 回転即時反映）/ 03-02（V16-QUAL-04 OCR 途切れ・待機秒数）/ 03-03（V16-QUAL-02/03
  キー秘匿監査・実 API 検証）の 3 プラン全完了。要件 V16-QUAL-01〜04 を達成。
- 実 API 検証（03-VERIFICATION-REALAPI.md）はユーザー任意実行の手動項目として残置（D-07・キー未設定でも
  フェーズ完了をブロックしない）。
