---
status: investigating
trigger: "Phase 5 DEP-05-REGRESSION（normal-entry-scriptのcommunicate期限超過を再調査）"
created: 2026-10-22
updated: 2026-10-23
goal: find_and_fix
---

## Symptoms（最初の6失敗・履歴）

- expected: Windows起動・フォーカスの6件および単一の全件pytestが失敗0・ERROR0・クラッシュなしで成功する。
- actual: Phase 5計画時の全件実行は6 failed, 1623 passed, 2 warnings。
- errors: ready期限超過、expired、focus_correct不成立。
- timeline: 2026-10-22の計画時に記録。直前の環境更新あり。原因は未確定。
- reproduction: `.planning/phases/05-config-notification/05-PLANNING-CHECKS.md` の6テストを専用basetempで再実行後、全件を確認。

## Current Focus

hypothesis: 【原因未確定】元失敗(二次result.json保存の約11.3秒後もstdout EOF未達)の残存仮説は3つ。H1=二次(venv launcher→実python)の終了遅延、H2=第三者によるpipe保持、H3=親pytest側のreader thread/GILの停止。H2は静的に可能性が低い(二次は孫を作らず、親にも並行CreateProcessの経路が無い)。どれも約820件の観測で再現していない。
test: 新設の_finish診断(poll値・reader threadの生死と位置・起動後に生まれた生存process一覧とthread状態)と、時限dumpを常時armedにしたtraceback.logで、次の再発時に3仮説を1回で判別する。
expecting: 再発時、poll=None→H1(processが生存。traceback.logにPythonスタックがあればPython側、無ければOS/launcher側)。poll=0かつreader alive=True→H2(起動後に生存するprocess一覧に保持者)。reader aliveでなくTimeoutExpired→H3。
next_action: 単一全件ゲートの結果を確認し、結論(原因未確定・診断強化・依存は未解除)をreportする。

## Eliminated

- hypothesis: 終了時クラッシュ(STATUS_BREAKPOINT等)でWER dump待ちとなり、processが残ってpipeを保持した。
  evidence: WER `Disabled=1`・WerSvc停止。クラッシュしたprocessはWERに保持されず即時終了する。python.exeのApplication Error/Hangイベントも0件。
  timestamp: 2026-10-23
- hypothesis: 二次entry-script自身がプロセス(孫)を生成し、継承したstdout/stderrを保持した。
  evidence: 起動経路(`__main__.py`・`startup_*.py`・`pagefolio.py`)に子process生成が無い。Threadはdaemonのみで、exit hookも無い。
  timestamp: 2026-10-23
- hypothesis: OSのスリープ/電源遷移/時刻変更で失敗窓の約12秒が凍結した。
  evidence: 2026-10-22 21:55〜22:20のSystemログにKernel-Power・Power-Troubleshooter・Time-Service等のイベントが無い。
  timestamp: 2026-10-23
- hypothesis: 機械負荷による起動の遅れ(旧「遅いimport」仮説)が11秒超の遅延を説明する。
  evidence: 二次はresult.jsonを0.78sで保存済み(通常0.57s)。遅れは約1.4倍で、result保存後の11.3秒超を説明できない。CPU飢餓の再現でもresult→EOF差は最大0.29s。
  timestamp: 2026-10-23

## Evidence

- timestamp: 2026-10-23（常時armedの時限dumpが終了処理の停止を捕捉できることの確認）
  checked: scratchpad `arm_check.py`（`dump_traceback_later(2, repeat=True, file=trace)`をarmした関数が戻った後、非daemon threadが残りinterpreter finalizationで待たされる）
  found: 関数のローカル変数`trace`がスコープを外れた後も、`traceback.log`に`threading.py:1720 in _shutdown`（本体）と残存threadのスタックが2秒周期で記録された。
  implication: `_test_scenario_bootstrap`の時限dumpを取り消さない変更により、シナリオ完了後のPython側finalizationの停止はfixtureの`traceback.log`に残る。OS/launcher側の停止(Python外)は捕捉できず、親側の`_stall_report`のthread状態で見る。

