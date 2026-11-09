---
status: resolved
trigger: "出荷停止状態を解消して"
created: 2026-10-28
updated: 2026-10-28
---

## Scope

`gsd-debug` の init.debug / 現行進捗を照合して開始。利用者の出荷停止解消指示に基づき、CR-03 の修正・回帰検証を先に行う。既存 dirty・失敗原本・UAT 判定は保持する。親が直接実施する。出荷公開は受入完了とは別であり、未実施を合格にしない。

## Symptoms

expected: OCR を off に切り替えた後はサマリ生成が無効になり、旧接続先に本文を送らない。
actual: 旧 provider を保持し、サマリボタンと実行入口が off を検査しない。旧クラウド名も表示される。
errors: Phase 05 05-REVIEW.md の CR-03（BLOCKER）。例外の有無ではなく意図しない送信可能性。
reproduction: OCR 結果があるダイアログで LLM 設定を off に変更後、サマリを実行。
started: 2026-10-28 のレビューで検出。導入時期は未確定。

## Current Focus

hypothesis: provider を保持する off 分岐に対して、UI と実行入口が能力だけを参照している。
test: ローカル/クラウド provider の実設定適用からボタン、表示、直接呼出し拒否、再有効化を検証する。
expecting: 修正前に off の UI/入口の回帰が失敗し、修正後に本文や既存結果を変更せず送信を拒否する。
next_action: CR-03 の修正を完了。W05b の追加観測と現行ソースのビルド・依存検証鮮度・実機受入へ進む。

## Evidence

- `pagefolio/ocr_dialog.py` の `_apply_llm_settings` は off で旧 provider を保持。`_update_summary_btn_state` と `_on_summary` に off ガードなし。`_provider_display_name` は Claude/Gemini の型判定を設定より優先する。
- 進捗の現行照合は 14/16 SUMMARY、Phase 06 は 4/6。CR-03 と W05b、全110行の実機受入が残る。

## Resolution

root_cause: off 設定でも旧 provider を保持する仕様に対し、サマリの UI/入口が provider の能力だけで実行を許可していた。表示もクラウドの型判定を優先していた。
fix: ボタンと実行入口の off ガード、明示的な候補設定 off の拒否、無効時の旧 provider/model 表示の除去。既存本文とサマリは保持。v1.10.2 に同期。
verification: 修正前9 failed/3 passed（期待した回帰失敗）、修正後関連48 passed、OCR全体213 passed。最終単一native全件2083 passed/2 warnings/463.98s/exit0、入力hash変更0。全体Ruff check --no-cache、format . --no-cache（137 unchanged）、AST、対象diff --check成功。キャッシュ利用時のアクセス拒否は保持し、キャッシュなしで全体を検査。skip/除外/期限変更なし。

## 再レビュー（親エージェントによる限定レビュー）

- 実設定適用は `_active_ocr_settings` を破棄し、off でも結果を保持する。UI は現在の永続設定 off を拒否する。
- `_on_summary` はアプリ設定 off と明示候補 off の両方を、本文構築・キー確認・状態変更・worker起動より前で拒否する。クラウド型による安全側の判定は維持した。
- 再有効化とフォールバック既存回帰も成功。今回の CR-03 に追加指摘なし。独立エージェントによる再レビューではない。
- 原本レビューと対応表は `ocr-off-summary-evidence/05-REVIEW-before.md` / `05-REVIEW-DISPOSITION-before.md` に保全。
- 全件の生ログ・JUnit・環境・入力hashは `ocr-off-summary-evidence/native-20261028/`。既存の2071件証拠は変更していない。
- GUI人手確認・新EXE・全110行受入・出荷承認は未完了。本修正の成功でこれらをpassにしない。既存dirty/indexを保持、commit/pushなし。
