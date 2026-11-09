# W12c Explorer／端末の本人起動と実入力

対象は `W12c/explorer-python@script`、`terminal-python@script`、`explorer-exe@production-exe`、`terminal-exe@production-exe` の4行だけ。準備済みは正式受入を意味しない。各行は一回の一次ownerと一回の本人起動だけを採取し、失敗時に再起動・再peerしない。実機採取前にPhase04現行fresh、Python全入力・06-05 collector全体、この手順書の全bytes SHA256、元設定・2prompt・plugins、世代5の最終v1.10.2配布tree/hashを照合する。旧run/旧承認を現行へ転用しない。

実行担当が次の一行だけを開始する。配布元は `06-BUILD-EVIDENCE.json.final_release.loss_incident.restored_final_dir` の正本と完全一致させる。driverは固定production ownerが不在と読取証明できなければ起動しない。Python一次は既存W12a実script入口の固定namespace、EXE一次は未改変配布の隔離copyで、起動前に設定不存在overlayを宣言する。停止は入力や親報告が変化しても所有一次PID+64bit FILETIMEに限って先に実行する。

```powershell
.venv/Scripts/python.exe .planning/phases/06-release-validation/06-05-w12c-driver.py --row explorer-python@script --final-distribution "C:\Users\shdwf\AppData\Local\PageFolio-release\pf06_final_3f96a37a7cef4ee1ab3a1c1b2f2c435f\PageFolio-v1.10.2"
```

`--row` を対象4条件から一つだけ選ぶ。一次起動後の20秒で利用者本人が一次画面の実入力欄を選び、元の入力状態を作る。driverが起動指示を表示したら、Explorer行は本人がExplorerで表示pathをダブルクリックする。Python行はrun内の事前作成 `.lnk`、EXE行は隔離copyの `PageFolio.exe` 本体を開く。端末行は本人がPowerShellでdriver表示の一行を実行する。実行担当が `subprocess` 起動をExplorer／端末操作と偽称しない。ショートカット/コマンドは開始前に固定したtargetと引数を機械証拠へ記録する。Python二次の実行体 `pythonw.exe`／`python.exe` の全bytes SHA256もrunへ固定し、本人起動前・二次観測後・所有回収後・正式採用時に同じ値を照合する。途中改変では先に所有一次だけを回収し、not-runにする。

二次起動直後、利用者は同じ一次入力欄へ戻って実際にキー入力を続け、画面が増えたかも観察する。driverはチャットに切り替わる前に実foreground、一次PID・FILETIME、入力前後の同じ一次HWNDを自動採取し、通常inspect/stopする。前景とHWNDは実際にどの文字が入ったかを証明しない。本人の入力結果は回収後の直接回答で別に確認する。20秒準備、38秒以内の二次観測、12秒実入力観測、inspect8秒、stop15秒、余白10秒を120秒の一次期限内に確保できない場合は二次を始めずnot-runとして回収する。途中timeoutは保全して終了し、時計延長しない。

未改変EXEの二次では内部 `AllowSetForegroundWindow` 戻り値・OS errorを外部から取得できない。外部foregroundや別processのAPI結果で代用せず `unsupported` と保存し、EXE2行の正式採用を拒否する。Python2行はfixtureの `resource-audit.json` に実二次入口のAPI戻り・OS error、owner照合、peer FILETIMEを保存する。Explorer／端末という経路自体は本人の直接回答と起動物の固定情報を合わせて扱い、OSの前景だけから推定しない。

回収後、利用者へ完全行ID付きで「実際に指定経路から起動したか」「同じ一次入力欄へ実キー入力が入ったか」「一次画面は1つだったか」を尋ねる。肯定3点の場合の原文形式はExplorer行なら `W12c/explorer-python@script: Explorerから起動した/同じ入力先に実入力した/画面は1つ`、端末行なら同じ完全行IDと `端末から起動した` を使う。否定・不明なら実際の回答を保全し、not-runを維持する。続けて別の直接回答として、この完全行の証拠を正式採用するか尋ねる。肯定する場合は `採用` または `採用してよい` と回答してもらう。実行担当は回答を代理生成しない。

新規回答JSONを `06-05-evidence/W12c_explorer-python_at_script-YYYYMMDDTHHMMSSZ.json` のように保存する。`direct_answer.text` と `adoption.text` は本人原文を無改変で保存し、両回答の参照と実時刻を分ける。`machine_sha256` はrunの `w12c-machine.json` 全bytes、`answer_sha256` は直接観察回答原文UTF-8のSHA256。

```json
{
  "schema": "w12c-answer-v1",
  "condition": "explorer-python@script",
  "row": "W12c/explorer-python@script",
  "run": "C:/Users/shdwf/work/project/PageFolio/.planning/tmp/pagefolio-uat-<32hex>",
  "machine_sha256": "<64hex>",
  "direct_answer": {
    "source": "user-direct",
    "row": "W12c/explorer-python@script",
    "text": "W12c/explorer-python@script: Explorerから起動した/同じ入力先に実入力した/画面は1つ",
    "source_ref": "<回収後の本人観察回答参照>",
    "captured_at": "<ISO8601>",
    "observations": {
      "launch_route": "explorer",
      "real_input_target_kept": "はい",
      "one_primary_screen": "はい"
    }
  },
  "adoption": {
    "decision": "採用",
    "approved_by": "利用者",
    "source": "user-direct",
    "source_ref": "<回収後の別採用回答参照>",
    "text": "採用",
    "approved_at": "<ISO8601>",
    "answer_sha256": "<direct_answer.text UTF-8 SHA256>"
  }
}
```

dry-runと拒否では全ファイル無変更。正式記録時だけ対象1row/cardと新規rawコピーを更新し、他行、旧履歴、EXE兄弟行を変更しない。

```powershell
node .planning/phases/06-release-validation/06-05-record-w12c.cjs W12c_explorer-python_at_script-YYYYMMDDTHHMMSSZ.json --dry-run
node .planning/phases/06-release-validation/06-05-record-w12c.cjs W12c_explorer-python_at_script-YYYYMMDDTHHMMSSZ.json
```

今回の採取基盤は実機受入・06-05完了・出荷許可を意味しない。`release_allowed=false` を維持する。