- timestamp: 2026-10-23（診断強化後の検証）
  checked: 変更後の`tests/test_startup_windows.py`(`_finish`/`_stall_report`/`_reclaim`、時限dump常時armed、新規2試験)
  found: 新規2試験(終了済み+孫がpipe保持/process生存)と対象`[normal-entry-script]`は3 passed。pipe保持の報告は保持者(孫launcher)のpidと実python・conhostをthread状態付きで列挙し、reader threadの`alive=True`を示した。単一全件は**1637 collected / 1637 passed / failed 0 / ERROR 0 / 1 warning / 263.66s / exit 0**(basetemp `pf_dep05_gate_20261023_01`)。ruff check・ruff format(Python対象)・AST成功。
  implication: 診断強化は既存の合否基準を緩めておらず(失敗すべき状況は失敗のまま、報告だけが判別可能になる)、全件ゲートは通る。ただしこれは元失敗の原因証明ではなく、依存解除の根拠にしない。

- timestamp: 2026-10-23（汚れた親pytest内での繰返し観測）
  checked: `pytest tests/ test_zz_campaign.py`（全1635件に続けて同一pytest process内で二次entry-scriptを30 owner×6=180件観測。親側10msヒートビートで0.3秒超の停止を記録）
  found: 1636 passed / 483.58s / exit 0。180件すべてEOF到達、result→EOF差 最大0.064s、timeout 0、rc非0 0、親ヒートビートの0.3秒超の停止 0件。
  implication: 汚れた親(リークしたlistener thread・Tcl警告を含む)だけでは再現せず、H3(親のGIL/スケジューリング停止)を支持する観測は無い。ただし未再現は反証ではない。

- timestamp: 2026-10-23（機構の決定的再現：終了済みの子+孫がpipe保持）
  checked: scratchpad `pipe_hold_repro.py`（孫が`close_fds=False`でstdout/stderrを継承して60秒/30秒生存。変更前の`_finish`をそのまま呼ぶ）
  found: 変更前の`_finish`は「子process が12秒以内に終了しない: poll=0」と失敗し、しかも失敗処理の`child.kill()`後の無期限`communicate()`が孫の寿命いっぱい(30.17秒)ブロックした。`poll=0`は子が終了済みである証拠なのにメッセージは「終了しない」と誤誘導する。processの終了待ちとpipe EOF待ちを分離した版は約0.6秒で終了を検出し`exited_pipe_held`と分類できた。
  implication: 「harnessの待機がprocess終了ではなくpipe EOFで決まる」構造は決定的に再現できた。元失敗の保持者が実在したことは**未実証**(元失敗時のpoll値・出力は残っていない)。静的解析ではこの経路は可能性が低い。

- timestamp: 2026-10-23（3回目の再調査・静的解析と時系列再構成）
  checked: 元失敗の専用basetemp `pf_phase5_review_20261022_02/test_focus_restore_real_main_w14` の全ファイル時刻（22:08台、+0900）、`gsd-review-pytest.log`のtraceback、`subprocess.py`(3.15.1)の`_communicate`/`_execute_child`、起動経路のソース
  found: (1)時系列は owner spawn 22:08:24.55 → owner ready 29.91 → 二次spawn 30.35 → owner focus-result 31.109 → 二次resource-audit 31.129 → 二次result.json 31.130（spawn後0.78s） → ownerの自動終了(settings保存/resource-audit) 39.89〜39.98 → 12秒期限は約42.4。つまり二次はresult.json以後少なくとも約11.3秒、stdoutのEOFに達していない。(2)tracebackは`subprocess.py:1830`、`_communicate`のstdout reader threadの`is_alive()`判定。EOF未達(または親のreader未完了)を示す。stderr側は評価前で不明。(3)owner起動は通常(単体実測で約3.7s)より遅い約5.4s、二次は通常0.57sに対し0.78s、全件も354s(通常231〜240s)で、当時の機械負荷は通常の約1.4〜1.5倍。極端な飢餓ではない。(4)`pagefolio/startup_*.py`・`__main__.py`・`pagefolio.py`に子process生成は無い(`subprocess`はOCRのTesseract検出とplugin dialogのみ)。Threadはdaemonのlistener workerとI/O reaperのみで、exit hook(`atexit`/`__del__`/`finalize`)も無い。
  implication: 二次が自分で孫を作ってpipeを保持した可能性は静的に否定できる。ただし、二次の終了遅延かpipe保持かは当時の記録(poll値・出力なし)から遡及確定できない。

