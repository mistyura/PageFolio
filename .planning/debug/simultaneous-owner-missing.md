---
status: investigating
trigger: "$gsd-debug で独立調査して / restart"
created: 2026-10-23
updated: 2026-10-23T12:03:35Z
---

## Current Focus

hypothesis: 原因未確定。初回の一次はready約0.4秒後に通常終了したが、終了要求の呼出元が当時記録されていない。利用者は手動終了を否定した。
test: 再発時に一次fixtureのexit-audit.jsonlとresource-audit/result/tracebackを照合する。未調整の同条件試験を追加反復しない。
expecting: stop_pollならstop/stop-allの生成元、callitならwatchdog、Tk __call__直下ならWM/ボタン要求を切り分けられる。quit記録がなければmainloopの直接終了経路を調べる。
next_action: Phase 5停止を維持。診断付き再発証拠または追加の調査仮説を得たら同じdebugを継続する。原因修復・条件付き再開のいずれも今回確認していない。

## Symptoms

expected: 同時起動は編集画面1つに収束し、fresh二次起動も同じ一次へ復帰要求できる。
actual: test_simultaneous_real_processes_construct_one_editor[2]のfresh二次がowner_missingでexit 1。
errors: AssertionError: 接続先guardが要求を中断した。guard_blocked=owner_missing、owner_result=acquired。
timeline: 05-02-01の保存・終了制御変更後の初回全件で発生。前回05-01全件1660 passed。変更との因果は未証明。
reproduction: 既存.venvの単一全件pytest、専用basetemp pf_0502_task1_20261023。1674 passed/1 failed、252.25秒。

## Evidence

- timestamp: 2026-10-23 診断付き全件と上限10回の対象試験
  checked: simultaneous-owner-missing-evidence/full-01.txt、campaign.txt、専用basetemp pf_owner_missing_full_01
  found: 全件1675 passed / 0 failed / 0 ERROR / 2 warnings / 242.80秒 / exit 0。上限10回の[2]は10/10成功（各3.84〜4.33秒）。全件のsimultaneous 3ケースはexit-auditにstop_poll→_quit、stop_all=trueを記録。初回失敗は再現しなかった。
  implication: 診断の出力を確認したが、初回の原因修復の証拠は得られていない。警告はPyMuPDF ByteString非推奨とtest_ocr_engine.pyのTcl interpreter別thread破棄で、今回失敗との因果は不明。

- timestamp: 2026-10-23 独立調査
  checked: 利用者回答、初回の隔離settings.json、tests/test_startup_windows.pyの終了経路
  found: 利用者はテスト中に閉じていない。初回一次の設定には終了時に保存するwindow_geometry/edit_mode/sashがあり、_quit経由の可能性が高い。stop-allはfresh二次の検証後にだけ作られる。子プロセスは別fixtureと独立したTkを使う。
  implication: 手動終了を原因と断定できない。正常終了要求の呼出元を捕捉するため、simultaneous系のTracedApp._quitだけにexit-audit.jsonlを追加した。製品コードと終了期限は変更していない。

- timestamp: 2026-10-23 診断付き単体
  checked: owner-missing-probe-01.log、専用basetemp pf_owner_missing_probe_01
  found: 対象[2]は1 passed / 1 warning / 4.48秒 / exit 0。再現なし。
  implication: 単体成功で原因解決とは扱わず、初回と同じ全件の前後関係を確認する。

- timestamp: 2026-10-23 初回全件
  checked: .planning/phases/05-config-notification/05-02-task1-failure（manifest.jsonで原本とのSHA256一致）
  found: 一次constructed=1/restored=1/result=primary/elapsed=3438。ready_tick-started_tick=3031。後続二次はowner_missing。通常の一次watchdogはApp構築後10000msなので単純な期限到達では説明できない。
  implication: 一次は例外終了せずmainloopを抜けている。元のDEP-05 communicate timeoutとは異なる失敗として調査する。

## Eliminated

- hypothesis: 利用者が試験ウィンドウを閉じた。
  evidence: 利用者回答「閉じていない」。外部ソフトやOSからの終了要求までは検証できていない。
- hypothesis: 通常の試験watchdogが予定どおり10秒経過して終了した。
  evidence: 初回一次のelapsed=3438msはApp構築後10000msの予定時刻より短い。時計/タイマー異常の有無は未確定。

## Resolution

root_cause: 未確定。初回の呼出stack欠落により、どの終了要求が一次を閉じたかを遡って実証できない。
fix: 製品修復なし。simultaneous系TracedApp._quitにtick/monotonic/stop/stop_all/呼出stackを専用JSONLへ記録する診断を追加。期限・合否条件・guardは不変。
verification: 対象1件+上限10回成功、単一全件1675 passed/2 warnings/242.80秒/exit 0。全体Ruff check、Python対象format（101 files unchanged）、再check、pagefolio.py AST、diff --check成功。Phase 5の既存4ファイルのhashは初回失敗時から一致。
files_changed: tests/test_startup_windows.py（24行の診断追加）、本debug記録と証拠コピー。STATE/state.json/05-02-CHECKPOINTは未解決の現況を追記し、先行差分とともに未コミットで保持する。
disposition: unresolved。resolvedへ移動しない。DEP-05-REGRESSIONも未解除。Phase 5の05-02-01は未完了、Phase実装の再開・コミットは行わない。

## 実行commandと証拠hash

```powershell
.venv/Scripts/python.exe -m pytest 'tests/test_startup_windows.py::test_simultaneous_real_processes_construct_one_editor[2]' -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_owner_missing_probe_01"
.venv/Scripts/python.exe -m pytest -q --tb=short --basetemp="$env:LOCALAPPDATA\Temp\pf_owner_missing_full_01"
# 上限10回: 同じ[2]をpf_owner_missing_trial_1〜10の専用basetempで実行。失敗時打切り。
```

Windows通常権限、既存.venv Python 3.15.1。依存更新なし。全件のフィルタ/除外/skipなし。

| 対象 | SHA256 |
|---|---|
| tests/test_startup_windows.py | DC34E678D69EEA86EE53E9399BB3EEC57AC5C3EB08C8ED36998A74A4CDE8ECB4 |
| full-01.txt（元logと同一） | 002F4802E5AD78608CF641A49FDD06996BA22A6E524A2195394DD6064459279E |
| campaign.txt（元logと同一） | 725EA41A9F03CB56AE66A54CC077F7B0997B45567AF0887F733DF68F2148011D |

元の失敗証拠は05-02-task1-failure/と05-02-task1-full.logを保持。成功ログで置換しない。
