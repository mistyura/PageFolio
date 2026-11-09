# W05c 実配布 EXE の外部観測と採用

対象は `W05c/quit-no@production-exe` の1行だけ。世代5・最終 v1.10.2 の未改変 EXE を隔離 copy で起動する。script の W05c pass、Python 内部マーカー、`ask_return`、Undo identity、Tk 版、120秒 watchdog は実 EXE の根拠に使わない。採取・利用者回答・明示採用承認がそろうまで対象行は `not-run`、`release_allowed=false` を維持する。2026-11-06 の script 原本と既存 run、損失事故から復元した配布元、未検証の外部 report 2件、初回 tree は上書きしない。

## 開始前の確認

実行担当が `06-03-PLAN.md` の `resume_contract`、Phase 4/5 の現行検証鮮度、`06-BUILD-EVIDENCE.json` と `06-PROTECTION-EVIDENCE.json` の世代5、配布元の hash、通常 production owner 不在を読取確認する。元設定 `pagefolio_settings.json`、2つの prompt、`plugins/` は run の `snapshot_originals` で起動前・回収直前・回収後に比較する。差分がある場合は中断する。親の正式再開ゲートが未成立なら起動しない。

開始前に、利用者へ「確認表示中に二次起動し、その後にご自身で『いいえ』を押す。No 後は外部監視が `after_no` を記録するまで PageFolio を前景に保ち、合図が出てからチャットへ切り替えて直接回答する。代理クリック・自動 No・強制前面化はしない」と説明する。質問文と回答採取方法を先に確定する。回答を待つために無期限に GUI を放置せず、実行担当は事前に観察時間と安全な回収手順を確保する。

## 実行担当の採取順

PowerShell で次のコマンドを順に実行する。`$run` は `prepare` が返した新規 run のみ使い、既存 run を再利用しない。コマンド実行と人のクリックを取り違えない。`inspect` の JSON を毎回保存し、`evidence/inspect-NNN.json` と `manifest.json` に残す。

```powershell
$preparedJson = & .venv/Scripts/python.exe tests/release_uat_support.py prepare --distribution "C:\Users\shdwf\AppData\Local\PageFolio-release\pf06_final_3f96a37a7cef4ee1ab3a1c1b2f2c435f\PageFolio-v1.10.2" --case W05c
if ($LASTEXITCODE -ne 0) { throw "prepare failed; stop without starting an EXE" }
$prepared = $preparedJson | ConvertFrom-Json
$run = [string]$prepared.run
$expectedTmp = [IO.Path]::GetFullPath('.planning\tmp')
if ([string]::IsNullOrWhiteSpace($run) -or $run -notmatch '^[A-Za-z]:[\\/]' -or (Split-Path -Leaf $run) -notmatch '^release-uat-[0-9a-f]{32}$') { throw "prepare did not return an absolute run path" }
$resolvedRun = [IO.Path]::GetFullPath($run)
if (-not $resolvedRun.StartsWith($expectedTmp + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath (Join-Path $run 'manifest.json') -PathType Leaf)) { throw "prepare returned a run outside the owned tmp tree" }
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'tests'); import release_uat_support as u; print(u.add_fixture_pdf(r'$run', 'edit-three-page'))"
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'tests'); import release_uat_support as u; u.declare_overlay(r'$run', {u.SETTINGS_NAME: None}, 'W05c起動前の設定不存在を宣言')"
.venv/Scripts/python.exe tests/release_uat_support.py start --run $run
```

利用者が隔離 copy の3ページ PDF を開き、ページ回転などの未保存編集を作る。実行担当は元 PDF と編集画面を控え、`inspect --run $run` を1回実行する。この記録が `before_confirm`。利用者がウィンドウの ✕ を押し、終了確認を表示したら何も押さずに止まる。実行担当は `peer` を1回だけ起動し、確認が出ている間に `inspect` する。この記録が `during_confirm`。

```powershell
.venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
.venv/Scripts/python.exe tests/release_uat_support.py peer --run $run
.venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
```