- timestamp: 2026-10-23（process構成の新事実）
  checked: `.venv\Scripts\python.exe`起動直後のprocess木(CIM)
  found: Popenが保持するpidは`.venv\Scripts\python.exe`(venv launcher)で、その子に実体の`Python315\python.exe`(B)と`conhost.exe`(CREATE_NO_WINDOWの隠しconsole)が存在する。stdout/stderr pipeの書込端はlauncherとBの2process(+継承経路)が保持する。`child.poll()`/`kill()`はlauncherに対するものでBではない。
  implication: 本harnessでは全spawnが「孫を持つ」構造。EOFはlauncherとBの双方の終了が必要。ただし実測ではB終了からlauncher終了・EOFまで0〜数msで、conhostがpipeを保持して遅延させる証拠は無い。

- timestamp: 2026-10-23（WER・電源・OSイベントの切り分け）
  checked: HKLM/HKCU Windows Error Reporting設定、WerSvc、Application/Systemイベントログ(2026-08-01以降のApplication Error/WER/Hang、2026-10-22 21:55〜22:20のSystem)
  found: WER `Disabled=1`、WerSvc `Stopped`。python.exeのApplication Error/Hangイベントは0件(別プロセス5件のみ)。失敗窓のSystemログにKernel-Power/スリープ/時刻変更は無くDCOMとIsolatedUserModeのみ。
  implication: 「終了時クラッシュでWER dump待ちにprocessが残る」仮説はWER無効のため成立しない(Eliminated)。スリープ/電源遷移による凍結も裏付け無し。

- timestamp: 2026-10-23（終了遅延の定量観測）
  checked: scratchpad `campaign.py`/`timeline.py`で二次entry-scriptを実owner(focus-owner-normal)に対して繰り返し実行。result.json→B終了→launcher終了→pipe EOFを2msポーリングで記録
  found: 無負荷600件: result→EOF差 最大0.066s、全体EOF最大1.17s、timeout 0、rc非0 0。CPU飢餓(通常優先20本)10件: 差 最大0.28s。CPU飢餓(通常超優先24本)24件完走: 差 最大0.29s、result最大6.9s。後者の10件timeoutは全件result無し=owner自動終了後に二次が一次化した試験設計上の副作用で、現象ではない。
  implication: 機械のCPU負荷だけでは「result後の11秒超の終了/EOF遅延」を再現できない。ただし元失敗の頻度が約1/600なら無負荷600件でのゼロ件(約37%)は反証にならない。

- timestamp: 2026-10-22（再調査・診断の副作用切り分け）
  checked: dep-05-reopen-diag.log、dep-05-reopen-target.log
  found: stderrへの10秒周期スタック出力を追加した全件はslowケースのfresh起動expiredで1 failed/1634 passed/1 warning/239.90s/exit1。元のnormal-entry-script失敗は再現せず。未読pipeへの大量dumpによる副作用を避け、traceback.logへ分離後の起動・focus対象21件は21 passed/1 warning/99.37s/exit0。
  implication: 診断追加後の新失敗を製品の根因と扱わない。元の失敗に対して親pytest側のfaulthandlerも追加して証拠を取得する。失敗時のstdout/stderrを破棄していた_finishはpoll値とともに保持する。

