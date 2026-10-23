---
phase: 05-config-notification
plan: "03"
subsystem: configuration
tags: [settings, tkinter, toast, pytest, ast]
requires:
  - phase: 05-02
    provides: bool保存ownerとFIFO通知・モーダル中の可視時間保護
provides:
  - 全10操作群からApp保存ownerへ至る保存失敗通知とメモリ保持
  - プラグインの変更保存と開閉・無変更再検出の非保存
  - ネストLLMの単一保存ownerと内側閉鎖後の外側モーダル維持
  - 低層保存callerのalias・Attribute・再exportを含むAST監査
affects: [05-04, 06-release-validation]
actuals:
  tokens: 25682
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [App保存owner, 明示保存意図, 内側Destroy時の外側grab復元]
key-files:
  created:
    - .planning/phases/05-config-notification/05-03-dispatcher.py
    - .planning/phases/05-config-notification/05-03-deferred-items.md
  modified:
    - pagefolio/app.py
    - pagefolio/dialogs/plugin.py
    - pagefolio/dialogs/settings.py
    - pagefolio/ocr_dialog.py
    - pagefolio/dialogs/shortcuts.py
    - pagefolio/redact_ops.py
    - pagefolio/viewer.py
    - tests/test_config_notification.py
    - tests/test_provider_ui.py
    - tests/test_ocr.py
    - tests/test_pagination.py
key-decisions:
  - plugin closeと無変更rescanは保存せず、変更だけpersist=Trueを渡す
  - ネストLLMは専用callback、次にApp ownerだけへ委譲し、ownerなしstubはFalse
  - 内側LLMのApplyとCancelのどちらでも生存する外側Settings/OCRのgrabを復元する
  - 起動3問題と新しいTcl解放警告の原因は未確定のまま保持し、成功回数で解決扱いにしない
patterns-established:
  - UI値・binding・再描画は保存失敗でも維持し、通知は実_persist_settingsが一元管理する
requirements-completed: []
requirements-addressed: [V110-CFG-02, V110-CFG-03, V110-CFG-04]
coverage:
  - id: D1
    description: plugin非変更操作の原本保護と全App保存元の失敗通知
    verification:
      - kind: integration
        ref: tests/test_config_notification.py#TestAppSaveOrigins
        status: pass
    human_judgment: false
  - id: D2
    description: LLM一操作一保存・外側Cancel境界・セッションキーとモーダル維持
    verification:
      - kind: integration
        ref: tests/test_config_notification.py#TestLlmSaveOrigins
        status: pass
      - kind: integration
        ref: tests/test_provider_ui.py + tests/test_ocr.py
        status: pass
    human_judgment: false
  - id: D3
    description: ツール4入口の失敗保持と低層保存callerの非空厳密棚卸し
    verification:
      - kind: integration
        ref: tests/test_config_notification.py#TestToolSaveOrigins + TestSaveOriginCoverage + tests/test_pagination.py
        status: pass
    human_judgment: false
  - id: D4
    description: 通知可視性と実Windows操作感の人手受入
    verification: []
    human_judgment: true
    rationale: 05-04とPhase 6の人手受入は未実施であり自動試験で代替しない
commits: 3
plan_head_before: 4b9310d11a69f22484b0887b085f6ec586393444
plan_head_after: 9db68b8cb0d4910995b50f0264f865b1ddf4ce1e
duration: 58min
completed: 2026-10-24
status: complete
---

# Phase 05 Plan 03: 全設定保存元の通知統合 Summary

全10操作群をApp保存ownerへ揃え、プラグイン無変更操作の保存を止め、ネストLLMの二重保存を解消した。保存失敗でもメモリ・binding・OCR状態・再描画を保持する。

## Performance

- 記録開始: 2026-10-23T14:42:30Z。集計: 2026-10-23T15:40:10Z。
- 実装11ファイル、3タスク、台帳基点から実測3コミット。
- actuals.tokensは実装境界の`git diff --no-ext-diff 4b9310d..9db68b8 -- pagefolio tests`の102725文字を4で割り切り上げた25682。harness使用量ではない。viewer.pyの改行正規化も含む。

## Accomplishments

