---
phase: 06-release-validation
plan: "05"
status: implemented_pending_gates
implementation_status: implemented_native_integration_pending
ready_for_retry: false
created: 2026-11-05
---

# W05c 候補停止後の採取手順見直し

120秒の存命期間内に機械証拠を確定するv3採取runnerと受入契約を実装した。対象79件と最終全件2333件が成功したが、新規v3 Windows統合・全体format・再開ゲートは未成立。利用者は既存pytestの自動GUI試験のみ許可した。新規統合/正式試行/正常診断反復/期限延長/製品変更/commitは実施していない。元runのNo不成立原因は未特定であり、この文書を解決報告や追加試行の許可として使わない。

## 2026-11-05 実装と最終検証

- `tests/w05c_runner.py` に単発採取を追加。起動前plan/hash、実watchdog期限、観察区間、No後peer、回収前snapshot、同owner回収、回答待ちの原本固定を実装した。予算の実測根拠は次のWindows統合で必要であり、定数があるだけでは開始条件を満たさない。
- `tests/w05c_evidence.py` / `tests/test_startup_windows.py` へ新schemaを接続。既存v2の回答時刻条件を維持し、v3ではNo後peerを別名で扱う。
- `06-05-w05c-v3.cjs` / `06-05-w05c-evidence.cjs` / `06-05-record-w05c-python.cjs` で機械採取と回答採用を分離。早着/後着とも実取得時刻を保持し、原文・意味承認・封印identity/hashを照合して採用する。旧候補の事後pass化はしない。
- `tests/test_w05c_runner.py` に正負対照を追加、`06-07-quality.cjs` に新入力を登録。最終対象79件成功（`debug/phase06-w05c-no-marker/v3-target-final.xml`）。最終全件は `06-05-evidence/w05c-v3-final-native-20261105/` で2333 passed / 2 warnings / 1274.11秒、exit0、170一意入力前後変更0。初回2329成功は最終修正前の履歴として保存する。
- 全146 Pythonの明示Ruff/formatとASTは成功。全体 `ruff check .` はexit0だがアクセス拒否警告あり。全体 `ruff format . --check` は既存 `05-config-notification/05-closeout-20261028-tmp` へのアクセス拒否でexit1。全体走査の完全成功・品質ゲート通過とは報告しない。
- 新v3 runnerと実Windows ownerの統合は未検証。元マーカー欠落主因も未解決。新規統合の範囲/許可・実測予算、format制限、親ゲート鮮度の確認が残る。ready_for_retry=false、台帳28pass/80not-run・対象外2、06-06未開始、出荷不可を維持する。
- 最終全件検証後の品質入力差分は `開発履歴.md` の追記のみ。追記後の `tests/test_release_contract.py` は30 passed / 1 warning / 107.50秒。対象diff-check成功。保存30原本と回答hash・台帳28/80/2も一致した。照合結果は `debug/phase06-w05c-no-marker/collection-implementation-verification.json`。製品版番号は検証基盤のみの変更のため維持した。

## 保存証拠から確定できること

正本は `06-05-evidence/W05c_quit-no_at_script-20261105T072535Z-incomplete-raw/`。`run/uat-owner-native-quit/w05c-events.jsonl` のseq 6/8/9/10で同owner PID2844・生成時刻134383350518202484・HWND1511672のNo受信、元False、元quit戻り、元マーカー生成を確認する。seq 11はwatchdog開始である。

| 区間 | 保存値からの差分 | 解釈 |
|---|---:|---|
| No受信→元マーカー | 74.681 ms（UTC） | 今回はNoが正常に戻り元マーカーも成立 |
| 元マーカー→watchdog開始 | 97.672166秒（同ownerの単調時計） | 機械採取に使えた時間は存在したが、未実施 |
| watchdog開始→回答JSON取得時刻 | 約1958.220秒（UTC、約32分38秒） | 回答JSONは生存期間後に記録されている |

回答の時刻は `answer-original.json` の `answer_captured_at=2026-11-05T07:25:35.5599089Z`。利用者の送信時刻、ツール許可待ちの開始/終了、モデル処理待ちの内訳は保存されていない。遅延全体を利用者、製品、承認待ちのいずれかだけの責任としない。回答時刻は遡及変更しない。

