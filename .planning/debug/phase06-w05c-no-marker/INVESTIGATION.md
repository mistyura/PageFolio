# W05c/script マーカー欠落の調査記録

元runの主因は未解決。回収時の例外は専用runで直接再現できたが、利用者の「いいえ」が元dialogへ届かなかった理由は保存証拠から判定できない。製品・既存harnessを推測で修正せず、正式受入は変更しない。

## 立証できた範囲

| 診断 | 観測 | 判定 |
|---|---|---|
| 確認中peer→No実クリック→回答後peer | native WM_COMMAND=7受信、約14ms後にaskyesno=False、root/3ページ/[90,90,0]維持、quit-cancelledあり | 正常経路を1件観測 |
| No未入力→stop | cleanupでdoc=None→再入_quitがroot破棄→外側askyesno=False→ready:2204 TclError、quit-cancelledなし | 元stderrと同じ回収経路を1件再現 |
| 確認中peer→利用者のNo操作（強制Raiseなし） | WM_COMMAND=7受信、約85.9ms後にaskyesno=False、root/3ページ/[90,90,0]維持、quit-cancelledあり | 正常経路を追加で1件観測 |

No入力の診断は `.planning/tmp/pagefolio-w05c-probe-331580d77a8d42b883916f102fa72e39`、未応答回収の対照は `.planning/tmp/pagefolio-w05c-probe-4f6cdc66239b459fae857a9b291c2111`。両runは保持。`no-click/` と `stop-pending/` に参照用のテキスト保存を置いた（改行は正規化、元bytesの証拠は各run内を参照）。

元runは回答後peerでも同じnative HWND11276710を捕捉した。一方、最終定期stackのmtime04:03:24.263Zは回答後peer04:03:27.455Zより前で、Noの時刻は記録されていない。したがってこのstackだけで「No後も待機した」と断定しない。

回収による例外は、No自体を受信しなくても生じる。元stderrだけからNo操作の製品不具合を結論にできない。また、正常診断でも確認中peerのforeground_deniedは発生しており、それだけではNo不成立の十分条件にならない。

## 残る不確実性

- 元runのNo入力が元dialogへ到達したか、受信後に戻りが停止したかは不明。入力失敗・製品不具合・環境要因のいずれも確定しない。
- 正常診断では前面化操作を加えた。100ms周期の観測とnative subclassも追加しており、元の入力経路・タイミングの完全再現ではない。
- 診断はいずれも正式UATではなく、製品修正の検証でもない。既存W05c/scriptはnot-runのまま。

## 利用者No操作のcheckpoint結果

新規run: `.planning/tmp/pagefolio-w05c-probe-8ba3b45be3cd4c07b43c2b56fd4588cc`。原文回答は **「押した・確認が閉じた」**。回答と機械観測を `human-no/answer.json`、参照用ログを `human-no/` に保存した。元runは保持している。

- 04:40:37.750702Z: 同じnative HWND8523634へWM_COMMAND=7が到達。
- 04:40:37.836612Z: askyesno=Falseが戻る（85.903ms後）。rootは生存、3ページ/[90,90,0]を維持。
- 04:40:37.837Z: quit-cancelled作成。37.853099Zの観測でもcancelled=true。
- 04:40:43.763799Z: watchdogによるcleanup開始。askyesnoが戻った約5.93秒後であり、回収時のFalseをNoとして採用した結果ではない。
- 04:40:43.918116Z: root破棄。Tk callback例外0、ready:2204例外なし、PID30848は終了。元設定/2プロンプトは開始前後すべて不存在で一致。

診断driverに前面化/入力APIはなく、このrunではCUAのRaise/代理No操作も行っていない。今回は利用者のNoが正常に戻ったため、元runの主因を示す新しい失敗区間は得られなかった。100ms観測とnative subclassによる観測影響の可能性は残る。診断3件はいずれも正式UATや製品修正の確認には採用しない。

元runにはWM_COMMANDとask_returnの記録がなく、今回の正常結果から過去の入力先・停止機構を復元できない。現在の証拠でこれ以上の主因判定はできないため、追加GUI/再質問/テストを行わず、この操作checkpointを完了とする。元症状は未解決として保存する。

## 診断driver

`probe.py` は既存harnessを呼び、試験専用nonceと新規 `.planning/tmp` runで原設定/プロンプトを隔離する。終了確認のnative WM_COMMAND/破棄、askyesno/quitの開始・戻り、cleanup、root破棄、Tk callback例外を `probe.jsonl` へ記録する。製品の終了判断を置き換えない。

再発を調べる場合の準備:

```powershell
.venv/Scripts/python.exe .planning/debug/phase06-w05c-no-marker/probe.py start
```

返された新規runだけを対象に、`peer --run <返されたrun> --entry script`、可視のNo操作、`inspect --run <同run>` を行う。No受信後も戻らない場合は、回収前の `probe.jsonl` とstackを先に保存する。`stop --run <同run>` は未応答dialogを破棄するため、その後のFalseを利用者のNoとして採用しない。GUIは可視で操作し、人手UATの採否は別途扱う。

## 検証と意図外変更

`verification.json` に実測を保存した。

- 既存品質入力118件は全件SHA一致。直近の全件試験2254 passedは同入力のため再利用し、新たなpytestは実行していない。
- 実ソース115ファイルとdriverの計116ファイルは `ruff check` と `ruff format --check` がexit0。`pagefolio.py` とdriverのAST解析も成功。
- 必須の全体 `ruff check .` は既存basetempの生成fixture95件とアクセス拒否により完走せず、全体 `ruff format .` は既存生成fixture153ファイルを意図外に整形し、invalid fixture/アクセス拒否でexit1。これらの全体ゲートは合格扱いにしない。
- 整形対象153件はすべて `.planning/phases/04-startup-control/04-reverify-20261105-full/basetemp` 配下。現在のSHA/size/mtimeは `formatter-impact.json`。整形前bytesの保存がなく推測復元していない。
- 同時刻のbasetemp外Python変更は0件。走査不能4ディレクトリは `verification.json` に列記し、網羅確認とは表現しない。
- 元W05c34証拠は全件SHA/size一致。製品・testsを含む118入力不変。正式受入台帳・凍結EXEの更新は実施していない。

セッションはinvestigatingを維持し、診断結果inconclusiveとして残す。今回の操作checkpointは回答照合済み。正式受入は必須28 pass / 80 not-run、対象外2、出荷不可を維持する。主因未立証のため解決済みへの移動・commit・Phase完了は行っていない。将来の再開には、同一native HWNDへのNo受信時刻とask_return未完了区間を含む新たなマーカー欠落の証拠が必要であり、自動再開だけで同じ正常診断を繰り返さない。
