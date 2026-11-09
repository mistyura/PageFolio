# Phase 04 品質停止解除後の検証前ゲート追補（2026-10-28）

## 結論と所有範囲

`$gsd-execute-phase 06` の依存元鮮度契約に従う Phase 04 の検証前ゲートをインラインで評価した。Nyquist自動範囲とSecurityはpass、UIはpartial、コードレビューは既知Warning 1のまま。独立verifierへの引渡しを妨げる新規ゲート不合格は検出しなかった。最終 `04-VERIFICATION.md` の生成・fingerprint・Phase完了判定は次の独立verifier/親担当で行う。

製品、tests、AGENTS.md、pyproject.toml、版、過去失敗原本、STATE/ROADMAP/requirementsは編集していない。新規build、GUI起動、UAT、pytest、コミット、phase.completeを実行していない。既存dirtyは保全した。

## 実行順と評価

所有手順は `C:/Users/shdwf/.codex/gsd-core/workflows/execute-phase/steps/verify-phase-goal.md`。関連skillとvalidate-phase/secure-phase/ui-review/code-review、code-review-disposition/regression-gateの手順を参照した。hookは今回 `loop render-hooks verify:post --raw` / `execute:post --raw` で取得した。

| 順番 | ゲート | 今回の評価 | 根拠・継続条件 |
|---|---|---|---|
| 1 | Nyquist、onError halt | pass | State A、6 PLAN/6 SUMMARY・13タスク・5要件。既存Per-Task Verification Mapへ照合、自動MISSING/PARTIAL 0。最新2071件と追加監査24件を同入力で再利用。人手Wは別途not-run。 |
| 2 | Security、onError halt | pass | ASVS L1/block_on high。計画時22脅威はclosed22/open0。製品bytes不変、追加面は試験監査。API wrapperと証拠不足時の失敗閉鎖を読解し、新未緩和highなし。 |
| 3 | UI、onError skip | partial | UI-SPECなし、抽象6柱。製品表示不変、Experience Designの新監査配線を静的確認。実capture/クリック/DPI/権限差/session/EXEはnot-run。score nullを維持。 |
| 4 | Code Review、onError skip | issues_found | standard、既存17対象＋監査helper/故障注入試験2件の19対象。既存不変部分は前回レビュー再利用、Windows試験差分と新2件を読解。Critical0/Warning1/Info0、新指摘0。 |
| 5 | Review disposition、advisory | open0/total2 | 履歴CR-01 fixedを維持、WR-01 deferredを維持。15609msと15140msは打消さず、Phase06 W07bで契約再評価。 |
| 6 | Gap-closure / TDD | 対象外 | Phase04は整数の既存機能phase。gap-closure対象外。workflow.tdd_mode=false、execute:postにTDD hookなし。 |
| 7 | Regression | 対象なし | ROADMAPの現行v1.10.0はPhases4–6。Phase04が最初。現行phasesのVERIFICATIONは04/05だけで05は後続。過去milestoneの同番号や後続05をpriorへ取り込まない。 |

`verification.append-audit` を報告更新後に所有CLIで実行した。VALIDATIONは同じ0/0/0のため `appended:false`、SECURITYは22/22/0の監査表を追加して `appended:true`。両方exit0。最初のPowerShell経由はJSON引数分割で拒否され、ファイル変更なし。Nodeの引数配列で同じ所有verbを実行して解消した（製品/試験の失敗再走ではない）。

## 最新成功証拠の同一性と再利用

実測正本は `.planning/debug/quality-gate-unblock.md`（resolved）と `.planning/debug/quality-gate-unblock-20261028/`。以下の成功を再実行せず採用した。

| 証拠 | 実結果 | 現行との対応 |
|---|---|---|
| `full.json` / `full.xml` / `full-0.stdout.txt` | 単一全件2071 passed / 2 warnings / 480.86秒、exit0、failures/errors/skipped各0、実行前後changed=[] | 146入力の142一致、Python137/137一致。追加監査24件と関連293件をXML内で確認。 |
| `connection.json` / `connection.xml` | 実OS監査接続1 passed / 1 warning / 0.45秒 | 監査API記録と実window eventの接続を含む。同じPython137/137。 |
| `nine.json` / `nine.xml` | owner＋8 peer 1 passed / 1 warning / 2.67秒 | identity/集約/snapshot/寿命/期限/foregroundの判定が通った試験。同じPython137/137。 |
| `native-final.json` と4stdout | 全体Ruff check/format/format --check、ASTがすべてexit0、137 files unchanged/already formatted、stderr空 | 146入力中143一致。Python137/137、Ruff設定一致。差分は文書3件。 |
| `documents.json` / stdout | 全件後のDoD/リリース契約47 passed / 1 warning / 9.51秒 | 当時の文書同期後の成功としてのみ参照。現行文書3件とGit除外のhashは異なるため、変更後全文章が検証済みとは主張しない。今回のPhase04報告変更は本文追記とreview対象数のみで、DoDが読むvalidated frontmatter/既存タスク対応は不変。 |

