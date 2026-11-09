# W12a 一次・二次 Python 入口 3×3 の採取手順

この手順は `W12a/<primary>-<secondary>@<primary>` の9行だけを対象にする。script は `pagefolio.py`、module は `python -m pagefolio`、relocated は隔離run内の `alternate/pagefolio.py` を通る。一次は `entry-owner-<primary>` の実 `PDFEditorApp`、二次は `entry-<secondary>` で、既存normal/PDF ownerを入口別の一次として流用しない。製品・凍結EXE・元設定/プロンプト/pluginsを変更しない。正式採用までは9行とも `not-run`。

## 起動前の境界

実行担当はPhase04の独立再検証が現行sourceで `passed` か確認する。正式CLI `start` は親freshがなければ起動を拒否する。`tests/test_startup_windows.py` はPhase04のcovered fileかつW05c v3の採取入力なので、変更前のfresh報告やclaimed済みW05c planは新runへ転用できない。全件品質・04/05再検証は親が実施する。

一行ずつ、次のコマンドだけを実行する。`--primary` / `--secondary` を `script`、`module`、`relocated` から選ぶ。runは毎回新規生成され、一つのrunで二次は一回だけ。前景は二次終了直後にWindows APIから自動取得するので、利用者は採取中にチャットへ切り替えない。

```powershell
.venv/Scripts/python.exe .planning/phases/06-release-validation/06-05-w12a-driver.py --primary script --secondary module
```

driverは一次のreadyを待ってから20秒の準備時間を表示し、二次を一回だけ起動する。利用者は一次の実画面で編集状態を作り、その状態を覚える。例: 設定画面の入力欄に値を入れ、選択位置を作る。二次起動後は15秒間、画面の個数・同じ一次への実復帰・入力/選択状態の保持を見る。端末やチャットを前景にしない。終了直後の外部前景 snapshot `w12a-after-peer.json` は、driverが結果を表示する前に保存する。driverは `inspect` と通常 `stop` を行い、`w12a-driver.json` に時系列を保存する。予算はstart最大30秒、準備20秒、peer最大20秒、観察15秒、inspect最大5秒、stop最大15秒で105秒以内。一次の独立watchdogは120秒。期限不足・例外・二次の失敗は再peer/再起動せず、所有runの通常stopを一回試みて生証拠を残し、対象行は `not-run` のままにする。stop失敗時はwatchdog後に同runを読み取り、複数PID killはしない。

readyに記録された一次ownerの実watchdog登録・期限時刻を使い、準備・peer・観察・inspectの各段階で残作業最大時間と通常stop用15秒、さらに10秒の余白を予約する。不足時は次のpeerや待機を行わず直ちに通常stopする。原本/source/親freshが途中で変化しても、stopはrun・fixture・一次PID+FILETIMEを照合して先に回収し、変化を失敗証拠として保存する。watchdogの期限は延長しない。

利用者へrun終了後、完全な行ID（例 `W12a/script-module@script`）付きで次を直接尋ねる。回答原文にもその完全な行IDを含める。回答は表示を見た利用者自身の原文を保存し、担当が代理で「はい」を作らない。

1. 二次起動後も編集画面は一次の1つだけでしたか。
2. 二次の後、同じ一次画面が実際に前面へ戻りましたか。
3. 一次で作った入力・選択などの編集状態は保たれましたか。

回答後、実行担当はrun内の `manifest.json`、`w12a-driver.json`、`w12a-after-peer.json`、`inspection.json`、`provenance-before-stop.json`、一次/二次のready・result・resource-audit、元設定2 prompt/pluginsの不変とsource hashを確認する。二次 `resource-audit` のowner PID+64bit FILETIME・`allow_foreground.allowed/os_error` と、別の実foreground HWND+PIDを照合する。`allowed` だけでは表示合格としない。relocatedでは隔離したcopyの全Python bytes hashを元sourceと照合する。

helper自身の開始時SHAと現行SHA、および現行Python入力のpath集合と全bytes hashも照合する。追加・削除・変更・symlinkがあれば採用しない。機械回収が完了し、上記3問の直接回答を保存した後、**別の回答**として利用者へ「この行を正式に採用しますか。採用する場合は『採用』または『採用してよい』と明示してください」と尋ねる。否定・保留・不明は採用しない。回収前承認は無効。

## 回答JSONと正式記録

実行担当は `.planning/phases/06-release-validation/06-05-evidence/` に次の形の新規JSONを置く。runはdriver出力の絶対path。`manifest_sha256` はrunのmanifest全bytes、`owner_process_created` はJSONに記録された64bit FILETIMEの**十進文字列**、`answer_sha256` は `direct_answer.text` のUTF-8 bytes hash。時刻は実際のISO 8601時刻、`source_ref` は二つの異なる利用者直接回答の参照を記す。回答原文は改変しない。

```json
{
  "schema": "w12a-answer-v1",
  "primary": "script",
  "secondary": "module",
  "row": "W12a/script-module@script",
  "run": "C:/Users/shdwf/work/project/PageFolio/.planning/tmp/pagefolio-uat-<32hex>",
  "manifest_sha256": "<64hex>",
  "owner_process_created": "<FILETIME decimal digits>",
  "direct_answer": {
    "source": "user-direct",
    "row": "W12a/script-module@script",
    "text": "W12a/script-module@script: <利用者原文>",
    "source_ref": "<直接観察回答への参照>",
    "captured_at": "<ISO8601>",
    "observations": {
      "one_primary_screen": "はい",
      "secondary_returns_to_primary": "はい",
      "state_kept": "はい"
    }
  },
  "adoption": {
    "decision": "採用",
    "approved_by": "利用者",
    "source": "user-direct",
    "source_ref": "<回収後の別回答への参照>",
    "text": "採用",
    "approved_at": "<ISO8601>",
    "answer_sha256": "<direct_answer.text UTF-8 SHA256>"
  }
}
```

ファイル名は `W12a_script-module_at_script-YYYYMMDDTHHMMSSZ.json` の形。まずdry-runで全照合だけを行い、利用者の明示採用が揃った場合に限り同じファイルで正式記録する。dry-runと拒否は全ファイル無変更。正式記録は対象1行・対象UAT card・新規raw copyだけを更新し、兄弟行と旧supersede履歴は保持する。

```powershell
node .planning/phases/06-release-validation/06-05-record-w12a.cjs W12a_script-module_at_script-YYYYMMDDTHHMMSSZ.json --dry-run
node .planning/phases/06-release-validation/06-05-record-w12a.cjs W12a_script-module_at_script-YYYYMMDDTHHMMSSZ.json
```

対象の9組は `script-script`、`script-module`、`script-relocated`、`module-script`、`module-module`、`module-relocated`、`relocated-script`、`relocated-module`、`relocated-relocated`。1組ごとに新規run、直接観察回答、回収後承認を得る。これは採取手順の準備であり、実機受入・06-05完了・出荷許可を意味しない。`release_allowed=false` を維持する。
