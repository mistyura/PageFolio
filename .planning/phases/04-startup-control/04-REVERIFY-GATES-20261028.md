---
phase: 04-startup-control
date: 2026-10-28
status: blocked
gate: blocking-human
stopped_at: verify_post_security_gate/nyquist
verification_owner_status: stale
---

# Phase 04 現行入力の再検証停止報告

全6計画にSUMMARYが存在し、未完了計画は0。実装タスクは再実行せず、Phase 06 の依存契約に従って `aggregate_results` → 共有 `verify-phase-goal.md` を再開した。再委任せずインラインで準備・最初のNyquist監査を実施。必須試験失敗により停止し、後続ゲートと最終独立verifierを未完了のまま返す。

## ゲート順序と結果

| ゲート | 設定・今回結果 |
|---|---|
| Nyquist / validate-phase | 有効。State A。全13タスクと5要件の既存対応、新F1試験を照合。現行全件で1件失敗、compliant=falseへ戻し停止 |
| Security / secure-phase | 有効、既存ASVS L1/登録済み脅威22件/未解決high0。今回の正式再監査は前段停止のため未完了 |
| UI / ui-review | 有効。既存partial・visual capture未実施・Phase06移管を保持。今回の再監査未完了 |
| Code review / disposition | 有効、standard。準備時にF1差分・新試験を読んだが正式完了扱いにしない。CR-01 resolved/WR-01 deferredの旧処置を維持 |
| TDD execute:post gate | 有効hookなし、TDD_MODE=false |
| Gap closure parent artifacts | init manifestで除外 |
| Regression | init manifestで有効。Nyquist失敗により当該ステップへ未到達。現行全件は途中停止なので既存回帰全件合格の証拠にはならない |
| 独立 verifier / fingerprint | 未実施。親から独立gsd-verifierへ委任する前に失敗の扱いを解決する必要あり。古いVERIFICATIONへ新digestだけを差し替えない |

## 初回証拠

採取器: `04-REVERIFY-20261028.cjs`。Pythonソース・試験・設定113ファイルを実行前後でSHA256照合し、新規repo外basetempを使用。`-x` は最初の失敗で止めるためで、成功時の収集対象を除外しない。採取器以外の製品・試験変更なし。

1. sandbox: `2026-10-28T00:22:01.961Z`〜`00:22:03.907Z`、最初のTk fixtureで `Cannot find a usable init.tcl`。環境資源到達エラー。証拠は `04-reverify-20261028/` 直下、ログSHA256 `c419d33b34cda7d2a8794aa10977b61cfe3ba70424dac012b24165a24c112749`。
2. native（require_escalated 1回）: `2026-10-28T00:25:02.117Z`〜`00:27:28.371Z`。**1810 passed / 1 failed / 1 warning / 144.87秒**、終了値1。証拠は `04-reverify-20261028/native/`、ログSHA256 `8fd685d2e2d9c31e28dfe3e38c99cfc730af8273067115737adff530f73aec07`。

native実行コマンド:

```
.venv/Scripts/python.exe -m pytest -q -x --basetemp=C:\Users\shdwf\AppData\Local\Temp\pf04-reverify-3a9071d0-3f30-4a48-8f80-e95fef4cb428
```

環境: Python3.15.2 / pytest9.1.1 / Windows11 10.0.26300 / Tcl9.0・Tk9.0。環境記録のSHA256は `574d41cd3f6e3c4d440e790319db9db2d8a6dd2531ffccd4cea63be8b97a6bcf`。前後入力manifestのSHA256は両方 `2c75948a9b85fae8f1d355bc14a5f97b96e31aeffbf5b288ac3055b98f3a6850`。実行中の入力変更0。

失敗位置: `tests/test_startup_wake.py:216`、`test_native_tcl_getmessage_stall_recovers_with_product_wake[True]` の `foreground_unchanged=False`。直前の `removed == 1` と `posted > 0` は通過。後続のworker停止・400ms回復assertは未到達。子JSONは成功標準出力を親試験が内部捕捉する実装で、失敗ログには当該False以外の生データを出していない。値や前景変化の原因を推測しない。

子プロセスは `tests/startup_wake_child.py`。このhelperは `result.json`・`traceback.log`・独立stdoutログを作成せず、集計JSONを標準出力へ出すだけである。呼出側試験の `result.stdout` に内部捕捉され、前景assertにその値を渡していないため、今回の永続証拠に子の完全JSONは残っていない。前景のbefore/after HWNDはhelper内の局所変数のみで、PID/window/titleも記録されない。したがってそれらの値を取得済みとして報告できない。保存済みtracebackの正確な場所は `.planning/phases/04-startup-control/04-reverify-20261028/native/pytest-full.txt` のFAILURES節（31行目以降）で、`run.json` は終了値・環境・入力/logのハッシュを記録する。新たな値を得るための再走はしていない。

再走・試験緩和・製品修正をせず停止した。既存F1成功ログはmanifest欠落のため今回の現行入力合格として再利用していない。利用者の2026-10-28通常操作確認は、Phase06の正式受入とは分けて保持する。

## 引継ぎ

今回変更した範囲は `04-VALIDATION.md`、本報告、採取器と今回専用証拠のみ。旧 `04-VERIFICATION.md` は stale のまま。STATE/ROADMAP/要件台帳/Phase06証拠/製品/tests/AGENTS.md/pyproject.toml は編集していない。コミットなし。

停止後の読み取り自己確認: 現行113入力とnative実行前manifestの不一致0、ログhashとrun.json記載値の一致、前manifest hashの一致を確認。専用CLI `query verification.status .planning/phases/04-startup-control` は `status=stale / route=execute-phase`、変更被覆は `pagefolio/__main__.py` と `pagefolio/startup_win32.py`。最終fingerprint再生成は未実施で、失敗したゲートを新指紋で隠していない。

親はこの初回失敗を新規の未確定事象として扱い、受入停止条件に従って次の調査・対応範囲を確定する。原因修復前にPhase04をpassedへ昇格せず、Phase06実EXEのbuild/受入を再開しない。DEP-05・owner_missing・通知前景不一致・Tcl既知症状・WR-01の既存未解決記録を、本件またはF1の解決と混同しない。
