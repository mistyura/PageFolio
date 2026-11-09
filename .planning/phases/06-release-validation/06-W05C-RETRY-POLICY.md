---
phase: 06-release-validation
plan: "05"
task: "06-05-02"
status: design_complete
implementation_status: validated
ready_for_retry: false
created: 2026-11-05
---

# W05c 証拠採取と再試行の見直し

## 2026-11-05 候補停止後の手順見直し（最新）

`06-W05C-COLLECTION-REVIEW.md` を現行の実装/検証正本とする。v3採取runner/契約を実装し、対象79件・最終全件2333件成功（170入力前後不変）。既存pytest自動GUIのみ利用者許可済み。新規v3 Windows統合は未検証、全体formatは既存tmpアクセス拒否で未通過。元主因未解決、ready_for_retry=false、台帳28pass/80not-run・対象外2、06-06未開始・出荷不可。全体formatの既存検証tmpアクセス拒否を解消し、新規v3 Windows統合の範囲/許可・実測予算を確定する。再開前に06-03 resume_contractで親ゲート鮮度を照合。新規統合/正式試行/期限延長/正常診断反復/製品推測修正/commitは自動実行しない。 frontmatterのimplementation_status: validatedは旧v2の履歴である。

## 2026-11-05 候補1回後の停止（保存履歴）

新規script候補を1回実施。No/False/元マーカーは成立したが、回答後peer/回収前snapshotより前に120秒watchdogで終了した。元マーカー欠落は今回再現していない。追加試行0、ready_for_retry=false、正式台帳のpass追加0。原本30ファイルと回答を保全し、owner終了確認済み。`06-W05C-CANDIDATE-STOP-20261105.md` を正本として `$gsd-debug continue phase06-w05c-no-marker` へ戻す。以下の候補開始条件が成立したという記述から直接再起動しない。

## 2026-11-05 計測実装後の現在地（候補開始前の履歴）

`06-W05C-INSTRUMENTATION.md` に従い、計測・回収前検査・正式helperと正負/機構対照を実装した。対象39件とnative全件2293件（失敗/ERROR/skip各0、167一意入力の前後/現行一致）が成功。現在の全体Ruff/format/ASTは成功、Phase04=21/21・Phase05=23/23を必須ゲートで再検証し公式statusは両方passed。凍結配布物build-only監査成功、通常production ownerと所有検証process、参照配布先build lockは不在を確認した。利用者の操作可能時間の回答待ちのため `ready_for_retry=false` を維持する。

元No不成立や過去153fixture整形事故の原bytes不明を解決したとは扱わない。開始前Ruffの一過性アクセス拒否警告も原本保持し、終了後の警告なし再確認と区別する。新規正式script候補は0回、台帳28pass/80not-run・対象外2、EXE手順未整備、06-06未開始・出荷不可は不変。以下の「未実装」は方針設計時の履歴であり、現在の実装状況は本節と計測報告を優先する。

2026-11-05の利用者指示「W05cの証拠採取・再試行方針を見直しを進めて」に対応する設計。今回の変更は計画・操作カード・再開案内だけであり、計測実装、GUI起動、受入採用、停止条件の解除は含まない。

## 判定と適用範囲

- 正式台帳は必須108行中28 pass / 80 not-run、W11対象外2 not-runのまま。W05cはmoduleのみpass、scriptとproduction-exeはnot-run。
- 元run `pagefolio-uat-tone_ht2` のマーカー欠落と34ファイルの原本を保持する。診断3件を正式受入へ転用しない。
- 元runのNo不成立の主因は未特定。回収経路の例外が立証されたことと区別し、resolvedへ変更しない。
- 同じ正常診断を繰り返す旧手順を終了する。次に進める作業は、下記の計測・検証の整備である。整備後の新しい正式受入候補はscriptを1回だけとし、自動再試行しない。
- この設計は既存の異常時停止規則を置き換えない。未解除事項を記録したまま、計測・品質・親の再開ゲートを満たした報告が揃うまで `ready_for_retry=false` を維持する。

## 根拠と不足

| 確認した箇所 | 確認できた事実 | 次回必要な証拠 |
|---|---|---|
| `tests/test_startup_windows.py` の `ready()`（2198〜2205行付近） | 元の `app._quit()` が戻りroot存在確認に成功した後にだけ `quit-cancelled` を作る | この順序を維持し、戻りとマーカーを回収前に採取する |
| 同ファイルの `stop_poll()`（2809行付近） | stopはcleanupでdocを閉じてから再入 `_quit()` する | cleanup/stop/watchdogの開始時刻と呼出元を区別する |
| `pagefolio/app.py::_quit` | Noなら戻る。確認後は保存失敗でも戻るため、関数の戻りだけではNoを証明できない | 同じ確認の実際の戻り値とroot・doc・編集状態を組にする |
| `06-05-record-w05c-python.cjs` | マーカー、2 peer、owner、編集状態、凍結入力、回答原文を照合する | 新計測の時系列を追加検査する。現行helperだけでは新設計の合格を判定しない |
| `debug/phase06-w05c-no-marker.md` と `human-no/answer.json` | 代理入力なしの診断でNo受信→False→マーカーを観測。元runの受信時刻はない | 正常診断の追加ではなく、正式候補の同一runで入力から回収まで記録する |

