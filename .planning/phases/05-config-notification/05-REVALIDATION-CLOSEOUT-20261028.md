# Phase 05 再検証の完了記録（2026-10-28）

`$gsd-execute-phase 05` により、4/4計画の既存SUMMARYを保持し、対象6ファイル変更によるstaleを検証ゲートから再開した。実装タスクの再実行はない。

| ゲート | 結果 |
|---|---|
| Nyquist | 4要件/9タスクの自動検証対応、追加gap 0。05-VALIDATION.md |
| Security | 計画時登録14件closed/open 0、ASVS L1で対策再照合。05-SECURITY.md |
| UI | 利用者が既存レビュー再利用を選択。静的22/24、追加GUIなし。05-UI-REVIEW.md |
| コードレビュー | critical 1/open 1（CR-03）。既存CR-01/CR-02/WR-01のfixedを保持 |
| 先行Phase回帰 | 同一入力の既存単一全件証拠を再利用。先行Phase参照の7試験ファイル/286件はJUnit内でfailure/error/skip 0 |
| 独立検証 | 23/23 passed、4要件達成、artifact16/16・key link9/9。CLI fingerprint v4とverification statusで確認 |
| 文書更新後 | `tests/test_gsd_dod.py tests/test_release_contract.py` を新規実行し47 passed / 1 warning / 11.51秒 / exit 0 |

既存全件は `.planning/debug/quality-gate-unblock-20261028/full.json`、`full.xml`、`full-0.stdout.txt`、`environment.json` の2071 passed / 2 warnings / 480.86秒 / exit 0。今回、製品・試験・依存定義・環境の一致を照合して再利用した。全件を新規実行したという意味ではない。文書テストの原本は `05-closeout-20261028.txt` と `05-closeout-20261028.xml`。コマンドはプロジェクト`.venv`のPythonで `-m pytest -q -x -p no:cacheprovider tests/test_gsd_dod.py tests/test_release_contract.py --basetemp=.planning/phases/05-config-notification/05-closeout-20261028-tmp --junitxml=.planning/phases/05-config-notification/05-closeout-20261028.xml`。`git diff --check`も成功した。

## 完了範囲と残る制約

新規CR-03はOCRをoffにした後も旧providerが残り、サマリを旧ローカル接続先へ送信できる経路。実通信は行っていない。独立検証は、Phase 05の設定I/O失敗通知・原本保護の契約とは別の欠陥と判定した。Phase完了を維持する一方、CR-03は重大・openとして製品修正・回帰・再レビューを要し、出荷停止を継続する。

H01〜H14と意味評価2件の人手passは既存履歴を保持。DEP-05、owner_missing、通知前景不一致等の原因未解決、未分類edge4件と証拠限界を解除しない。Phase 06のW05b自動復帰未実証・全110受入not-run・06-05/06停止を維持する。

ROADMAP・REQUIREMENTS・state.jsonは既にPhase 05をCompleteと記録しており、検証再生成後のroadmap.analyzeでdisk_status=complete、checkbox_conflict=[]になった。完了処理を再適用してPhase 06の実行中位置を「未着手」へ戻すことを避け、共有STATE/ROADMAP/PROJECTには今回の再検証とCR-03だけを追記した。Phase 06の既存限定debug再開点は変更していない。新規製品・試験・版番号の変更はない。
