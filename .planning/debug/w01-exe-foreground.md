---
status: resolved
trigger: "出荷停止状態を解消して / W01実EXEの前景観測不一致"
created: 2026-10-28
updated: 2026-10-28
---

## Current Focus

hypothesis: 診断runでは実際に自動復帰し、その後PowerShell上のクリックで前景が移ったことを連続観測した。元状態記録前の最小化と、観測中の切替を防ぐ手順案内・判定が不足していた。
test: 最初の原本を保全し、利用者の実観察とdriverの観測区間・既存読み取り専用入力監視を照合する。製品期限・前景権限・起動引数は変更しない。
expecting: 前景遷移と操作の時系列で一時復帰後の手動切替、前景化拒否、元状態準備不足を区別できる。
next_action: 正式driverのW01でもpeer区間を連続監視し、全ウィンドウ上のクリックを手順汚染として保存する。通常状態/最小化を確認できなければ二次起動せず止める。4秒の既存観測終了後に音を鳴らして回答開始を案内する。機構確認後に正式UATを再開する。診断はpassへ転用しない。

## Symptoms

expected: 最小化前の同一状態・同一矩形・ステータス文字を保ち、二次起動後の実foregroundが既存PageFolioになる。
actual: 最新runでは通常状態へ復元されて同一の起動時矩形になったが、peer約4秒後のforegroundはPowerShell。最小化前snapshotはすでにiconic=trueで、必要な準備観測も不成立。
errors: 製品例外の証拠は現時点でない。copy保護・正常終了・owner解放は成功。
timeline: 2026-10-28のW01正式UAT。最初の配布版runは前景が一致したが、設定overlay未宣言で不採用。その後2回の終端前景がPowerShell。
reproduction: uat_row.py --row W01/normal@production-exe。製品は凍結世代5 EXE hash 66be5df663e333057c5c3cde02180857f930d2433e377f69c2838432d49a19d4。

## Evidence

- `W01_normal_at_production-exe-20261028T101300Z.json`: 同一HWND35852470・矩形・実前景は一致。終了時に設定作成されoverlay未宣言のためverify_after.ok=false。原本4ファイルを保存しnot-run attempt。driverへ設定不存在overlayを事前宣言する修正済み。関連29 tests passed。
- `W01_normal_at_production-exe-20261028T101828Z.json`: 同一HWND22875480・矩形保持、保護検査成功。終端PowerShell。利用者「PageFolioが戻った後、自分でPowerShellへ切り替えた」。原本保存済み、手動切替による観測不成立としてnot-run attempt。
- `W01_normal_at_production-exe-20261028T102221Z.json`: run d79a2d088f504e288de0cb4de5e5eca0。10:21:45.644864Zのbefore-minimizeは既にiconic。10:21:50.953361Zにpeer前Enter、10:21:55.156674Zのafter-peerはHWND13307238の通常状態・矩形[234,228,1450,1067]だがPowerShell HWND37683358が前景。status_kept入力は「尾内」で、同じへ自動補正しない。利用者の完了申告「10秒待って確認を完了した」。追加の実観察回答待ち。

## Scope

GSD debugを初期化済み。既存依頼の範囲で親が小さな調査を直接実施する。次の本受入・コミットは停止し、原本・未実施判定を保全する。既存合格2行と無関係なdirty変更は維持する。診断や観測補助を本受入passに流用しない。

## 連続観測（2026-10-28 10:30 UTC）

`w01-exe-foreground-evidence/observe-20261028T103018Z.json`、run `7d3427babd214b939ffc4b99a28fbb63`。元状態normal→最小化成立。8ms読み取り専用監視1656 samples、最大gap13ms、errorsなし。peer開始約0.192秒でPowerShell HWND6098014からPageFolio HWND11735488へ実前景が移った。約2.424秒でPowerShell上の左クリック（座標1581,381）を検出し、同じ時刻にPowerShellへ前景が移った。4/10/14秒snapshotはいずれもPowerShell。利用者入力はvisible=PageFolio、operation=していない、note=なしで、機械記録との相違をそのまま保持する。クリックの発生を記録した事実を越えて、その主体を断定しない。配布元不変、設定のみoverlay変更、primary closed・peer already-exited・owner空。

この診断は前景化失敗ではなく一時復帰後のクリックによる切替を支持する。元の点観測runで起きた全操作へ一般化しない。製品・EXE・期限・前景権限APIは変更しない。

正式driverの補助変更後、`--check-monitor` の既存ケースとW01追加3ケースを検証した。追加テスト初回は偽サンプラへ辞書でなく整数を渡してTypeErrorとなり1件失敗。入力を辞書へ訂正して全機構確認成功。実APIの読み取り監視も約0.6秒のサブプロセス待機中に継続・正常停止した。全PythonのRuff/format/AST成功。音は4秒観測の終了後にのみ鳴らし、製品の期限を延ばさない。原因を区別する機構が整ったため、次の正式runで無操作・実前景・元状態/文字・保護を確認する。

正式run `W01_normal_at_production-exe-20261028T103611Z.json` は最初のEnter時点ですでに最小化されていた。新しい準備検査でpeerを起動せず停止した。原本3ファイルとnot-run attemptを保持。通常画面については起動直後の位置を先に記録し、覚える→最小化→Enterの1段階にした。観測条件・4秒・終了音・監視は維持。Ruff/format/AST成功後、19:38:19 JSTに可視PowerShell PID30464で新runを開始した。

その正式run `W01_normal_at_production-exe-20261028T103918Z.json` でも0.230秒で自動復帰、2.812秒のPowerShellクリックで前景が移った。無操作終了音より前のクリックを検出したため不採用のまま原本を保存。二次起動の実終了時刻を従来driverが持っていなかったことも分かり、固定4秒待機を`Popen.wait(timeout=4)`へ変更し、正常終了code=0の直後に実前景を記録する方式にした。S.peerの既存popen注入で返された所有子ハンドルを保持するだけで、EXE引数・cwd・stdio・製品コード・製品期限・前景権限は変えない。外部の上限も4秒のまま。終了code/時刻を保存し、pass記録にはそれらと実前景・無操作・全既存条件を要求する。任意時点の短い一時復帰を後付けでpassとする変更ではなく、過去の5attemptはnot-runを保持する。

正式再確認 `W01_normal_at_production-exe-20261028T104332Z.json` で無操作、元状態/矩形/文字の保持、二次起動code=0後の実前景一致、配布物保護、正常終了を確認して台帳へpass記録した。原本4ファイル保存・凍結65入力hash一致。診断をpassへ流用していない。全件pytestはまだ必要で、debugの最終closeoutは品質確認後。

## Resolution

root_cause: 設定保存overlay未宣言と、準備・観測中の画面切替を区別しないdriverの手順/記録不足。前景の連続観測では自動復帰自体は成立し、その後のPowerShellクリックを検出した。旧点観測runの全操作主体や旧世代の原因までは断定しない。
fix: 設定不存在を事前overlay宣言。通常状態の記録を最小化操作前に自動取得。元状態不足はpeer前停止。二次起動の所有ハンドルからcode=0/終了時刻を確認して実前景を採取。peer区間の読み取り専用入力監視と終了音、status_kept直接回答を追加。製品/期限/EXEは変更なし。
verification: W01の6行が正式pass、require-pass W01 exit0。単一全件2233 passed/2 warnings/512.20秒、155入力前後不変、exit0。正本 `.planning/phases/06-release-validation/06-05-evidence/w01-closeout-20261028/result.json` とjunit.xml/checks.json。監視機構確認も全成功。06-05の残る102必須行とW11対象外2未確認を維持し、出荷承認とは扱わない。