元runの最終stackは入力後の停止を確定する証拠ではない。`foreground_denied` だけでもNo不成立を説明できない。新しい計測にも動作への影響があり得るため、「観測のみなので無影響」と仮定しない。

## 実装担当への作業契約（未実装）

対象はPythonのW05c用harness・記録helperとその回帰試験。製品 `_quit()` の判断・戻り値・例外を変更する推測修正は行わない。既存 `probe.py` は診断専用であり、そのまま正式driverに昇格させない。

1. **採取経路を整備する。** 同じrun ID、owner PID/生成時刻、native HWNDを全イベントへ結び付ける。UTCと同一プロセスの単調時計、順序番号、採取エラーを記録する。native確認の出現・No受信、元 `askyesno` の開始/戻り、元 `_quit` の開始/戻り、既存マーカーの生成、stop/cleanup/watchdog/root破棄、Tk例外を区別する。native callbackは元処理へ委譲し、Tk操作・入力・前面化・ブロッキングI/Oを追加しない。終了時に未書出し記録がないことを検査する。
2. **回収前の判定を分離する。** 回答後に既存マーカーと新計測を照合する確認段階を作る。欠落を検出したら、ログ・stack・native窓・owner identity・現在の編集状態を先に保存する。その後に既存stopで同じ所有runだけを回収し、回収前と回収後の証拠を別ファイルへ保存する。stopで初めて出たFalseやマーカーを受入に使わない。マーカーをobserver/helper側で作成しない。
3. **記録helperを厳格化する。** 既存照合に加え、下記の順序、欠落、owner/HWNDの対応、期限、回収開始を検査する。利用者回答の原文・取得時刻・出所を保存し、固定表記に合わせた書換えをしない。「1と2」等の表記揺れは原文を保持した意味の対応を別欄へ記録し、根拠が曖昧なら追加回答を待つ。意味の対応を自動推測しただけでpassにしない。旧回答や他runの回答は流用しない。
4. **計測追加の検証を行う。** 下記の正負対照、対象lint/format/AST、必要な品質・鮮度照合を実施する。製品・起動・通知・build入力・収集設定への影響は06-03の `resume_contract` で評価し、必要な新世代準備を省略しない。既存passを新hashへ付け替えない。整備完了報告に対象ファイル/hash・実行コマンド・結果・未解除事項を記す。

### Pythonで必須にする順序

1. 同一ownerの確認窓を捕捉し、確認中peerがconstructed=0で同ownerを参照する。
2. 利用者がその確認の「いいえ」を1回押す。同じHWNDへのNo受信を記録する。
3. 元 `askyesno` がFalseを返し、元 `_quit()` が戻る。rootと3ページ・回転 `[90,90,0]` を維持する。
4. 元 `ready()` が `quit-cancelled` を作成する。この時点までstop/cleanup/watchdog/root破棄が始まっていない。
5. 利用者の直接回答と照合し、回答後peerもconstructed=0で同ownerを参照する。最新focus結果も3ページ・同じ向き・状態維持と一致する。
6. 回収前snapshotを確定してからstopする。回収後にowner終了・原設定/2プロンプト・凍結入力・証拠hashを確認する。

順序の判定は実イベントで行う。ファイルmtimeだけ、No受信だけ、Falseだけ、編集表示だけでは代替できない。手動切替は別欄へ記録し、自動復帰の根拠にしない。許可API結果と実foregroundも区別する。

### 実装後に必要な正負対照

| 入力・条件 | 必須の結果 |
|---|---|
| 同じ確認のNo→False→元マーカー→回答後peer→回収の完全な証拠 | dry-run成功。dry-run中は台帳・カードを書き換えない |
| No受信なし、ask_returnなし、元マーカーなしの各欠落 | それぞれ拒否し、台帳・カード・既存原本を不変に保つ |
| No未入力のまま回収し、その後にFalse/マーカーを観測 | 拒否。回収経路の証拠としてだけ保存する |
| 異なるHWND/owner、時系列逆転、記録失敗/ログ欠落、deadline到達 | 拒否し、自動再試行しない |
| 原文不一致、別run回答、編集内容不一致、peerが新primaryになる | 拒否。表記を直して通さない |
| 旧module証拠や診断runを新script候補として渡す | 拒否。既存module passは保持する |
| 観測の有無を切り替えた自動対照 | 同じ終了判断・編集保持・例外伝播を比較。自動Noは機構検証専用で正式受入にしない |

