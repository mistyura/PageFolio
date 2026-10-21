---
phase: 04-startup-control
plan: "05"
status: checkpoint
task_completed: "04-05-01"
resume_task: "04-05-02"
gate: blocking-human
updated: 2026-10-22
task_commit: 7ea8fb41e2ccb216509e5b3f4a358fb181a5eb7f
plan_head_before: b26ddec8bd056ae66d0ac23788f33894408ed42f
task_head_after: 7ea8fb41e2ccb216509e5b3f4a358fb181a5eb7f
task_commits_measured: 1
task_diff_tokens_chars_div_4: 15722
requirements_completed: []
---

# 04-05 再開用チェックポイント

## CHECKPOINT REACHED

**Type:** human-verify
**Gate:** blocking-human
**Plan:** 04-05
**Progress:** 1/2 tasks complete

## Completed Tasks

| Task | Name | Commit | Files |
|---|---|---|---|
| 1 | 起動経路横断の自動受入と実機確認環境 | `7ea8fb4` | tests/test_startup_windows.py、04-WINDOWS-UAT.md、04-VALIDATION.md、04-05-EVIDENCE.json、04-05-RED.xml |

## Current Task

**Task 2:** Windowsの実操作結果を確認して検証記録を確定する
**Status:** awaiting verification
**Blocked by:** W11は利用者回答「別アカウントがない／切替できない」により準備不能not-run。
新通知の実クリック/DPI/通常・昇格両順、他アプリ入力中の実OS拒否、W01〜05とW12の最終実操作確認も未実施。
**04-05/Phase 4は未完了。自動コマンド成功だけで承認/完了へ進まない。**

## Checkpoint Details

自動受入は完了している。

- 指定局所 **140 passed / 1 warning / 0.61秒**。
- 指定Windows **6 passed / 53 deselected / 1 warning / 22.23秒**。script/module/別配置の一次・二次9組、製品ID版/frozen不変、接続先消失/生成時刻不一致の安全停止を含む。
- 単一process全件 **1603 passed / 1 warning / 212.88秒**。failed/ERROR/skipなし。120秒の時間目標超過は無断除外で隠していない。
- **ruff check / ruff format / AST / git diff --check成功**。整形後コードで全件pytest成功。warningは既存PyMuPDFのByteString非推奨警告のみ。
- 原本3ファイルの存在とSHA-256を各fixture/子bootstrapで照合。不在を維持、pluginsは初回app import前から隔離。
- W07の6.5秒slowreadyは二次expired/15437ms、5秒単一期限・10秒案内・一次復帰0。
- W07の6.5秒busyは単独条件で二次expired/15140ms、backend5000ms、busy前後復帰0/0。
  表示期限10000ms、OS閉鎖処理実値10015ms、表示/閉鎖各前後foreground135134不変。
- busyの並行負荷runは15609msで15.5秒上限を109ms超過した。削除/合格化せず、cross_entry並行条件とともに保存した。
  全試験終了後、コードを変更せず同harnessを**一度だけ単独再測定**し15140msを得た。
  任意負荷時の上限保証を実証したとは主張しない。超過は`04-05-EVIDENCE.json`とUAT表に残る。
- slowready/busy通知窓は閉鎖15秒以上後にIsWindow=false。単独busyでは56532ms後も消失。
  全実測終了後、test_startup_windows.pyを実行するPython process残留 **0**。

全件pytestが成功した試験ファイルのSHA-256:
`D5749E4B163FADD4988B4FD797592AFAD204A1B47077CF27D5C383D20B0C8A57`。
製品コードは`b26ddec`から変更していない。新規依存/pyproject変更/製品テストCLIなし。
版番号・README・開発履歴の同期、実PyInstaller EXE混在試験はPhase 6担当。実API/課金試験も未実施。

## 再開時の自動準備と具体的手順

実行担当が以下を実行する。利用者へコード作成・コマンド調査・CLI実行を依頼しない。
試験窓は現在すべて終了済み。harnessが一時PDF/入力欄/fake OCR/modalを準備し、利用者は入力・クリック・UAC・目視だけ行う。

```powershell
git log -6 --oneline
$uat = .venv/Scripts/python.exe tests/test_startup_windows.py --uat start --case settings | ConvertFrom-Json
.venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $uat.run --entry script
.venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $uat.run
.venv/Scripts/python.exe tests/test_startup_windows.py --uat stop --run $uat.run
```

