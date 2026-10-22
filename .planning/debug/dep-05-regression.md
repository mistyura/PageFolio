---
status: resolved
trigger: "Phase 5 DEP-05-REGRESSIONを解消するため、Windows起動・フォーカステスト6失敗を調査・修正"
created: 2026-10-22
updated: 2026-10-22
goal: find_and_fix
---

## Symptoms

- expected: Windows起動・フォーカスの6件および単一の全件pytestが失敗0・ERROR0・クラッシュなしで成功する。
- actual: Phase 5計画時の全件実行は6 failed, 1623 passed, 2 warnings。
- errors: ready期限超過、expired、focus_correct不成立。
- timeline: 2026-10-22の計画時に記録。直前の環境更新あり。原因は未確定。
- reproduction: `.planning/phases/05-config-notification/05-PLANNING-CHECKS.md` の6テストを専用basetempで再実行後、全件を確認。

## Current Focus

hypothesis: 起動試験が正常な期限切れを不許可にし、focus選択が一時的なtoplevelを記憶した入力先より優先する。
test: 初期化8.5秒遅延・一時的toplevel focusの決定的再現と修正後のWindows実プロセス試験。
expecting: 製品5秒期限を維持し、古い要求で遅れて復帰せず、新しい起動で入力先が復元される。
next_action: DEP-05-REGRESSION解除。次の独立作業は `$gsd-execute-phase 5`。

## Eliminated

## Evidence

- timestamp: 2026-10-22
  checked: 05-PLANNING-CHECKS.md、作業ツリー、既存debug記録
  found: 6失敗の記録あり。既存debugは解決済み。計画・依存更新の未コミット変更が存在。
  implication: 既存変更を保持し、この回帰の独立修復と証拠更新に限定する。Phase 5実装は開始しない。

- timestamp: 2026-10-22
  checked: 計画時の専用basetemp `pf_phase5_plan_20261022` の対象JSON
  found: 8並行起動の一次は20:38:22.335にinitializing、20:38:27.456にready。二次3件のelapsedは5000ms、terminalはexpired。同時起動2件とrelocated一次にはreadyがない。focusの元証跡はboolのみ。
  implication: 初期化は5秒を超え得る。既存expired不許可は製品契約と矛盾する。旧focus失敗の個別イベント順は証跡不足で遡及確定しない。

- timestamp: 2026-10-22
  checked: 修正前6件と単一全件
  found: 対象6件は6 passed / 30.15s。全件は1629 passed, 2 warnings / 230.86s、exit 0。未修正のまま再現しないため、成功だけを修復の根拠にしない。
  implication: 遅延と一時的toplevel focusを決定的に与えて、原因を検証する。

- timestamp: 2026-10-22
  checked: 修正前への回帰条件追加
  found: toplevel_focused=Trueのthumb/preview/entryが3 failed、Falseの3件はpassed。初期化8.5秒遅延は8.24秒でready数0による失敗。
  implication: 製品の入力先選択と試験の待機条件の問題を個別に再現。

- timestamp: 2026-10-22
  checked: 修正後の局所試験
  found: focus単体30 passed / 0.17s。Windows実プロセス24 passed / 118.44s。thumbのcompleted時にimmediate_focus=None、settled_focusは期待canvasと一致した実例あり。
  implication: 同期呼出し直後のfocus_getではTkイベント処理を観測できない。idleで一度だけ観測する修正は、成功まで再試行する免除ではない。

## Environment and Commands

- Windows 11 `10.0.26300` / Python `3.15.1` AMD64 / Tk `9.0` / Tcl `9.0.4`。
- Python: `C:\Users\shdwf\work\project\PageFolio\.venv\Scripts\python.exe`。
- ネイティブ試験は承認済みsandbox外実行。単体focusはsandbox内。製品の5秒期限は変更なし。
- 検証前HEAD: `a49f3042b54709315e6627ae4330b5acf4a80093`。既存requirements.txt更新を含む作業ツリーを使用。依存更新をこの修復commitへ混ぜない。
- 全件・局所いずれも新規basetemp使用。全件ではフィルタ・除外・skip追加なし。

