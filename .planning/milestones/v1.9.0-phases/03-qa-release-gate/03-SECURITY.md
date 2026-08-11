---
phase: 3
slug: qa-release-gate
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-11
---

# Phase 3 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

フェーズ 3「qa-release-gate」の 4 プラン（03-01〜03-04）の PLAN.md `<threat_model>` ブロックから
脅威レジスタを統合し、実装への緩和策の存在を検証した記録。

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| ユーザー操作（上書き確認 / 保存先ピッカー）→ ファイルシステム書き込み | ユーザーの同意が「どのパスへ書くか」を決める唯一のゲート。再試行はこのゲートを迂回するため、確定パスの束縛が信頼境界そのものになる | 保存先パス・PDF バイト列 |
| アプリ内部状態（`self.doc` / `self.filepath`）→ 実保存層 | トーストは非モーダルで、表示中にファイルを閉じる・別ファイルを開く操作が可能。実保存層は自身が受け取った引数のみを信頼する | Document ハンドル・暗号化設定 |
| テスト実行環境（pytest プロセス / Tcl-Tk ネイティブ層）→ リリース判定 | 「全テスト完走」という主張が出荷可否を決める。ここで観測を歪めると、壊れたビルドがゲートを通る | テスト結果件数・合否 |
| 調査時の一時的な回避策（`--basetemp` / 除外フラグ）→ 恒久的な運用手順 | 実験中の便宜が、そのまま CLAUDE.md の日常手順へ昇格してしまう経路 | 運用手順文書 |
| 開発環境の Tcl/Tk 探索 → PyInstaller 配布 EXE の Tcl/Tk 探索 | conftest.py での環境変数上書きは開発環境だけでなく凍結ビルドの探索ロジックへ波及しうる | 環境変数（`TCL_LIBRARY` / `TK_LIBRARY`） |
| 実 API 実行（Gemini / LM Studio）→ UAT 記録・SUMMARY・git 履歴 | API キー・OCR 対象 PDF の内容・ユーザー名を含むパスが記録へ流れ込みうる経路 | API キー・OCR 本文・ローカルパス |
| 実機確認のユーザー返信 → `03-UAT-RESULTS.md` の記録 | 人の観測が唯一のソース。転記の段階で結果を丸めると、記録がリリース判定を誤らせる | UAT 実施結果 |
| `APP_VERSION`（単一情報源）→ README バッジ / 開発履歴.md / 配布物 | 版数が食い違うと、ユーザーが実際に使っているビルドと documentation が対応しなくなり、不具合報告の切り分けが不能になる | バージョン文字列 |
| 過去マイルストーンの履歴記述 → 今回の追記 | 追記操作が既存エントリを壊すと、史実が失われる | 開発履歴エントリ |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01-01 | Tampering | `pagefolio/file_ops.py` `_do_save_as` / `_do_save_compressed` | high | mitigate | 実保存層が `encryption=fitz.PDF_ENCRYPT_KEEP` を保持して受け渡し（`file_ops.py:1118` `setdefault`・`:1153`・`:1207`・`:1322`）。`tests/test_password.py` 23 件 green（本監査で実行確認） | closed |
| T-03-01-02 | Tampering | `retry_cb` に束縛された確定パス | high | mitigate | `functools.partial` でパスと `bound_doc` を束縛（`file_ops.py:1168` / `:1220` / `:1293`）。実保存層 `_do_save_file` / `_do_save_as` / `_do_save_compressed` は `bound_doc` と `self.doc` の同一性を検証し、不一致・None なら書き込みせず dismiss（CR-01 / WR-02 修正、`3562b09` / `7251698`） | closed |
| T-03-01-03 | Elevation of Privilege | 上書き確認のスキップ範囲 | medium | mitigate | 公開エントリ `_save_file`（`:1171` 確認ダイアログ）・`_save_as`（`:1227` ピッカー）・`_save_compressed`（`:1312` ピッカー）は確認・パス選択層を保持。スキップは `retry_cb` 経由のみ。回帰テストで初回の確認表示を固定（`5817e7b`） | closed |
| T-03-01-04 | Denial of Service | 再試行の無限ループ | low | accept | 自動再試行ループ未実装。再試行はユーザーのボタン押下ごとに 1 回のみ（AR-03-01） | closed |
| T-03-01-SC | Tampering | npm/pip/cargo installs | low | accept | 新規パッケージ導入ゼロ（`functools` は標準ライブラリ）。`git diff main -- requirements.txt pyproject.toml` 空を確認（AR-03-02） | closed |
| T-03-02-01 | Repudiation | リリースゲートの合格記録（`CLAUDE.md` / `03-TEST-ENV-INVESTIGATION.md`） | high | mitigate | CLAUDE.md「リリースゲート」節に実行コマンド全文・実測 1398 件・非再現の連続実行回数（10回＋リサーチ7回＝累計17回）・除外禁止事項を明記し、根拠を `03-TEST-ENV-INVESTIGATION.md` へリンク | closed |
| T-03-02-02 | Tampering | `tests/conftest.py` へ入れる修復コード | high | mitigate | 切り分けの結果非再現につきコード変更ゼロ。`git diff main -- tests/conftest.py` 空。リポジトリ配下の `.py` に `TCL_LIBRARY` / `TK_LIBRARY` の記述なし（検出はいずれも `.venv/` 配下の PyInstaller 同梱物のみ） | closed |
| T-03-02-03 | Tampering | `pagefolio/` 製品コード | high | mitigate | Plan 2 のコミット群（`3182490` 以前の 03-02 系）は製品コード無改造。Plan 2 スコープでの `pagefolio/` 差分ゼロを受け入れ基準で検証済み（`03-02-SUMMARY.md`） | closed |
| T-03-02-04 | Denial of Service | pytest 一時ディレクトリ（`%TEMP%\pytest-of-shdwf`）のロック競合 | low | accept | `--basetemp` 指定での運用回避。根本対応は CONTEXT.md の Deferred Ideas で明示的に範囲外（AR-03-03） | closed |
| T-03-02-05 | Tampering | 依存パッケージ構成（`requirements.txt` / `pyproject.toml`） | medium | mitigate | `pytest-forked` / `pytest-xdist` 等の導入なし。両ファイルの `git diff main` 差分ゼロを確認 | closed |
| T-03-02-SC | Tampering | npm/pip/cargo installs | low | accept | 新規パッケージ導入ゼロ（AR-03-02 と同根拠） | closed |
| T-03-03-01 | Information Disclosure | `03-UAT-RESULTS.md` / checkpoint 返信 / SUMMARY | high | mitigate | `03-UAT-RESULTS.md` 内の `C:\Users\` 出現 0 件を本監査で再確認。API キー様パターン（`AIza…` / `sk-…` / `api_key: "…"`）の検出 0 件。OCR 結果は要旨のみ記録 | closed |
| T-03-03-02 | Repudiation | UAT 結果の記録 | high | mitigate | `## 実施結果` 表が `実施日` / `結果` / `根拠` を必須列として持ち、`結果` は pass / fail / 未実施 の 3 値。`## サマリ` 内訳合計と対象確定表の行数一致を検算済み（`0e00ee8`・実施 13 pass / 未実施 2） | closed |
| T-03-03-03 | Tampering | 遡及項目の文言 | medium | mitigate | 過去 UAT の `expected` 原文を読み取ったうえで書き換えず検証。意味を失った項目は書き換えず「除外」＋理由で処理（`8d225e5` 対象確定） | closed |
| T-03-03-04 | Spoofing | 実 API 実行時の送信先 | low | accept | 送信先は Phase 2 以前で完成した既存プロバイダ実装が決定。本フェーズで新規送信先の追加なし（AR-03-04） | closed |
| T-03-03-SC | Tampering | npm/pip/cargo installs | low | accept | 新規パッケージ導入ゼロ（AR-03-02 と同根拠） | closed |
| T-03-04-01 | Tampering | `APP_VERSION` と README バッジ / 開発履歴.md の版数不一致 | medium | mitigate | `pagefolio/constants.py:12` `APP_VERSION = "v1.9.0"`・README バッジ `version-v1.9.0`・開発履歴.md 最終更新/索引表 v1.9.0 の 3 者一致を本監査で再確認 | closed |
| T-03-04-02 | Tampering | 開発履歴.md の既存エントリ | medium | mitigate | `Edit` による範囲限定の追記のみ（`c4fe579`）。`Write` 不使用。差分は冒頭ブロック引用とバージョン索引表の 2 箇所に限定 | closed |
| T-03-04-03 | Repudiation | v1.9.0 エントリに書くテスト件数・要件件数 | medium | mitigate | 件数は当マイルストーンの実測のみを出典（テスト 1398 件・要件 27/27）。過去の値（1109 / 1387）の書き写しなし | closed |
| T-03-04-04 | Tampering | ビルド設定（`pyproject.toml`） | low | mitigate | CLAUDE.md 禁止事項どおり未編集。`git diff main -- pyproject.toml` 差分ゼロ | closed |
| T-03-04-SC | Tampering | npm/pip/cargo installs | low | accept | 新規パッケージ導入ゼロ（AR-03-02 と同根拠） | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-01-04 | 再試行はユーザーのボタン押下ごとに 1 回だけ実行され、自動再試行ループを実装しない。失敗し続けても同じトーストが更新されるだけでリソース枯渇に至らない | PLAN 03-01 threat model | 2026-08-11 |
| AR-03-02 | T-03-01-SC / T-03-02-SC / T-03-03-SC / T-03-04-SC | 本フェーズは新規パッケージのインストールを一切行わない（V14-D-01 の新規 pip 依存ゼロ方針）。`03-RESEARCH.md` の Package Legitimacy Audit も「該当なし」と結論 | PLAN 03-01〜03-04 threat model | 2026-08-11 |
| AR-03-03 | T-03-02-04 | `%TEMP%\pytest-of-shdwf` のロック競合は `--basetemp` 指定での運用回避で通す。根本対応は 03-CONTEXT.md の Deferred Ideas で明示的に範囲外 | PLAN 03-02 threat model | 2026-08-11 |
| AR-03-04 | T-03-03-04 | 実 API の送信先は Phase 2 以前で完成した既存プロバイダ実装が決定しており、本フェーズは無改造。Gemini / LM Studio ともに Phase 2 までのコスト確認ゲートを通る | PLAN 03-03 threat model | 2026-08-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-11 | 21 | 21 | 0 | /gsd-secure-phase (ASVS L1, block_on: high) |

### Security Audit 2026-08-11

| Metric | Count |
|--------|-------|
| Threats found | 21 |
| Closed | 21 |
| Open | 0 |

**監査深度:** ASVS L1（grep 深度）。レジスタは 4 プランすべての PLAN.md `<threat_model>` に
由来する（`register_authored_at_plan_time: true`）ため、新規脅威のスキャンは行わず既知脅威の
緩和策の実在を検証した。`threats_open: 0` かつ L1 のため短絡ルールにより auditor サブエージェント
の起動は不要と判定。

**本監査で実行した実証:**

- `pytest tests/test_password.py -q` → 23 passed（T-03-01-01 の暗号化維持）
- `git diff main --stat -- requirements.txt pyproject.toml tests/conftest.py` → 差分なし（T-03-02-02 / T-03-02-05 / T-03-04-04）
- リポジトリ `.py` の `TCL_LIBRARY` / `TK_LIBRARY` grep → ヒットは `.venv/` 配下のみ（T-03-02-02）
- `03-UAT-RESULTS.md` の `C:\Users\` grep → 0 件、API キー様パターン → 0 件（T-03-03-01）
- `APP_VERSION` / README バッジ / 開発履歴.md の 3 点一致 grep（T-03-04-01）

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-11