full実行後の相違は `.gitignore`、`docs/DEVELOPMENT.md`、`CONTRIBUTING.md`、`開発履歴.md` の4件。除外は今回pytestの選択条件を変更しておらず、実際の全件argvには試験除外なし。現行Python、製品/tests、AGENTS、pyproject、requirements、Ruff設定は成功実行時と同一。これら4件の新旧SHA256は同名JSONの `snapshots.full.current_comparison.differences` と `04-GATES-CURRENT-FINAL-20261028.json` の `current_full_comparison` に個別記録した。`.planning/` 文書はこの146入力manifestの対象外なので、今回更新した5報告の前後hashを別途保持した。

旧2047件証拠の118入力と現行は113/118一致、旧manifest内Python111件ではWindows試験1件だけが差分。残り4件はROADMAP/STATE/VALIDATION/開発履歴。新helper2件は旧manifest対象外だが最新146入力には含まれる。旧2047件を最新の現行成功と取り違えず、現在の判定は2071件の正本に結合した。

Python実行ファイルSHA256は `f14d10e954b922d758234ff49335ad0e07e567103e06b38ff675c6bc85282865` で記録時と一致。読取実行でPython3.15.2、Windows11 build26300、pytest9.1.1、Ruff0.17.1、PyMuPDF1.28.2、Pillow13.0.0、tkinterdnd2 0.6.4を照合した。環境を変更していない。過去runのデスクトップ全状態が同一と証明するものではない。

全件の2警告は既知PyMuPDF ByteString廃止予告とJUnit xunit2/record_propertyの非互換通知。製品異常やTcl leakの合格への読み替えではない。試験を追加反復していない。

## 変更された試験の監査

`tests/test_startup_windows.py` の変更全体と `tests/startup_foreground_audit.py` / `tests/test_startup_foreground_audit.py` を確認した。backend構築前のcontext内 `_bind` 監査、引数・戻り値・例外・last-errorの保持、元bind復元、子fixture内への記録、PID/生成時刻/roleとWinEventの結合を確認した。製品のidentity/ACL/期限/取消し/通知境界は旧入力と同一で、前回Securityの緩和策を再利用できる。

判定はNOACTIVATE欠落、OSに拒否された禁止API要求、元HWNDへ戻った後でも途中の通知前景化をviolationにする。要求元未確定の外部切替はunexplained_transition、9process/時刻/開始終了/API復帰/解除/identityの採取不足はaudit_errorとして不合格にする。判定の自己循環や未知切替の成功扱いは見つからなかった。窓名や利用者入力内容は保存せず、試験自体は前景を強制しない。

製品側新endpoint/auth/schema変更なし。新規Critical/Warningや未緩和highは検出していない。対象差分および今回5報告のCRLF対応 `git diff --check` はexit0。

## 証拠SHA256と保全

| ファイル（debug証拠は上記quality-gate-unblock-20261028配下） | SHA256 |
|---|---|
| `full.json` | `7849ddb583b1cbf44dd80db6c18027332248e016a8a635ca1cfd4f52bbf047db` |
| `full.xml` | `8a35848f605a68b2e8014b2b51782c288ce55b40805a212b69c953b563b2a527` |
| `full-0.stdout.txt` | `c34b2e154a1361032f0aa6f67f10a3e00ff5915654a58466d4e0c5b78a3ae885` |
| `native-final.json` | `7049109c802f8de1eae58ca56d0962fcd0ac9a76fc107b38944dd5c00aa8745b` |
| `connection.json` | `bb2fba87a35b2e7e5c3f5219acb69bb343837704a4e0488de294627b44870c58` |
| `nine.json` | `563c595b2dd9737e7b6310f02bef1637f1fcc1d3c63b002b753f47e14a6f63b7` |
| `documents.json` | `41a36c33ee7571a543ccf214851e67c297b7f123fa2973fe5d8539ba0a6de0e3` |
| `04-GATES-CURRENT-20261028.json` | `69cb4791e3001f2f0a1f4aa5cf58ae7677316ab773db41df9f09a2fa3da6846d` |
| `04-GATES-CURRENT-FINAL-20261028.json` | `00ce5348082dad52ed38dc93994f97021ac2a3e8e66440cf74d2ee3714c79cc5` |

最初の今回JSONに証拠17件のhash、12 PLAN/SUMMARYのhash/タスク/verify/要件/脅威、関連JUnit testcase、ゲート報告更新前hashを保存した。FINAL JSONで証拠17件不変、環境一致、Python137一致、5報告更新後hash、`04-VERIFICATION.md` 不変を確認した。今回収集用 `04-GATES-CURRENT-20261028.cjs` は製品を変更せず、再実行時は今回証拠の上書きを拒否する。

## 未解決と引渡し

- 人手W・実EXE・DPI/実入力/別権限/sessionの未実施は承認済みPhase06移管のnot-runを維持。UI partialをpassへ上げない。
- DEP-05、owner_missing、元の前景切替要求元、WR-01、未分類edge・未確認の禁止事項は解除しない。最新runの成功は過去原因の確定ではない。
- 過去04-reverifyの失敗、元47失敗証拠、品質解除中の失敗ログ、2047件の旧成功は変更していない。
- 次は独立verifierが最新ゲート報告と製品/試験を対象に正式VERIFICATIONを生成し、所有CLIでfingerprintを計算する。本追補はその最終判定を代替しない。