- timestamp: 2026-10-22（再調査）
  checked: 05-REVIEWS.md最新全件ログ、pf_phase5_review_20261022_02/test_focus_restore_real_main_w14のJSON/ファイル時刻、Python315/Lib/subprocess.py
  found: entry-scriptの_finishで12秒期限超過。二次result.jsonは生成約1秒後に正常結果completed/elapsed172msを記録。ownerのfocus-resultは状態保持・対象・focusすべてtrue。stop未作成でownerは10秒の自動終了。今回は対象単体1 passed/1 warning/4.34s/exit0。
  implication: 遅いimport仮説は元失敗の説明にならない。二次のmain終了後からpipe EOFまでを調査する。旧成功証拠だけで依存を解除しない。

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

## Resolution（8689c27時の過去の解決記録）

root_cause: 初期化8秒の固定待機と正常expiredの不許可という試験の前提誤り。focus選択でtoplevel自身を記憶した子widgetより優先する製品不具合。元のfocus失敗は即時boolのみで、個々のネイティブイベント順序までは遡及確定できない。
fix: 試験bootstrap待機を30秒に分離。expiredの5秒境界・新規起動での復帰・遅延復帰なしを検証。製品focusは生存する子widgetを優先。実測はTk idle時に一回だけ観測し即時値も保存。
verification: 最終単一全件1635 collected / 1635 passed / failed 0 / ERROR 0 / skipped 0、1 warning、239.82秒、exit 0、クラッシュなし。追加6件は一時的toplevel focus 3件・現在の入力先優先1件・Tk最後の入力先1件・遅延起動1件。lint/format/AST成功。
files_changed: pagefolio/startup_focus.py、tests/test_startup_focus.py、tests/test_startup_windows.py、pagefolio/constants.py、README.md、開発履歴.md。版番号v1.9.1へ同期。

## DEP-05-REGRESSION解除証拠（8689c27時の履歴・現在の解除ではない）

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

## 2026-10-22 再調査の到達点（未解決）

- 環境: Windows 11 `10.0.26300` / Python `3.15.1` AMD64 / Tk `9.0`を現在の.venvで確認。ネイティブ試験は制限外、lint/format/ASTはsandbox内。Tclパッチ版は今回再取得していない。
- 検証対象HEAD: `cdcfce8ae2470993f2e56f9fe56ca0044f8585b4`。未コミット差分はtest_startup_windows.pyの診断追加。製品コード・起動期限・終了待機12秒・テスト件数は変更なし。既存requirements.txtと計画の変更は保持。
- 元失敗の発生箇所は二次entry-scriptに対する`communicate`のstdout reader threadのjoin後判定。結果JSONは約1秒で保存済み。旧記録にpoll値と捨てられたstdout/stderrがないため、実process生存と親pipe待機のどちらかは遡及確定できない。
- 診断変更: `_finish`でタイムアウト時poll値・stdout/stderrを報告。子bootstrapの10秒周期スタックを隔離fixtureの`traceback.log`へ保存。これは原因修復ではなく、調査継続用の未コミット診断。
- 最終単一全件: **1635 collected / 1635 passed / failed 0 / ERROR 0 / skipped 0 / 2 warnings / 231.65秒 / exit 0 / クラッシュなし**。親側の12秒スタックはslowケースのbootstrap待機のみ。元失敗は再現しなかった。
- 警告: PyMuPDF ByteString非推奨、および`test_ocr_pipeline.py::TestProducerConsumerMemory::test_in_flight_count_never_exceeds_maxsize`の別スレッドでのTcl interpreter破棄。後者と元のcommunicate期限超過の因果は未証明。
- 対象21件: 21 passed / 1 warning / 99.37秒 / exit 0。診断追加前の対象1件も1 passed / 4.34秒。最初のstderr出力診断で発生した別のslow失敗は上記Evidenceに保持。
- ruff check全体、Python対象ruff format（100 files left unchanged）、pagefolio.py ASTはexit 0。pyproject.toml変更なし。
- **原因未確定・新規修復なしのため依存は未解除。** 成功した全件を修復証拠にすり替えない。Phase 5実装・コミット・版番号更新は行わない。