No 直後の実前景は、利用者がチャットへ切り替える前に採る。確認表示中の `during_confirm` を採った後、次の外部監視ジョブを起動する。ジョブは一次 PID/生成時刻を読取照合し、同じ PID の可視確認ダイアログを一度検知してから、その消失を検知した直後に `u.inspect(run)` を1回実行する。`w05c-exe-watch-ready` は監視が確認表示を認識した合図であり、製品内部マーカーではない。45秒以内に監視が成立しなければ成功扱いせず、証拠を保持して所有 run を回収する。

```powershell
$watchCode = @'
import json, sys, time
from pathlib import Path
sys.path.insert(0, 'tests')
import release_uat_support as u
run = sys.argv[1]
owner = u.load_run(run)['processes'][0]
deadline = time.monotonic() + 45
seen = False
while time.monotonic() < deadline:
    ident = u.process_identity(owner['pid'])
    if ident is None or not u.same_process(owner, ident) or not ident['alive']:
        raise SystemExit('owner identity lost; preserve evidence and stop')
    shown = any(w['visible'] and w['class'] == u.DIALOG_CLASS for w in u.windows_of(owner['pid']))
    if shown and not seen:
        seen = True
        (Path(run) / 'w05c-exe-watch-ready').write_text('dialog seen', encoding='utf-8')
    if seen and not shown:
        print(json.dumps(u.inspect(run), ensure_ascii=False))
        raise SystemExit(0)
    time.sleep(0.05)
raise SystemExit('dialog transition not observed within 45 seconds')
'@
$watchJob = Start-Job -ArgumentList $watchCode,$run,(Get-Location).Path -ScriptBlock {
  param($code,$ownedRun,$projectRoot)
  Set-Location -LiteralPath $projectRoot
  & .\.venv\Scripts\python.exe -c $code $ownedRun
  if ($LASTEXITCODE -ne 0) { throw "after_no observer failed" }
}
while ($watchJob.State -in @('NotStarted','Running') -and -not (Test-Path -LiteralPath (Join-Path $run 'w05c-exe-watch-ready'))) { Start-Sleep -Milliseconds 50 }
if (-not (Test-Path -LiteralPath (Join-Path $run 'w05c-exe-watch-ready'))) { throw "observer was not armed; do not ask for No" }
```

合図を確認してから利用者に「いいえ」を押してもらい、PageFolio を前景のまま保ってもらう。この段階では**チャットへの返答を求めない**。実行担当は先に `Wait-Job` で自動記録の完了を待ち、出力の `foreground.owned_by=primary` と owner PID が一致することを読み取る。失敗した場合は `after_no` が成立していないため採用しない。成功を伝えた後でのみ、利用者はチャットに切り替えて次の質問へ直接回答する。

```powershell
$null = Wait-Job -Job $watchJob -Timeout 50
if ($watchJob.State -ne 'Completed') { throw "after_no observer did not complete" }
$afterNo = Receive-Job -Job $watchJob | ConvertFrom-Json
if ($null -eq $afterNo -or $afterNo.foreground.owned_by -ne 'primary') { throw "after_no foreground was not the primary EXE" }
```

利用者に次の文面をそのまま示し、画面が残る間に直接回答を受ける。

> 今回の W05c/production-exe の同じ run で、①終了確認が表示された、②自分で「いいえ」を押した、③確認が閉じた、④未保存の編集内容と作業画面が残った、⑤一次の PageFolio 画面だけが残り、二次が別の作業画面を作らなかった、⑥No 後の実前景が一次画面だった、⑦これらを回収前に観察した、の各点を確認できましたか。見えたことを原文で答えてください。

回答の時刻・出所参照・質問原文を保存する。確認できない点があれば採用せず、現状を保存して通常の所有 run 回収へ進む。回答後、まだ回収前に `inspect` を1回実行し、`after_peer` とする。`after_no` と `after_peer` の間に直接回答が存在することが採用条件。`after_peer` の前景はチャット等に移っていても原記録のまま保存し、同 owner の生存/生成時刻と peer 消失を独立に判定する。外部 snapshot はダイアログの表示→消失、同 owner PID/生成時刻、二次の終了と別の可視 window 不在、No 直後の実 foreground を示す。API の許可結果を表示観察の代わりにしない。