- `_toggle_lang`、`_apply_llm_settings_live`、変更を伴う`_reload_plugins(persist=True)`が実`_persist_settings`へ到達する。LLM適用は保存boolを返し、失敗時もOCR/バッチ状態を再評価する。
- PluginDialogのtoggleは一回保存、close/WM_DELETE_WINDOWは保存しない。rescanはdisabled IDsの前後差がある場合だけ保存する。同値の一般Apply/LLM Applyによる明示再試行は維持する。
- SettingsDialogはLLM部分だけを専用callbackまたはApp ownerへ渡す。外側の未適用theme等をディスクへ流さず、外側CancelでもLLM値はAppへ残る。ownerなしstubはメモリ更新だけでFalse、一般callbackへ代替委譲しない。
- OCRDialog、ショートカット、モザイク、サムネイル倍率/件数もApp保存ownerを使う。保存失敗時にもprovider生成・prompt同期・キー参照・binding・再描画が続く。
- 実Tkで内側LLM破棄後の外側grab消失を検出し、Settings/OCRで復元する。内側Apply/Cancelの4実Tkケースとfake clockで、外側を閉じるまで通知が消化されないことを固定した。
- AST監査はName/Attribute/alias/相対import/star importと`pagefolio.__init__._EXPORTS`による再exportを解決し、同梱pluginsも検査する。低層保存の直接callerは`PDFEditorApp._persist_settings`の1箇所だけで、空集合は不合格。

## Task Commits

1. **05-03-01 Appとプラグインの保存意図** — `9a22a2c3efc198aeb47d9191a77a5ec472a95bce`
2. **05-03-02 LLM保存ownerと外側モーダル保護** — `2e6ddcf0fc6e216df20f156635b8584518640723`
3. **05-03-03 ツール保存・ページネーション・caller監査** — `9db68b8cb0d4910995b50f0264f865b1ddf4ce1e`

各commitは固定root/feature/v1.10.0と非保護ブランチを確認し、通常hooks・明示path限定で作成した。意図しないファイル削除なし。既存ROADMAPのindex blob `9b9f86ba59fe99666e128faf5931216e5bc19494`を保持する。

## Verification

| 検証 | 結果 | 証拠 |
|---|---|---|
| Task 1: `pytest -q tests/test_config_notification.py::TestAppSaveOrigins` | 24 passed / 1 warning / 2.70秒 / exit 0 | `05-03-task1-targeted-confirmed/` |
| Task 1 + wheel既存回帰 | 26 passed / 1 warning / 3.36秒 / exit 0 | `05-03-task1-regression-fixed/` |
| Task 1 単一全件 | 1718 passed / 1 warning / 269.82秒 / exit 0 | `05-03-task1-full-owner-fixed/` |
| Task 2: `pytest -q tests/test_config_notification.py::TestLlmSaveOrigins tests/test_provider_ui.py tests/test_ocr.py` | 428 passed / 1 warning / 2.21秒 / exit 0 | `05-03-task2-targeted-fixed/` |
| Task 2 単一全件 | 1745 passed / 1 warning / 266.95秒 / exit 0 | `05-03-task2-full/` |
| Task 3: `pytest -q tests/test_config_notification.py::TestToolSaveOrigins tests/test_config_notification.py::TestSaveOriginCoverage tests/test_pagination.py` | 117 passed / 1 warning / 0.74秒 / exit 0 | tool実出力。REDは`05-03-task3-red.xml/json` |
| Task 3 最終単一全件 | 1778 passed / 2 warnings / 276.02秒 / exit 0 | `05-03-task3-full/` |

- 各全件は通常Windows・プロジェクト`.venv`、非表示pythonw→固定`05-02-verify.py`による`python.exe -m pytest -x -q --tb=short --basetemp=<専用Temp>`。全件ではselectorなし、除外・skip追加・期限延長なし。`-x`は最初の失敗を保持するためで、成功時は全件実行した。各status.jsonに実commandがある。
- 全体`ruff check .`→`ruff format . --config "include = ['*.py', '*.pyi', '*.ipynb']"`→check→`pagefolio.py`のAST→`git diff --check`が最終exit 0。105 Pythonファイルはunchanged。`pyproject.toml`は編集していない。
- 3成功全件は各423診断をコピーし、原本/コピー/manifestのSHA256一致をcommit前に確認した。各入力104ファイルのhashも対応する全件と一致。raw診断はローカル保持し、各`.gitignore`はrawだけを除外してmanifestを追跡する。
- 一般設定・言語・plugin・ネストLLM・OCR内LLM・shortcuts・mosaic・thumb_zoom・page_size・終了保存の10操作群が05-01〜03の実handler試験へ対応する。移行前の11低層call site数とは区別する。

## TDD Notes

3タスクとも予定のassert失敗を実JUnitで記録し、`check tdd-red-evidence`の`RED_EVIDENCE_OK`と意味確認を終えてから製品実装した。