v2実装の `tests/w05c_evidence.py::checkpoint` は回答JSONを読み込んでからsnapshotを依頼する。`06-05-w05c-evidence.cjs::validate` は回答取得と意味承認を `before_peer` のsnapshot／後続peerより前に要求する。`tests/test_startup_windows.py` のpeer入口も成功したbefore_peerと回答記録の一致を要求する。このため「No検知で既存peerを先に起動する」「回答時刻の比較だけ削除する」は現行契約と両立しない。

## 採取と受入を分ける設計（実装済み、Windows統合未検証）

既存v2はそのまま保持する。新しいschema/versionを持つPython用採取契約を別途実装し、v2へ自動フォールバックしない。機械採取完了は `machine_collected_pending_answer` として保存し、直接回答の確認と正式helperの採用を終えるまで台帳はnot-runとする。

| 段階 | 実行条件と処理 | 不成立時 |
|---|---|---|
| 起動前準備 | run保存先・固定argv・単発採取runner・終了回収・記録先・権限・入力hashを準備。必要な実行許可は起動前に完了し、途中で新しい承認やチャット応答を待つ構成にしない。承認を回避する実装にはしない | ownerを起動しない |
| owner開始/確認中 | 同runを1つだけ起動し、同ownerの確認中peerを1回記録。採取runnerはownerの実watchdog登録期限に接続し、稼働を確認する | 証拠保存後、同ownerだけを回収 |
| 利用者No | 利用者は同じ確認で「いいえ」を1回押し、画面が残っている間に確認消失・全3ページ・各向き・1画面を観察する。代理No・強制Raiseは行わない | 正常証拠を補完せず未成立 |
| 機械採取 | runnerが同owner/HWNDのNo→元False→元quit戻り→元マーカーと編集状態を検査し、成功時だけNo後peerを1回実行、同owner/constructed=0を確認してsnapshotを固定する。チャット回答は条件に含めない | 後続peerを増やさず回収前の失敗証拠を保存 |
| 観察時間/回収 | 最初の採取だけで直ちに画面を閉じない。起動前に定めた観察区間を確保し、既存watchdogより前の回収予算を残した期限で最終snapshot→inspect→通常stop→同owner終了を確認。チャットを待って延長しない | 余裕不足、watchdog先行、owner喪失、回収失敗は未成立 |
| 後着回答 | 同runを示した質問への原文・出所・実取得時刻を別ファイルへ追記し、人が意味対応を確認する。観察対象は自動回収より前の画面と明記する | 無回答/曖昧/別run/回収後だけの観察はpendingまたは拒否。採用しない |
| 正式受入 | 原本/hash・機械採取・回答・意味承認・凍結入力・終了を新schema用helperで照合。dry-run→明示書込み→該当行監査を行う | 台帳・カード・既存pass不変 |

`peer_after_answer` はv2ではチャット回答後を意味する。新schemaでは `peer_after_no` 等の別名で区別し、既存フィールドへ同じ意味であるかのように詰め替えない。直接回答がpeerより後でもよいという変更は、人手観察・原文・意味承認の省略を許さない。前景のAPI結果と実foreground、手動切替、自動復帰の直接回答も従来どおり区別する。

### 期限と観察区間

期限はharnessの `entry_registered / entry=watchdog` にある登録起点・120000 msを使い、新しいobserver開始時刻から120秒を数え直さない。今回のobserver_started→watchdogは約119.852秒であり、起点の違いを無視しない。異なるプロセスの単調時計を未検証のまま差し引かず、owner内で残時間を求めるか、Windows上の同一時計基準を契約・検証する。

起動前に後続peer、snapshot、inspect、通常stop/終了確認の上限時間と余裕を合算して回収予算を確定し、観察区間の終端をその前に置く。既存peerの期限を伸ばさない。Noが遅く、必要な観察時間と採取/回収予算を確保できない場合は、急いで合格扱いせず未成立で回収する。数値と実測根拠が未記入なら開始不可。

利用者への案内は起動前に完了する。「No後に画面が残る間の見え方を観察し、採取後は自動で閉じる。チャット返信の到着まで画面を延長しない」を明記する。観察が完了したかは実回答で確認し、観察区間を用意した事実だけから完了を推測しない。

### 原本と異常時