```powershell
# 対象1件（診断追加前）
.venv/Scripts/python.exe -m pytest 'tests/test_startup_windows.py::test_focus_restore_real_main_windows[normal-entry-script]' -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_reopen_probe_20261022_01"
# 診断stderr出力時の全件: 1 failed / 1634 passed / exit 1
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_reopen_diag_20261022_01"
# ファイルへ診断を分離後の対象21件
.venv/Scripts/python.exe -m pytest tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor tests/test_startup_windows.py::test_focus_restore_real_main_windows -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_reopen_target_20261022_02"
# 最終全件・全試験収集、フィルタ/除外なし（制限外の既存.venv）
.venv/Scripts/python.exe -m pytest -q --tb=short -o faulthandler_timeout=12 --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_reopen_diag_20261022_03"
```

最終ログ: `dep-05-reopen-parent-diag.log`（SHA256 `0DF55D181BADADF4BA86A16B7A207B11AF9251A2B2A684C35529611B537ADCE0`）。検証対象tests/test_startup_windows.py: `B2973DAD475795CB4F7E4B00E280380688CBC3D6F34A0410A72622B4C2239CA4`。requirements.txt: `5AFFADBAB19AAC41E06B20142E67DAF1A4326B898D0DE4D34CFDBBFA1B403F74`。これらログはgit管理外。

## 2026-10-23 3回目の再調査の結論（原因は未確定・診断を強化・依存は未解除）

root_cause: **未確定**。元失敗(`[normal-entry-script]`で二次のresult.json保存後に約11.3秒、stdout EOFへ到達しない)の原因は、次のどれも実証できていない。H1=二次(venv launcher→実python)の終了遅延/ハング、H2=第三者のpipe保持、H3=親pytest側のreader thread/GILの停止。H2は静的解析上の可能性が低く(二次は孫を作らず、親にも並行CreateProcessの経路が無い)、WER dump待ち・電源遷移・負荷による起動遅延は否定した(Eliminated参照)。

観測: 二次entry-scriptを実ownerに対して約820件観測(無負荷600、CPU飢餓34、全件pytestと同一processの汚れた親180、ほか)。result→EOF差は最大0.29s、timeout 0、rc非0 0。元失敗の頻度が1/600程度なら、600件のゼロ件は約37%で起こるため反証にならない。**再現は得られなかった。**

fix: 原因を断定する修復は行っていない。代わりに、次の再発を1回で判別できる診断と、待機の上限化を`tests/test_startup_windows.py`へ入れた(製品コード・起動期限・合否基準は不変)。
- `_finish`: 期限超過時にkillより前に`poll`・reader threadの生死と停止位置・起動後に生まれた生存process(pid/ppid/名前/thread状態別件数)を採取し、「process自体が終了しない」と「processは終了済みだがpipe保持者がいる」を文言で分ける。kill後の`communicate`は`_DRAIN_TIMEOUT`(5秒)で打ち切る(従来は孫の寿命まで無期限)。
- `_reclaim`: 回収の`communicate`も5秒で打ち切り、保持者が残る場合は`RuntimeWarning`で可視化する。
- `_spawn`: 起動時刻`pf_spawned_at`を記録(診断の基準)。`_pipe_popen`へ切り出し。
- `_test_scenario_bootstrap`: 時限dumpを取り消さず常時armed(シナリオ完了後のinterpreter終了処理が止まる場合もfixtureの`traceback.log`にPythonスタックが残る)。
- 新規試験2件: `test_finish_reports_exited_process_whose_pipes_are_held`(孫がpipeを保持→終了済みと分類し保持者pidを特定、決定的)・`test_finish_reports_live_process_as_not_exiting`。