- Task 1: language保存失敗後の通知期待1に対して0。
- Task 2: ネストApplyの低層保存期待1回に対して2回。
- Task 3: 実モザイクhandlerの保存失敗後の通知期待1に対して0。
- `05-03-task{1,2,3}-red.xml/json`にcommand/exit/期待/実測/semanticAssessmentを保持。fixture・collection・import障害をRED根拠にしていない。
- plan type=execute、workflow.tdd_mode=false。AGENTSのコミット前pytest成功条件に従い、RED単独commitは作らず、GREEN全件成功後にタスク単位でcommitした。

## Deviations from Plan

1. **[Rule 3 - Blocking] 既存stub移行の順序**: Task 1でApp LLM保存ownerを変更すると、Task 2予定のprovider_ui最小stubに`_persist_settings`がなく全件が1179 passed/1 failedになった。この4箇所の実owner束縛だけをTask 1へ前倒しした。既存assertは維持。最終全件1718 passedで確認。commit `9a22a2c`。
2. **[Rule 1 - Bug] plugin無変更rescan互換**: 初回全件950 passed/1 failedはwheel試験のFakeAppがpersist引数を受けないTypeError。無変更は既定`_reload_plugins()`、変更だけpersist=Trueに分岐し、既存wheel試験を変更せず26件局所と全件で確認。commit `9a22a2c`。
3. **[Rule 2 - Missing Critical] 外側modal復元**: 実Tkで内側LLM破棄後にSettingsのgrabがNoneとなり、外側閉鎖前の通知表示を防げなかった。内側自身のDestroyだけで生存する外側Settings/OCRのgrabを復元し、Apply/Cancel4ケース成功。commit `2e6ddcf`。
4. **[Rule 3 - Blocking] 検証起動環境**: Terminal前景のため開始前preflightが止まった結果を保存。同条件反復・focus操作はせず、親の許可でhidden launcher、後に固定runner専用dispatcherを使用した。dispatcherはpath/selectorを検査し任意commandを受け付けない。既存30秒待機・非console前景2秒安定・各試験期限は変更していない。結果ファイルのjob誤認を修正し、既済jobを再実行しない再起動後に継続。終了時status=stopped、残存プロセスなし。
5. **[Rule 3 - Blocking] 静的検証**: sandboxの全体format --checkは権限warning後Ruff panicとなったため、所定の通常環境で検証し成功した。viewer.pyの既存CRLFは変更行でgit空白エラーになったため、この担当fileをLFへ正規化。意味差分は共通保存への2入口移行だけ。commit `9db68b8`。

Task 1初回局所のmock戻り値回数不足は11 passed/1 failedとして保持し、テストを補完した。Task 2の実Tk初回grab失敗も保持する。成功させるための既存assert削除・警告抑止・除外はしていない。

## Remaining Work

- `owner_missing`、通知前景不一致、DEP-05は未解決。今回の成功は原因修復・出荷許可ではない。同種失敗の再発時は実装・後続・commitを停止し、最初の失敗と診断を保持する承認条件を維持する。
- 最終全件の追加RuntimeWarning: `test_ocr_engine.py::TestOCRRunEngineE2E::test_on_success_exception_still_reaches_on_complete`で別スレッドによるTcl interpreter解放を観測した。原因・新規実Tk試験との因果は未確定。`05-03-deferred-items.md`にopen記録。失敗/ERROR/クラッシュなし、同条件反復や推定修復なし。
- 05-04の複合受入と人手UATは未実施。`requirements.ready-ids`はCFG-02/03/04を全てblockedと返したため、要件完了を先取りしない。版番号・README・開発履歴の同期は承認済みPhase 6担当。
- 共有STATE/state.json/ROADMAP/REQUIREMENTS更新は逐次オーケストレータ担当として引き継ぐ。既存requirements/startup/debug/開発履歴の差分は巻き込んでいない。
- 新しい製品stub・未申告のnetwork/auth/schema信頼境界は検出しなかった。viewerのplaceholderは既存の遅延サムネイル描画部品であり未実装stubではない。

## Self-Check: PASSED

実装11ファイルと全検証証拠が存在し、3実装commitはHEAD祖先。保存台帳の基点/終点から実測3commitで一致する。evaluation-scopeは同番号の旧マイルストーンも返すため、当計画の実測境界は上記ledger/HEADに限定した。最終全件後の製品ソース変更なし。dispatcher停止と診断hash照合済み。
