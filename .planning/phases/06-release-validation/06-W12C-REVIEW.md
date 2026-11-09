---
phase: 06-release-validation
reviewed: 2026-11-06T16:47:06Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - .planning/phases/06-release-validation/06-05-w12c-driver.py
  - .planning/phases/06-release-validation/06-05-record-w12c.cjs
  - .planning/phases/06-release-validation/06-W12C-COLLECTION.md
  - tests/test_w12c_evidence.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
  necessity: 0
status: clean
---

# W12c本人起動・実入力の独立コードレビュー

## Summary

W12c専用4ファイルを標準深度で読み、必要な既存W12b provenance、実script入口、release UAT schemaと照合した。driverは本人向けのExplorerショートカット／端末コマンドを準備してから二次完了を待ち、一次PID・生成時刻、foregroundと入力前後のHWNDを外部採取する（`06-05-w12c-driver.py:121-158,275-389`）。HWND一致を文字入力成功と断定せず、回収後の利用者直接回答を別に要求する（`06-W12C-COLLECTION.md:14-24`、helper`:171-186`）。Python行は実scriptのresource-auditを照合し、未改変EXE行は内部APIを取得不能として正式helperが拒否する（helper`:42-43,78-100`）。一次の回収は例外時にも `finally` で先に試みる（driver`:390-415`）。W12aの既存4指摘とW12bの既存1指摘の解消判定は再利用した。

当初のCR-01とWR-01は差分再レビューで解消を確認し、新規指摘はない。W12cの4行は引き続き `not-run`、`release_allowed=false`。実装担当報告の修正後W12c隔離26件、W12b既存26件、全体Ruff/format・AST・Node・担当diff／末尾空白checkの成功を再利用した。こちらではpytest、実機、buildを実施していない。

## Narrative Findings (AI reviewer)

### CR-01 — Python本人起動先の実行体変更を正式採用前に検出できない（修正済み）

**当初分類:** BLOCKER／**現在:** 修正済み  
**File:** `.planning/phases/06-release-validation/06-05-w12c-driver.py:121-145`、`.planning/phases/06-release-validation/06-05-record-w12c.cjs:101-116,129-143`  
**Issue:** Python二次の起動先は `.venv/Scripts/pythonw.exe` または `python.exe` だが、driverは存在とパスだけを記録し、実行体bytes/hashを固定しない。helperも同パスを照合するだけで、Explorer `.lnk` のhashとは異なりPython起動先のbytesを読まない。共通 `source_inputs` は `.py` だけ（`tests/test_startup_windows.py:56-68`）、`collector_inputs` も `.py/.cjs` だけ（`06-05-w12b-driver.py:49-56`）である。したがって準備後に該当実行体を変更して二次を起動し、resource-audit等が揃った場合、異なる起動物でも正式helperが `pass` を記録できる。実行体改変の拒否回帰もない（`tests/test_w12c_evidence.py:299-326`）。  
**Fix:** driverが起動指示前にtargetの実path・非link・SHA256を `launch_route` に固定する。二次観測直後と正式helperで同じ実行体の非link・SHA256一致を要求し、変更時は採用拒否とする。Explorer／端末それぞれでtarget bytes変更を加え、dry-runと書込の全ファイル無変更を確認する。

**2026-11-07再監査:** `06-05-w12c-driver.py:57-77` は開始時に `python.exe` と `pythonw.exe` の非link・path範囲・SHA256を固定する。起動物自身のhashは同`:137-163` で `launch_route` に記録し、本人への起動指示前（`:305-321`）、二次観測後（`:359-363`）、所有一次の回収後（`:426-443`）に再照合する。`06-05-record-w12c.cjs:101-109,147-151` は開始時の両実行体hash、起動物hash、現行bytesを一致要求する。`tests/test_w12c_evidence.py:337-348,372-385` は実行体改変時のdry-run／書込拒否とfixture全bytes不変を確認する。起動後改変の隔離試験（同`:465-532`）では先に所有一次stopを呼ぶ。実GUIでの本人起動は未実施。

### WR-01 — 本人操作手順書が採取provenanceに含まれない（修正済み）

**当初分類:** WARNING／**現在:** 修正済み  
**File:** `.planning/phases/06-release-validation/06-05-w12c-driver.py:55-65`、`.planning/phases/06-release-validation/06-05-record-w12c.cjs:129-143`、`.planning/phases/06-release-validation/06-W12C-COLLECTION.md:6-24`  
**Issue:** 本人が操作する経路、入力タイミング、回答形式を定めるW12c手順書は採取の意味を決めるが、driverが流用する `base.provenance()` の `source_inputs` はPython、`collector_inputs` は `.py/.cjs` に限定される（`06-05-w12b-driver.py:49-75`）。helperもそれらの集合だけを再列挙するため、`06-W12C-COLLECTION.md` を採取後に変更しても同一runとして採用できる。  
**Fix:** 手順書のSHA256をW12c provenanceへ明示保存し、停止後・正式helperで現行bytesと照合する。変更拒否をdry-run／書込の無変更回帰に追加する。

**2026-11-07再監査:** `06-05-w12c-driver.py:57-81` は手順書hashを開始provenanceに追加し、起動前と回収後に照合する（同`:288,305,437-443`）。`06-05-record-w12c.cjs:141-145` は正式採用前の現行bytes一致を要求する。`tests/test_w12c_evidence.py:338-348,465-532` は手順書改変の拒否／無変更と、起動後改変時に所有一次を先にstopする順序を対象に含む。実機の所有PID回収を伴う統合実測ではない。

## 検証境界

- `tests/test_startup_windows.py:3314-3339,3779-3784` は固定namespaceの実script入口で、二次resource-auditにはPID・生成時刻・API戻りを記録する（同`:3054-3066,3104-3124,3160-3166`）。driverのPython二次はこの入口を指す。GUI実測は行っていない。
- driverは20秒準備と38秒待機を期限計算へ含め、期限不足なら二次開始前に回収へ進む（`:241-251,263-274,297-302,394-405`）。停止・例外時の実PID生存を伴う統合実測は今回ない。
- helperは完全行ID、64bit FILETIME、runとpeer fixtureのID、監査raw、本人の回収後観察回答と別の有限肯定承認を照合し、dry-runでは書き込まない（`:17-48,49-100,171-209`）。単体fixtureは実GUIや本人操作の代替ではない。
