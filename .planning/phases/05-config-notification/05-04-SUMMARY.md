---
phase: 05-config-notification
plan: "04"
subsystem: testing
tags: [settings, tkinter, acceptance, isolation, pytest]
requires:
  - phase: 05-03
    provides: 全保存元のApp owner統合と通知モーダル保護
provides:
  - 私有TemporaryDirectoryで実Appの4障害を再現する恒久helper
  - 読込失敗から明示失敗・再構築・回復・終了までの複合自動受入
  - 実App操作パネルとH01〜H12の具体的人手手順
  - 最新全件1789件と実コマンド・環境・入力hashの証拠
affects: [05-human-uat, 06-release-validation]
tech-stack:
  added: []
  patterns: [import前の解決先隔離, default-root退避と所有資源の逆順解放, 自動実測と人手未実施の分離]
key-files:
  created:
    - tests/config_notice_support.py
    - .planning/phases/05-config-notification/05-NOTICE-HARNESS.py
    - .planning/phases/05-config-notification/05-UAT.md
    - .planning/phases/05-config-notification/05-EVIDENCE.json
    - .planning/phases/05-config-notification/05-04-dispatcher.py
  modified:
    - tests/test_config_notification.py
key-decisions:
  - 実利用設定/PDF/プロンプト/pluginsは使用せず、原本の存在/相対名/SHA256を前後照合する
  - 読取不能は実ACLを変更せず隔離設定のopenだけへ障害注入する
  - 全件成功と起動症状の原因修復・出荷承認を区別し再発時停止を維持する
  - 人手H01〜H12が未実施のため05-04-02を完了扱いにしない
requirements-completed: []
requirements-addressed: [V110-CFG-01, V110-CFG-02, V110-CFG-03, V110-CFG-04]
coverage:
  - id: D1
    description: 実App複合操作と4障害の隔離・原本保護
    verification:
      - kind: integration
        ref: tests/test_config_notification.py#TestConfigAcceptance + TestScenarioIsolation
        status: pass
    human_judgment: false
  - id: D2
    description: PDF保存/印刷retryとDocument同一性の既存回帰
    verification:
      - kind: integration
        ref: tests/test_toast.py + tests/test_pdf_ops.py
        status: pass
    human_judgment: false
  - id: D3
    description: 実Windowsでの文言・入力先・編集継続・可視時間
    verification: []
    human_judgment: true
    rationale: 利用者目視が未実施であり自動focus試験を代用しない
actuals:
  tokens: 48455
  tasks: 1
  commits: 1
commits: 1
plan_head_before: 8c61ea8d0bce0c84ace3d0a68cf1ecd83c7b6a81
plan_head_after: f51ecb83645363f5bbc3bc1e3b47064f53882df7
duration: 23min
completed: 2026-10-24
status: halted
---

# Phase 05 Plan 04: 設定通知の複合受入と隔離確認環境 Summary

実Appで読込障害・連続保存失敗・再構築・回復・終了を通し、実利用原本を保護する恒久helperと目視用操作パネルを用意した。人手判定前のため計画は1/2タスクで停止する。

## Task Commits

1. **05-04-01 複合自動受入と隔離人手環境** — `f51ecb83645363f5bbc3bc1e3b47064f53882df7`（test）。通常hooks、固定root/feature/v1.10.0、非保護ブランチ、path限定。意図しない削除なし。
2. **05-04-02 説明と最終ゲート** — 人手確認待ち。`docs/CONFIGURATION.md`、`開発履歴.md`のPhase5専用8行、`05-VALIDATION.md`の実測表を準備済みだが、このタスクは未コミット・未完了。

共有STATE/state.json/ROADMAP/REQUIREMENTSは親の所有で変更していない。ROADMAPの既存staged blob `9b9f86ba59fe99666e128faf5931216e5bc19494`を保持する。WINDOWSには必須の未実施人手確認entry3を追加し、親へ限定commitを依頼した。

## Accomplishments

- `create_isolated_app`はApp import/初期化前にsettings/base/plugins解決を私有一時領域へ差し替える。設定・2実prompt・実pluginsの存在/相対名/hashは前後一致し、実plugin load0を確認する。書込障害は隔離設定のopen、差替え障害は隔離設定宛てreplaceに限定する。
- closeは所有callback/Toast停止→Undo解放→Document close→root destroy→patch/一時領域解放。初期化途中例外・終了No・製品終了後も解放する。別Tkのdefault rootを生成前に退避し、画像が別interpreterへ登録される競合を防いだ。
- 実Document/Undo/Redoのidentity、選択、回転→Undo→Redo、破損原本bytes、現在言語、通知event_id・残6秒、明示成功時の再読込を同時に検証する。
- D-19の確認No→初回失敗→確認No→次回Yes、明示成功flag解除後の再失敗、D-20の権限回復後も同セッション保存禁止・無通知終了・正常再起動、D-21の100件FIFO完走と前/途中/ネストmodal・PDF/印刷Toast割込みを固定した。
- 恒久pytestはtests内helperだけをimportし、planning harnessへ依存しない。harnessは`pagefolio/app.py`を持つ祖先を探索する薄い開発入口で、実App/実Toastとメモリ内PDFを使う。製品入口・配布物・OCR実API・起動排他は変更していない。

## Verification