caseはW01=`normal/zoomed`、W02=`settings/thumb/preview`、W03=`pdf`、W04=`ocr`、
W05=`nested/native-ocr/native-quit`、W06=`preview`、W07=`busy/slowready`。
W07はstartが返ったら直ちにpeerする。所有一次は最大120秒で安全終了する。
nativeケースの人手版は自動クリックしない。利用者がOK/Noを操作してから停止する。
作業状態の実際の同一性/selection、OCR継続、4手Undo/Redoなどの期待はUATの各行に記載済み。

新通知は次の専用可視leaseを使う。

```powershell
$notice = .venv/Scripts/python.exe tests/test_startup_windows.py --uat notice | ConvertFrom-Json
.venv/Scripts/python.exe tests/test_startup_windows.py --uat peer --run $notice.run
.venv/Scripts/python.exe tests/test_startup_windows.py --uat inspect --run $notice.run
```

W09は他processの入力を継続し、実クリックcloseと無操作10秒closeを**別run**で実施する。
100/150/200%は実際のWindows表示設定ごとに新runを準備し、全文・close領域・非活性を確認する。
W10は利用者がUACへ応答し、実行担当が`Start-Process -Verb RunAs -WindowStyle Hidden`で同じpeerを起動する。
medium一次→elevated二次/elevated一次→medium二次でowner/mapping/双方向pipeを記録する。
noticeはownerと同じ`--namespace <nonce>`で一方の権限に可視窓を作り、他方からそのnotice runへpeerして新leaseを確認する。
旧manual-ownerのA4-resource-checkは可視窓がなく、新leaseの合格証拠に使用しない。

W11は既存の別Windows sessionを用意できる環境だけで実施する。現環境では実行しない。
ユーザーを新設したり資格情報を取得せず、名前空間mockを別sessionの実証に置換しない。

W12のExplorer/端末固定名確認は`start --production --case preview`でのみ準備する。
既存ownerならpreflight/一次claimで要求せず中断。peerは接続先PID/生成時刻を毎snapshotで再確認する。
通常pytestで本番固定名をclaimしたり、本番既存ownerへ要求しない。

## 証拠・安全な再開

- 正本: `04-WINDOWS-UAT.md`（全W/D対応・手順・未実施理由）、`04-05-EVIDENCE.json`（機械可読の数値）、`04-VALIDATION.md`（draft）。
- 原生データは`.planning/tmp/pagefolio-uat-*`に残し、コミット済みJSONへ重要数値とrun IDを保存した。
- Task 1をやり直さず`7ea8fb4`の祖先関係と試験hashを確認してTask 2から再開する。
- STATE/ROADMAP/REQUIREMENTS/config/state.jsonは親オーケストレーターの単一書き手。子は編集/stageしなかった。
- 04-05-SUMMARY.mdは**まだ作成しない**。全必須W/A pass→SUMMARYとProgress→validate-phase実走→VALIDATION実結果→単一全件pytest→親のPhase完了→DoD再確認。
- 共有要件5件のComplete・Phase[x]・validatedを先行登録しない。3禁止事項はflagged-unverified、edge5件はunclassified/unresolvedを維持。

## TDD・逸脱・未解決範囲

- 04-05は既に実装された製品挙動へ受入範囲とharnessを追加した。製品コードのGREEN実装はない。
- `04-05-RED.xml`の最初の失敗は新owner roleの未配線によるharness失敗。
  製品未実装を示す正当なRED/RED_EVIDENCE_OKとは主張しない。
- AGENTS.mdのコミット前全件pytest成功を優先し、失敗RED単独commitは作成しなかった。
- 初回busyのraw結果誤記/短縮timerはharnessのみ修正して再測定し、元runを不採用として保持。
- Windows venv launcher PIDと実Python PIDの差を実測し、接続先は公開された実identityで照合した。
- sandboxのpytest一時領域/Tcl/生ログ/Git管理領域の拒否は正規昇格で実行し、試験除外や原本上書きで回避していない。
- Known Stub/無断skip/未実行Task 1 automated verifyなし。追加の未計画network/auth/schema境界なし。
- W11と人手未実施はTask 2の明示停止条件であり、自動試験成功による承認対象外。

## Awaiting

W11を含む全必須実機の観測根拠と承認が揃うまでTask 2は未完了。
利用者の「別session準備不能」は記録済みで、同じ確認を繰り返して承認を求めない。
別sessionを試せる既存環境が用意された時点、または明示的な再計画により前提が変更された場合に再開する。

## Self-Check: PASSED

Task 1成果物5ファイルの実在、`7ea8fb4`がHEADの祖先であること、台帳base/after/1commitを確認。
実diff文字数/4切上げは15722（Task 1 commitまで。停止記録のmetadata commitは含まない）。
stub/禁止パターン検索に該当なし、意図しない削除なし、原本不変、試験process残留0。