```powershell
# after_no は上記監視ジョブが既に記録している
# ここで利用者の観察について直接回答を受け、回答時刻と出所を控える
.venv/Scripts/python.exe tests/release_uat_support.py inspect --run $run
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'tests'); import release_uat_support as u; print(u.snapshot(r'$run', 'before-stop'))"
.venv/Scripts/python.exe tests/release_uat_support.py stop --run $run
```

`stop` は同一性を再照合して所有 run だけを通常終了させ、必要時に所有 handle で終了する。`closed` と `terminated` は終了経過として記録し、その値だけで合否を決めない。`stop` 後に owner が終了し、配布元・元設定/2 prompt/plugins が不変であることを確認する。PID 名での一括 kill、別 PID 操作、追加 peer、製品引数・patch・nonce 注入は行わない。異常時は最初の証拠を残し、再実行しない。`stop` は manifest に `after-stop` snapshot を追記して保存する。最終 manifest の SHA256 とファイル更新時刻を読取記録し、回収完了時刻を確定してから、利用者へ**別のメッセージで**正式採用の可否を尋ねる。回収前の観察回答に含まれる「採用」は最終承認に使わない。

回収後に利用者へ「今回の W05c/production-exe の回収後証拠を正式受入として採用してよいですか。採用する場合は『採用』または『採用してよい』とだけ直接返信してください。採用しない場合や不明な場合は、その旨を自由に回答してください」と尋ねる。helper は前後空白を除いた回答原文が `採用`、`採用。`、`採用してよい`、`採用してよい。` のいずれかと完全一致するときだけ許可する。判断に使う際の trim は保存する原文を変更しない。`不採用`、`採用しない`、保留や質問形は拒否する。

## 回答ファイルと正式採用

採取結果を `.planning/phases/06-release-validation/06-05-evidence/W05c_quit-no_at_production-exe-YYYYMMDDTHHMMSSZ.json` に新規保存する。これは `w05c-exe-v1` 専用で、script の `w05c-v3` と混ぜない。回答が無い間はファイルを作っても `collection_status=machine_collected_pending_answer` のまま正式採用しない。`direct_answer.text` は利用者の観察回答の原文を改変せず、`source_ref` は元のチャットメッセージ等の参照、`captured_at` はその実時刻とする。各 boolean は原文の質問と回答で明示確認された場合だけ true とする。推測で補完しない。`adoption` は最終 inspect・stop・after-stop snapshot・最終 manifest 保存・回収完了時刻より**後**に、別の直接メッセージで利用者が正式受入へ「採用」と明示した場合にだけ記入する。