| 検証 | 実測 | 証拠 |
|---|---|---|
| 最終局所 `pytest tests/test_config_notification.py tests/test_toast.py tests/test_pdf_ops.py -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_0504_targeted4` | 280 passed / 1 warning / 11.30秒 / exit0 | 05-EVIDENCE（実tool結果から記録） |
| 最終単一全件 `python.exe -m pytest -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_0504_task1_full` | 1789 passed / failed0 / ERROR0 / skipped0 / 1 warning / 278.95秒 / exit0 / クラッシュなし | 05-04-task1-full/pytest.txt・status.json |
| 全体Ruff→Python限定format→Ruff→AST→diff | 全成功、108 files unchanged。harness/dispatcher個別lintも成功 | 05-EVIDENCE |
| 原本/コピー/manifest SHA256 | 診断423件一致、検証入力103ファイル不変 | 05-04-task1-full/artifacts/manifest.json・05-EVIDENCE |
| 利用者ファイル前後 | 設定と2promptは両時点不存在、実plugin/pycは両時点hash一致 | 05-EVIDENCE original_files_before/after |

全件は通常Windowsのhidden dispatcher→既存固定`05-02-verify.py`を使用。30秒上限・非console前景2秒安定は変更せず、TerminalからChromeへの遷移後に通過。selector/skip/除外/期限延長なし。成功時は`-x`でも全件実行した。終了後dispatcherはstopped。今回の警告は既存PyMuPDF ByteString非推奨1件。

診断原本のsandbox再読取はPermissionErrorとなり、正規require_escalatedで原本/コピー423件・入力103件一致を確認した。製品ソース・pyproject・依存定義は変更なし。既存requirements未commit差分のSHA256 `5AFFADBAB19AAC41E06B20142E67DAF1A4326B898D0DE4D34CFDBBFA1B403F74`を保持した。

## TDD Notes

- 最初のsandboxはTcl init.tclで1 failed/3 warnings/0.49秒。assert未到達のためREDに採用しない。
- 通常環境の対象1件は実Appのstatusがmissing、期待corruptという予定assertで失敗（1 failed/1 warning/2.63秒）。`05-04-task1-red-normal.xml/json`を保存し、`check tdd-red-evidence`のRED_EVIDENCE_OKと意味確認後にscenarioを実装した。
- 製品の既存機能は05-01〜03で実装済み。今回のRED対象は隔離scenarioの実装であり、製品機能を未実装と偽っていない。execute型・global tdd_mode=false。AGENTSのコミット前全件成功条件によりRED単独commitは作らない。

## Deviations from Plan

1. **[Rule 3 - Blocking] 検証環境**: sandbox Tcl初期化失敗後、正規通常環境でRED/局所/全件を確認。既存固定runnerを05-04限定のevidence/Temp/selectorへ制限したdispatcherで起動した。前景を強制変更していない。
2. **[Rule 1 - Bug] 新規試験spyとTk隔離**: 最初の局所は9 passed/1 failedでload_plugin名のtypo。拡大局所は107 passed/1 failedで別Tk画像owner、次は112 passed/1 failedで破棄済みdefault rootの復元を検出した。helperの生成前退避へ修正し、製品コードを触らず280局所・1789全件で確認。初期失敗も05-EVIDENCEに保持。
3. **人手待ち**: 05-04-02のacceptance「禁止2件は利用者目視までflagged-unverified。未達は記録して停止」により未完了。追加の承認gateを発明せず、計画に含まれる人手確認へ引き渡す。

## Checkpoint and Remaining Work

- **CHECKPOINT human-verify / blocking、05-04-02、1/2 tasks。** 文書・実測表は準備済みだがH01〜H12の人手結果が無い。05-UATのpending、禁止2件flagged-unverified、edge4件unclassified/unresolved/nullを維持する。
- read-corrupt harness起動済み。launcher33244/実Python32632、通常権限でPageFolio HWND16845424・Responding=True、stderr空を確認。sandboxがhandle0を返す制限と区別する。これは利用者の視覚評価ではない。初回10秒通知が過ぎていたら親が隔離harnessを正常終了・再起動して起動時観測を用意する。ユーザーにCLIは求めない。
- `05-UAT.md`に4scenarioの起動、12操作、期待結果、観測者/時刻/根拠欄を準備。まず破損/読取不能の別文言・入力先・PDF編集継続、次に保存write/replace・modal/言語・終了No/Yesを利用者が評価する。
- Task2の説明/開発履歴は未commit。開発履歴の開始前20行は他作業であり、Phase5の8行だけをindexに入れること。バージョン/README同期・実EXEはPhase6。
- `DEP-05-REGRESSION`、owner_missing、通知前景不一致は未解決。9384268祖先・利用者条件付き承認・過去と現在の全件証拠を照合した。今回の成功は原因修復・依存解除・出荷承認ではない。同種再発時に実装/後続/commitを止め、最初の失敗と診断を保持する。
- 05-03のTcl別thread破棄警告は今回未観測だが、05-03-deferred-items.mdのopenを解除しない。Nyquist/独立code/secure/goal-backward/Phase正式完了/DoDは親担当。
- `.planning/WINDOWS.md` entry3はunrun-verifyとしてopen。新規製品stub、skip/TODO、未申告のnetwork/auth/schema境界なし。隔離ファイルアクセスはT-05-12で被覆する。

## Actuals and Self-Check

台帳の基点8c61ea8からf51ecb8まで実測1commit/15files、git diffを改行結合した193817文字÷4切上げ=48455。診断manifestと実測証拠も含め、実装だけに狭めて見積との差を小さくしない。Task2準備差分と後続SUMMARY文書commitはこの実装境界に含めない。

## Self-Check: PASSED

主要8成果物が存在し、Task1 commitはHEAD祖先。最終入力103hashと利用者原本の前後hashが一致、git diff --check成功。Task2/人手/独立検証を完了済みと記載していない。
