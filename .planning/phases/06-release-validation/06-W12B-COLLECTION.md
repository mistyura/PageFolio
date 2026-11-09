# W12b 混在9行の外部採取

この手順は `W12b/<condition>@<entry>` の9行だけを対象にする。機械採取の準備と正式受入は別段階である。未改変v1.10.2最終EXE、同版の別run完全copy、実script/module入口、承認済みv1.9.1技術tracerを区別する。旧tracerや旧Python passを現行へ転用しない。

## 採取前

Phase04の現行sourceで独立fresh `passed` を確認する。driverは現行Python全入力、06-05採取helper群のpath集合と全bytes、元設定/2prompt/plugins、Phase04 status・covered_digest・報告hashを固定する。最終配布tree/hashは `06-BUILD-EVIDENCE.json` の世代5と照合する。tracer行は `06-W12B-NEW-TRACER-20261107.json` と保存した64入力source manifest、両report、保持配布treeを照合し、source側の起動排他/固定namespace/protocolの実装対応を確認する。いずれかが不明なら新しいGUI試行を始めない。

一次Pythonの混在runだけは実 `PDFEditorApp` をscript/module入口から固定production namespaceで起動する。開始前に既存ownerの不在を読取確認し、不在を証明できなければ拒否する。一次EXE・tracer・別配置copyは `release_uat_support.prepare/start` の隔離copyを使い、起動前に設定不存在のoverlayを明示宣言する。停止後snapshotは `copy.ok`、未宣言ファイル、追加・欠落ディレクトリ、配布ファイル変更も確認する。二次は一回のみ。Python二次は `entry-script`/`entry-module` の実入口、EXE二次は未改変copyを引数・hookなしで起動する。一次ownerと二次のPID・64bit FILETIME・session・image、二次の期限内終了、一次のwindow/実foregroundを別々に保存する。一次起動後に20秒の状態準備時間を設け、利用者が入力・選択などの元状態を作る。二次後の即時foreground snapshotが終わるまで端末やチャットへ切り替えない。準備時間を含め120秒のowner期限内に回収余白を確保できなければ、二次を起動せずnot-runとして回収する。

一行ずつ次を実行する。`--row` は下記9条件のいずれか。最終配布元の絶対pathは世代5正本と一致するものだけを指定する。隔離runの準備は一次起動より前に行う。一次が実行中になった後は期限余白を確認し、peer→即時前景snapshot→直接観察回答→inspect→所有runだけの通常stopを行う。期限不足・異常時は再peer/再起動せず、先に回収し失敗証拠を残す。

```powershell
.venv/Scripts/python.exe .planning/phases/06-release-validation/06-05-w12b-driver.py --row exe-script@production-exe --final-distribution "C:\Users\shdwf\AppData\Local\PageFolio-release\pf06_final_3f96a37a7cef4ee1ab3a1c1b2f2c435f\PageFolio-v1.10.2"
```

`exe-exe-samecopy@production-exe`、`exe-script@production-exe`、`script-exe@script`、`exe-module@production-exe`、`module-exe@module`、`exe-tracer@production-exe`、`tracer-exe@tracer`、`exe-relocated-copy@production-exe`、`relocated-copy-exe@relocated-copy` が対象である。

driverが実foregroundを保存してから、利用者本人が端末へ完全行ID付きで観察原文を入力する。確認事項は「一次画面は1つだけか」「二次後に同じ一次画面へ実際に戻ったか」「元の入力・選択などの状態は維持されたか」の3点で、順に肯定なら `W12b/exe-script@production-exe: はい/はい/はい` のように完全行IDと3回答を本人が入力する。1つでも否定・不明なら実際の回答を保存し、正式採用しない。session同一性は実行担当が外部PIDで照合する。観察回答は通常stop前、正式採用回答はstop・最終回収・原本hash確認後の別回答とする。無回答/timeoutではnot-runを維持する。画面観察をAPI成功から推定しない。

未改変EXEが二次の行では、EXE内部の `AllowSetForegroundWindow` 戻り値・OS errorを外部observerが取得できない。driverは `api_return.status=unsupported` と原文で保存する。別processから同APIを呼んだ結果や前景成功を代用しない。この7行は現時点で正式helperが採用を拒否し、not-runのままにする。実Python二次の2行だけは既存 `resource-audit.json` の真の戻り値を照合できる。取得不能な条件は受入条件の緩和では解消しない。

## 回収後の回答と記録

`run/w12b-machine.json` とrun内のmanifest・peer audit/result・inspect、元設定/2prompt/plugins、両配布tree/hash、Phase04 freshを確認する。利用者に別の直接回答として「この完全行IDの証拠を正式採用しますか。採用する場合は『採用』または『採用してよい』と答えてください」と尋ねる。否定・保留・回収前承認は採用しない。

次の新規JSONを `.planning/phases/06-release-validation/06-05-evidence/` に作る。`direct_answer.text` はdriverが保存した観察原文を**無改変**で転記する。`machine_sha256` はrunの `w12b-machine.json` 全bytes、`answer_sha256` はその原文のUTF-8 SHA256。時刻と二つの `source_ref` は異なる実際の利用者直接回答に結ぶ。回答を担当が代理生成しない。

```json
{
  "schema": "w12b-answer-v1",
  "condition": "exe-script@production-exe",
  "row": "W12b/exe-script@production-exe",
  "run": "C:/Users/shdwf/work/project/PageFolio/.planning/tmp/release-uat-<32hex>",
  "machine_sha256": "<64hex>",
  "direct_answer": {
    "source": "user-direct",
    "row": "W12b/exe-script@production-exe",
    "text": "W12b/exe-script@production-exe: はい/はい/はい",
    "source_ref": "<stop前の直接観察回答参照>",
    "captured_at": "<ISO8601>",
    "observations": {
      "single_primary_screen": "はい",
      "same_session_return": "はい",
      "primary_state_kept": "はい"
    }
  },
  "adoption": {
    "decision": "採用",
    "approved_by": "利用者",
    "source": "user-direct",
    "source_ref": "<回収後の別回答参照>",
    "text": "採用",
    "approved_at": "<ISO8601>",
    "answer_sha256": "<direct_answer.text UTF-8 SHA256>"
  }
}
```

ファイル名は `W12b_exe-script_at_production-exe-YYYYMMDDTHHMMSSZ.json`。以下を順に実行する。dry-run/拒否は全ファイル無変更、正式時だけ対象1row/cardと新規raw copyを更新する。他行、旧supersede履歴、EXE兄弟行は変更しない。

```powershell
node .planning/phases/06-release-validation/06-05-record-w12b.cjs W12b_exe-script_at_production-exe-YYYYMMDDTHHMMSSZ.json --dry-run
node .planning/phases/06-release-validation/06-05-record-w12b.cjs W12b_exe-script_at_production-exe-YYYYMMDDTHHMMSSZ.json
```

これは採取基盤であり、実機受入・06-05完了・出荷許可を意味しない。`release_allowed=false` を維持する。