再発時の読み方(失敗メッセージ):
- `process自体が終了しない`(`poll=None`): H1。fixtureの`traceback.log`にPythonスタックがあればPython側(finalization等)、無ければlauncher/OS側。thread状態一覧のWaitReasonも見る。
- `processは終了済みだが…EOFが来ない`(`poll=0`、reader `alive=True`): H2。「起動後に生まれた生存process」の中の保持者を同定する。
- `TimeoutExpired`だがreader threadが`alive=False`: H3(親側の停止)。親のスタック・ヒートビートを調べる。

verification: 単一全件 **1637 collected / 1637 passed / failed 0 / ERROR 0 / 1 warning / 263.66s / exit 0**(`pf_dep05_gate_20261023_01`、フィルタ・除外・skipなし。ログ`dep-05-gate-20261023.log` SHA256 `34C2B11C4A7DF4C9D72C342EE41FB029D100A66CF5360FCD1D37011D4B04D87E`、git管理外)。ruff check・ruff format(Python対象)・AST成功、`pyproject.toml`変更なし。tests/test_startup_windows.py SHA256 `C61CA695A1CDAB0EFC21DE230D2F34A389905F1D0A93660443801C4EE73755BD`、requirements.txt `5AFFADBAB19AAC41E06B20142E67DAF1A4326B898D0DE4D34CFDBBFA1B403F74`(未変更)。
**この成功は修復の証拠ではない。** 元失敗は再現しておらず、原因未確定のためDEP-05-REGRESSIONは解除しない。

files_changed: tests/test_startup_windows.py(診断・待機上限化・試験2件。未コミット)。製品コード・pyproject.toml・requirements.txtは変更なし。

未証明: (1)元失敗の実体がH1/H2/H3のどれか。(2)launcher→実python→conhostの終了順序が極まれに崩れる条件。(3)元失敗時の機械状態(別CLI並行実行など)が影響したか。

依存の扱いの推奨: 解除条件は「原因の確定」または「決定的再現+修復」。現状どちらも無い。Phase 5の実装を進める場合は、単一全件ゲートで同種の失敗が再発した時点で停止し、本診断の出力(上記の読み方)で判別してから次へ進む運用が必要。この判断は呼び出し元/利用者に委ねる。

利用者判断(2026-10-23): **診断強化版を採用してPhase 5へ進む。** `tests/test_startup_windows.py`の診断差分のみを独立commitとし、requirements.txtの依存更新は混ぜない。DEP-05-REGRESSIONは未解除のまま維持し、Phase 5の単一全件ゲートで同種の失敗(`子processが12秒以内に完了しない`)が再発した時点で実装を停止し、失敗文言でH1/H2/H3を判別してから`/gsd-debug continue dep-05-regression`で再開する。本セッションのstatusはinvestigatingのまま保持。

```powershell
# 新規2試験+対象1件
.venv/Scripts/python.exe -m pytest tests/test_startup_windows.py::test_finish_reports_exited_process_whose_pipes_are_held tests/test_startup_windows.py::test_finish_reports_live_process_as_not_exiting "tests/test_startup_windows.py::test_focus_restore_real_main_windows[normal-entry-script]" -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_fin_20261023_01"
# 単一全件ゲート: 1637 passed / exit 0
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_gate_20261023_01"
# 汚れた親内の二次180件観測(scratchpadのtest_zz_campaign.pyを全件の後ろに連結)
pytest tests/ <scratchpad>/test_zz_campaign.py -q --tb=short -p no:cacheprovider --rootdir=. --basetemp="$env:LOCALAPPDATA\Temp\pf_dep05_dbg_camp3_20261023_01"
```