- 回答を含まない採取manifestへrun ID、owner PID/生成時刻、native HWND、source/input hash、schema、実watchdog期限、採取/回収予算を記録する。採取runnerは固定された同runだけを扱い、重複実行を拒否する。
- 機械snapshot、log prefix、stack、窓/前景、peer、回収前後のcopy/hashを封印してから、別ファイルの回答を結び付ける。回答の追加で機械原本を書き換えない。markerをrunner/helper側で作らない。
- No不足、元戻り不足、marker不足、時系列逆転、異なるowner/HWND、採取エラー、runner停止、権限拒否、時間不足は合格へ進めない。可能な回収前証拠を保存し、同ownerのidentityを再検証して回収する。終了済みPIDや再利用PIDにstopを送らない。
- watchdog/cleanup/stop後に初めて出たFalseやmarkerを拒否する。watchdog先行のrunは、後着回答が正しくても正式採用しない。旧未完了候補に新schemaを付けて不足peer/snapshotを補うことも禁止する。

## 実装と正負対照の引継ぎ

変更範囲はPythonのW05c harness/採取runner、純粋検査helper、正式記録helperと回帰試験に限定した。製品 `_quit`、既存moduleの受入、実EXEの契約を変更していない。新runner/契約の実装・自動対照成功と、新規Windows統合の未検証を区別する。

最初にGUIなしの仮想時計・固定ログ・fake runnerで次を検証する。これは人手受入やWindowsの機構検証を代替しない。

| 対照 | 必須結果 |
|---|---|
| 同runで正常No、チャット回答が120秒後に到着 | 期限内に機械採取/通常回収。回答前はpending。回答・承認・hash照合後だけ新schemaのdry-run候補 |
| 回答なし/曖昧/別run/原文改変/回収後のみ観察 | 機械採取成功でも受入不可 |
| No/False/元quit戻り/markerが各々欠ける | 後続peerなし、未成立証拠保存。自動再試行0 |
| watchdog/stop/cleanupが先、期限直前No | 回収前証拠としてだけ保存し正式採用を拒否 |
| PID再利用、HWND/run不一致、peerが新primary、seq欠落、書出しエラー | 拒否し別processに操作しない |
| 承認待ち/runner起動失敗/途中停止/重複実行/部分JSON | owner開始前なら開始不可、開始後なら未成立で所有runを回収 |
| 採取が早く終わる/Noが遅い | 観察区間を短縮して成功にしない。残時間不足を明示 |
| v2・新schema・旧module・診断run・今回の保存候補を混用 | schema混在・過去runの事後採用を拒否 |
| 正常/異常dry-run | 台帳・カード・原本のhash不変 |

実装後は対象検証、プロジェクト必須Ruff/format/AST/pytest、06-03 resume_contractによる品質・Phase04/05鮮度・凍結入力の照合が必要。新コードに旧2293件成功を付け替えない。実Windowsの差分検証が必要でも、追加GUI禁止中には実行しない。必要性と未検証範囲を提示し、親の再開ゲートまで `ready_for_retry=false` を保持する。

## 現在の結論

新runner/契約の実装・対象/全件自動試験まで完了した。元症状の修復、新規Windows統合、全体format制限の解消、次の正式候補は完了していない。再開前にこれらの検証条件と親ゲート鮮度を確認する。台帳28pass/80not-run・対象外2、06-06未開始、出荷不可を維持する。

## 設計のみの時点の読取検証（保存履歴）

`node .planning/debug/phase06-w05c-no-marker/collection-review-check.cjs` が成功。既存全件品質の167入力、保存原本30ファイル、回答原本と元回答ファイルのhashは全件一致。18イベントの時系列、台帳28/80/2、7か所の設計参照、HANDOFFの新実装未着手/再試行不可/出荷不可/06-06未開始を照合した。結果は `.planning/debug/phase06-w05c-no-marker/collection-review-verification.json`。変更した追跡文書の `git diff --check` は成功、indexは空（global ignoreへのアクセス拒否警告あり）。

Python・製品・harness・正式helper・品質入力は変更していないため、Ruff/pytest/Windows機構対照は再実行していない。この読取監査は新runnerの検証ではなく、既存2293件成功の入力を維持して文書見直しを行った確認である。