負対照は合成ログ/隔離fixtureで検証し、利用者に同じ正常診断を再要求しない。GUI/実前景の機構検証が必要になった場合も、既存成功との重複を避け必要な差分だけを検証する。

## 新規script候補を1回実施するための開始条件

全項目の実測根拠が揃うまで起動しない。現時点では未評価/未実装であり、開始条件を満たしていない。

- 上記の計測・回収前確認・helper・正負対照が実装/検証済み。helperの構文確認だけで完了にしない。
- 06-03のresume照合により、Phase04/05鮮度・品質入力/環境・凍結配布物と失効範囲が確認済み。全体Ruffの既知失敗と153生成fixtureの意図外整形を未解消のまま成功と扱わない。入力が変われば旧2254件成功を無条件再利用しない。
- 通常production ownerと前runの所有process/lockが不在。試行・証拠の保持先はrepo内 `.planning` 等とし、%TEMP%に新規成果物を置かない。
- 実行担当が実装済みコマンドを手順へ記入し、利用者が操作可能と回答済み。既存120秒watchdogとpeer期限を延長しない。説明を起動前に済ませ、時間不足なら開始しない。
- 未特定原因、観測影響、単発の候補であることを再開報告に明記し、親の再開ゲートで新手順の開始可否を評価済み。計画改訂だけをゲート通過としない。

## 利用者操作と失敗時の扱い

開始可能になった後の案内は「同じ終了確認の『いいえ』を一度押す→確認が閉じたか→全3ページ・1/2ページが横・3ページが縦・1画面か」を区切る。利用者は見たとおりの原文を答える。利用者の回答前に自動No、代理入力、強制Raiseを行わない。

回答後のマーカー/戻りが欠けたら回答後peerや後続ケースへ進まず、回収前証拠を保存する。120秒以内に採取できない場合もwatchdogを止めず、その開始時刻を記録し、試行を未成立として回収する。異常・無回答・期限切れは新runの未成立理由として追記し、元失敗を上書きしない。再発時の追加試行は0回で、同じdebugへ戻す。

全条件成立時も直ちにpassにせず、回収後の正式helper dry-run→書込→該当行監査を順に行う。現行 `--require-pass W05c` はEXEを含む全subrowを要求するため、scriptだけの段階ではW05c全体合格と報告しない。moduleを再実施しない。

## production-exeへの境界

Pythonの計測成功はEXEの観測に転用しない。scriptを正式採用した後で、固定hashの未改変EXE用記録手順・helperを整備/検証してから別runへ進む。

- 実EXEへPython hook・native subclass・試験引数を注入しない。`quit-cancelled` や内部ask_returnが存在すると仮定しない。
- 同じ確認窓の表示/消失、利用者No回答、全3ページと各向き、単一画面、確認中/回答後の同owner・peer・実foregroundを外部から記録する。外部観測で得られない内部経路は未観測と明記する。
- 回収前の記録を固定してからstopし、通常終了/force終了を別欄へ残す。回収時の窓消失を利用者Noによる消失と取り違えない。
- Pythonと異なる証拠モデルをEXE用helper/監査で検証する。手順やhelperがない段階ではEXEを起動しない。

## 完了条件と現在の次作業

方針見直しは完了。計測・helperの実装と正負対照は未実施、正式再試行は0回、原因は未解決。次は本契約の「実装担当への作業契約」をGSD内で実装・検証する。直接 `--uat start` や `probe.py start` へ進まない。

旧停止報告、既存2254件の品質証拠、全体Ruff失敗、BUILD-LOSS-20261103、tracer消失等はそのまま残す。本書は免除・出荷承認・Phase完了の根拠ではない。

## 今回の文書改訂の検証

- `tests/test_release_contract.py::TestCaseCoverage` のケース重複/割当、未判定行の必須欄、全カードのラベル/必須観測、Python注入とEXEの分離を検査する4件が成功（4 passed / 既知PyMuPDF廃止予告1件、0.12秒）。`-p no:cacheprovider` とrepo外 `%LOCALAPPDATA%/PageFolio-validation/w05c_policy_<一意ID>` のbasetempを指定した。
- HANDOFFのJSON解析、ready_for_retry/出荷/Phase完了のfalse、全6案内文書からの本書参照、台帳28/80/2を読取照合して成功。
- `pagefolio/app.py`、`tests/test_startup_windows.py`、診断 `probe.py`、W05c記録helper、正式台帳、BUILD証拠、既存debug `verification.json` の7ファイルは開始時と終了時のSHA-256一致。
- 対象の追跡文書の `git diff --check` は成功、indexは空のまま。製品/Python/同梱文書/版番号は変更せず、GUI・再build・全件pytest・全体Ruff・commitは実行していない。今回の局所4件は未実装計測の検証や全体品質ゲート成功を意味しない。