```powershell
# 修正前全件: 1629 passed / 2 warnings / exit 0
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_full_20261022_01"
# 決定的遅延再現: 1 failed / exit 1（修正前）
.venv/Scripts/python.exe -m pytest "tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor[slow]" -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_slow_red_20261022"
# 修正後Windows局所: 24 passed / 1 warning / exit 0
.venv/Scripts/python.exe -m pytest tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor tests/test_startup_windows.py::test_cross_entry_owner_accepts_both_entries_and_other_location tests/test_startup_windows.py::test_focus_restore_real_main_windows -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_fixed_20261022_01"
# 修正後全件（下記Resolutionに最終実測を記録）
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_full_20261022_02"
# 必須Python品質ゲート
.venv/Scripts/ruff.exe format . --config "include = ['*.py', '*.pyi', '*.ipynb']"
.venv/Scripts/ruff.exe check .
.venv/Scripts/python.exe -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"
```

Ruff 0.17.1の既定formatはMarkdownのコード例も対象にし、既存Markdown60件と今回のPython1件を整形対象とした。`--exclude "*.md"`でもMarkdownへ適用され、アクセス拒否も生じた。整形だけの副作用を戻し、CLI `include` でPython範囲を明示。100ファイル変更なし・exit 0、lint/ASTもexit 0。`pyproject.toml`は変更しない。既存計画の履歴コード例をこの回帰修正へ混ぜない。

ローカル実行ログ: `dep-05-full-before.log`、`dep-05-slow-before.log`、`dep-05-targeted.log`、`dep-05-full-after.log`（このファイルと同じディレクトリ、ログはgit管理外）。

## Resolution

root_cause: 初期化8秒の固定待機と正常expiredの不許可という試験の前提誤り。focus選択でtoplevel自身を記憶した子widgetより優先する製品不具合。元のfocus失敗は即時boolのみで、個々のネイティブイベント順序までは遡及確定できない。
fix: 試験bootstrap待機を30秒に分離。expiredの5秒境界・新規起動での復帰・遅延復帰なしを検証。製品focusは生存する子widgetを優先。実測はTk idle時に一回だけ観測し即時値も保存。
verification: 最終単一全件1635 collected / 1635 passed / failed 0 / ERROR 0 / skipped 0、1 warning、239.82秒、exit 0、クラッシュなし。追加6件は一時的toplevel focus 3件・現在の入力先優先1件・Tk最後の入力先1件・遅延起動1件。lint/format/AST成功。
files_changed: pagefolio/startup_focus.py、tests/test_startup_focus.py、tests/test_startup_windows.py、pagefolio/constants.py、README.md、開発履歴.md。版番号v1.9.1へ同期。

## DEP-05-REGRESSION解除証拠

- 修復commit: `8689c2720e38fc2397407e38317687d1952b22f6`（現在ブランチへ適用済み）。
- 全件実行対象は同commitの製品・テスト内容と一致。既存未コミットのrequirements.txtを含む環境で検証し、その更新は独立修復commitへ含めていない。
- 最終ログSHA256: `650FD866F5F16049162C83FDE589CB4421A4903D3A3217C5300433D079427EEA`。
- 検証時のSHA256:

| ファイル | SHA256 |
|---|---|
| pagefolio/startup_focus.py | B9F605201E394FABC75EFD06B6B3CB3F9A4574CE3924FE9565898A1C2FD2B881 |
| tests/test_startup_focus.py | 8573A40B3B97CC4911EC61592B1EA7B7392ADA07DEA097A67E0BFF903B5348D1 |
| tests/test_startup_windows.py | 6D6D1CD52D96ED74F876D14F2A51F7134D00BDE8F960A3C58B48767468DCF014 |
| pagefolio/constants.py | 6A84D64613D5C462EDD35F9B1EA7BD86EE0BB3A4E1BE91B8AA8B5B292C458B10 |
| requirements.txt | 5AFFADBAB19AAC41E06B20142E67DAF1A4326B898D0DE4D34CFDBBFA1B403F74 |

最終warningはPyMuPDFのByteString非推奨警告1件。修正前全件ではTcl interpreter leaked警告も1件発生したが、最終全件では非再現。Tcl内部の警告原因を解決済みとはしない。配布EXE/UAC等のPhase 6人手受入は未実施。Phase 5の計画品質合格とこの前提解除は、Phase 5の実装完了を意味しない。