```json
{
  "schema": "w05c-exe-v1",
  "case": "W05c",
  "row": "W05c/quit-no@production-exe",
  "entry": "production-exe",
  "condition": "quit-no",
  "collection_status": "machine_collected_pending_answer",
  "run": "C:\\Users\\shdwf\\work\\project\\PageFolio\\.planning\\tmp\\release-uat-<32桁run ID>",
  "manifest_sha256": "<回収後のmanifest.jsonのSHA256>",
  "owner_created": "<manifest内の一次PID生成FILETIMEを10進文字列で正確に>",
  "peer_created": "<同じrun内の二次PID生成FILETIMEを10進文字列で正確に>",
  "binary_sha256": "<世代5のEXE hash>",
  "fixture_sha256": "<run/fixtures/edit-three-page.pdf のSHA256>",
  "tree_sha256": "<世代5のtree hash>",
  "input_manifest_sha256": "<世代5の入力manifest hash>",
  "inspections": {
    "before_confirm": {"index": 2, "sha256": "<inspect-002.jsonのSHA256>"},
    "during_confirm": {"index": 3, "sha256": "<inspect-003.jsonのSHA256>"},
    "after_no": {"index": 4, "sha256": "<inspect-004.jsonのSHA256>"},
    "after_peer": {"index": 5, "sha256": "<inspect-005.jsonのSHA256>"}
  },
  "peer_constructed": 0,
  "peer_constructed_basis": "external-no-new-primary-window-and-same-owner",
  "confirm_disappeared_before_collection": true,
  "confirm_disappeared_basis": "direct-user-observation",
  "direct_answer": {
    "source": "user-direct",
    "source_ref": "<元メッセージ参照>",
    "question": "<提示した質問原文>",
    "text": "<利用者の回答原文>",
    "captured_at": "<回答のUTC時刻>",
    "quit_confirm_shown": true,
    "answered_no": true,
    "confirm_disappeared": true,
    "edit_state_kept": true,
    "owner_kept": true,
    "foreground_after": true,
    "observed_before_collection": true
  },
  "adoption": {
    "decision": "採用",
    "approved_by": "利用者",
    "source": "user-direct",
    "source_ref": "<回収後の別メッセージ参照>",
    "text": "採用してよい",
    "approved_at": "<明示承認のUTC時刻>",
    "answer_sha256": "<回答原文のUTF-8 SHA256>"
  },
  "stop_outcome": "closed",
  "stop_observed_at": "<回収後のUTC時刻>",
  "originals_sha256": "<manifest.snapshots[0].originals のJSON.stringify UTF-8 SHA256>"
}
```

`stop_outcome` は実測が `terminated` ならそのまま記入する。inspect 番号は run の実際の連番に合わせる。`owner_created` と `peer_created` は JavaScript の数値へ丸めず、manifest の生 JSON から正確な10進文字列を写す。回答ファイルの `manifest_sha256` と inspect の hash は回収後の原本に対して計算する。`stop_observed_at` は回収完了の実時刻で、最終 manifest の更新時刻以降とする。`adoption.approved_at` はこの時刻を含む全回収時刻より後でなければ拒否される。利用者の観察回答や承認を機械が生成しない。

```powershell
node .planning/phases/06-release-validation/06-05-record-w05c-exe.cjs W05c_quit-no_at_production-exe-YYYYMMDDTHHMMSSZ.json --dry-run
node .planning/phases/06-release-validation/06-05-record-w05c-exe.cjs W05c_quit-no_at_production-exe-YYYYMMDDTHHMMSSZ.json
.venv/Scripts/python.exe tests/release_uat_support.py audit --phase-dir .planning/phases/06-release-validation --require-pass W05c
```

最初の `--dry-run` は全ファイルを変更しない。照合に失敗した場合も全ファイル無変更で終了する。正式実行時だけ、同一 run の原本 manifest、3ページPDF、4枚の inspect を `-raw/` へ新規コピーし、台帳の対象1行とカードの対象1枚を更新する。他行は変更しない。`audit --require-pass W05c` は W05c の3入口が揃ったことの確認であり、G3全体や06-05完了・出荷許可を意味しない。実機の観測が未実施の現時点では、この helper の隔離試験成功を受入 pass に転用しない。

## 実装時の検証記録

2026-11-06: `tests/test_w05c_exe_evidence.py` を `.planning/tmp/w05c-exe-cr04-20261106` の隔離 fixture で実行し、37 passed / 1 warning（PyMuPDF の既知 deprecation）。正常 dry-run、通常/force 終了値、対象行だけの書込、未知・不採用・boolean decision、別 owner、別 EXE hash、確認未消失、直接回答欠落、回収先行、時系列逆転、schema 混同、原本保護差分、別 run、チャット切替後の別 foreground、回収完了前の承認5時点、採用原文の4肯定形と5否定/不明形、保存時の原文不変を検証した。AST parse、`node --check 06-05-record-w05c-exe.cjs` は成功。全体 `ruff check .` は成功、全体 `ruff format . --check` は149ファイル変更不要で成功。手順書のPowerShellコードブロック6個はPowerShell Parserで構文確認した。実 EXE 操作、全件 pytest、build、正式 UAT 受入はこの検証に含めていない。
