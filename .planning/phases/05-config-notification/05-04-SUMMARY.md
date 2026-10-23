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
  - 利用者によるH01〜H12の12 passと設定失敗時の利用者説明
affects: [05-human-uat, 06-release-validation]
tech-stack:
  added: []
  patterns: [import前の解決先隔離, default-root退避と所有資源の逆順解放, 自動実測と利用者の明示回答の分離]
key-files:
  created:
    - tests/config_notice_support.py
    - .planning/phases/05-config-notification/05-NOTICE-HARNESS.py
    - .planning/phases/05-config-notification/05-UAT.md
    - .planning/phases/05-config-notification/05-EVIDENCE.json
    - .planning/phases/05-config-notification/05-04-dispatcher.py
  modified:
    - tests/test_config_notification.py
    - docs/CONFIGURATION.md
    - 開発履歴.md
    - .planning/phases/05-config-notification/05-VALIDATION.md
key-decisions:
  - 実利用設定/PDF/プロンプト/pluginsは使用せず、原本の存在/相対名/SHA256を前後照合する
  - 読取不能は実ACLを変更せず隔離設定のopenだけへ障害注入する
  - 全件成功と起動症状の原因修復・出荷承認を区別し再発時停止を維持する
  - 利用者の明示回答でH01〜H12を12 passとし、独立検証とPhase正式完了を別ゲートへ引き渡す
  - descriptor不明の禁止2件と未分類edge4件は人手完了だけで解決済みにしない
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
    verification:
      - kind: manual_procedural
        ref: .planning/phases/05-config-notification/05-UAT.md#H01-H12
        status: pass
    human_judgment: true
    rationale: 利用者が2026-10-24 JSTに隔離harnessで文言・入力先・編集継続・通知保持・終了分岐を確認し明示回答した
actuals:
  tokens: 54692
  tasks: 2
  commits: 3
commits: 3
plan_head_before: 8c61ea8d0bce0c84ace3d0a68cf1ecd83c7b6a81
plan_head_after: d68b8c7643d5a5b0b3a07aa69e7467ef9a7ee39b
duration: 23min（Task1）+ 人手待機・文書同期（別セッション）
completed: 2026-10-24
status: complete
---

# Phase 05 Plan 04: 設定通知の複合受入と隔離確認環境 Summary

実Appで読込障害・連続保存失敗・再構築・回復・終了を通し、原本隔離の自動受入1789件と利用者の人手受入12件を説明・検証証拠へ同期した。計画は2/2タスク完了。Phase正式完了と出荷は別ゲートであり未承認。

## Task Commits

1. **05-04-01 複合自動受入と隔離人手環境** — `f51ecb83645363f5bbc3bc1e3b47064f53882df7`（test）。通常hooks、固定root/feature/v1.10.0、非保護ブランチ、path限定。意図しない削除なし。
2. **05-04-02 説明と最終ゲート** — `d68b8c7643d5a5b0b3a07aa69e7467ef9a7ee39b`（docs）。設定説明、開発履歴のPhase5専用8行、VALIDATION、EVIDENCE、UATの5ファイル。通常hooks、私有一時indexによる限定commitで他作業のステージ内容を保持。意図しない削除なし。

**途中checkpointの記録:** `c8c1922`（docs）。Task1完了・人手確認待ちの当時の記録。利用者の明示回答後にfresh continuationでTask2を完了した。

共有STATE/state.json/ROADMAP/REQUIREMENTSは親の所有で変更していない。ROADMAPの既存staged blob `9b9f86ba59fe99666e128faf5931216e5bc19494`と開発履歴の別件20行を保持した。WINDOWS entry3の人手未実施記録は今回の12 passに対応する更新を親へ引き渡す。要件の正式完了判定も親が独立検証後に扱う。

## Accomplishments

- `create_isolated_app`はApp import/初期化前にsettings/base/plugins解決を私有一時領域へ差し替える。設定・2実prompt・実pluginsの存在/相対名/hashは前後一致し、実plugin load0を確認する。書込障害は隔離設定のopen、差替え障害は隔離設定宛てreplaceに限定する。
- closeは所有callback/Toast停止→Undo解放→Document close→root destroy→patch/一時領域解放。初期化途中例外・終了No・製品終了後も解放する。別Tkのdefault rootを生成前に退避し、画像が別interpreterへ登録される競合を防いだ。
- 実Document/Undo/Redoのidentity、選択、回転→Undo→Redo、破損原本bytes、現在言語、通知event_id・残6秒、明示成功時の再読込を同時に検証する。
- D-19の確認No→初回失敗→確認No→次回Yes、明示成功flag解除後の再失敗、D-20の権限回復後も同セッション保存禁止・無通知終了・正常再起動、D-21の100件FIFO完走と前/途中/ネストmodal・PDF/印刷Toast割込みを固定した。
- 恒久pytestはtests内helperだけをimportし、planning harnessへ依存しない。harnessは`pagefolio/app.py`を持つ祖先を探索する薄い開発入口で、実App/実Toastとメモリ内PDFを使う。製品入口・配布物・OCR実API・起動排他は変更していない。
- 設定概要・保存保護・自動保存・手編集の説明をD-01〜D-21と同期。corruptの明示保存とunreadableのセッション保護、終了確認No/初回失敗/次回終了/明示成功flag解除、各10秒FIFOを記載した。版番号/README同期はPhase6へ維持する。
- 利用者が隔離harnessでH01〜H12へ明示回答し12 pass。H03はread-corruptの約10秒自然消去、✕はH04の保存通知で確認。H06はApply直後の実Settings保持で、通知開始前の厳密な境界を自動証拠と区別する。

## Verification

| 検証 | 実測 | 証拠 |
|---|---|---|
| 最終局所 `pytest tests/test_config_notification.py tests/test_toast.py tests/test_pdf_ops.py -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_0504_targeted4` | 280 passed / 1 warning / 11.30秒 / exit0 | 05-EVIDENCE（実tool結果から記録） |
| 最終単一全件 `python.exe -m pytest -x -q --tb=short --basetemp=C:/Users/shdwf/AppData/Local/Temp/pf_0504_task1_full` | 1789 passed / failed0 / ERROR0 / skipped0 / 1 warning / 278.95秒 / exit0 / クラッシュなし | 05-04-task1-full/pytest.txt・status.json |
| 全体Ruff→Python限定format→Ruff→AST→diff | 全成功、108 files unchanged。harness/dispatcher個別lintも成功 | 05-EVIDENCE |
| 原本/コピー/manifest SHA256 | 診断423件一致、検証入力103ファイル不変 | 05-04-task1-full/artifacts/manifest.json・05-EVIDENCE |
| 利用者ファイル前後 | 設定と2promptは両時点不存在、実plugin/pycは両時点hash一致 | 05-EVIDENCE original_files_before/after |
| 利用者の人手受入 | H01〜H12の12 pass、原文回答・シナリオ・起動PID・実施日2026-10-24 JSTを記録 | 05-UAT・05-EVIDENCE manual_results |
| Task2の再利用確認 | 検証入力103ファイルを再hashし不一致0。製品/テスト/依存/環境の変更なし。全件・品質検査の不要な反復なし | 05-EVIDENCE tested_files_sha256と現行入力を照合 |

全件は通常Windowsのhidden dispatcher→既存固定`05-02-verify.py`を使用。30秒上限・非console前景2秒安定は変更せず、TerminalからChromeへの遷移後に通過。selector/skip/除外/期限延長なし。成功時は`-x`でも全件実行した。終了後dispatcherはstopped。今回の警告は既存PyMuPDF ByteString非推奨1件。

診断原本のsandbox再読取はPermissionErrorとなり、正規require_escalatedで原本/コピー423件・入力103件一致を確認した。製品ソース・pyproject・依存定義は変更なし。既存requirements未commit差分のSHA256 `5AFFADBAB19AAC41E06B20142E67DAF1A4326B898D0DE4D34CFDBBFA1B403F74`を保持した。

## TDD Notes

- 最初のsandboxはTcl init.tclで1 failed/3 warnings/0.49秒。assert未到達のためREDに採用しない。
- 通常環境の対象1件は実Appのstatusがmissing、期待corruptという予定assertで失敗（1 failed/1 warning/2.63秒）。`05-04-task1-red-normal.xml/json`を保存し、`check tdd-red-evidence`のRED_EVIDENCE_OKと意味確認後にscenarioを実装した。
- 製品の既存機能は05-01〜03で実装済み。今回のRED対象は隔離scenarioの実装であり、製品機能を未実装と偽っていない。execute型・global tdd_mode=false。AGENTSのコミット前全件成功条件によりRED単独commitは作らない。

## Deviations from Plan

1. **[Rule 3 - Blocking] 検証環境**: sandbox Tcl初期化失敗後、正規通常環境でRED/局所/全件を確認。既存固定runnerを05-04限定のevidence/Temp/selectorへ制限したdispatcherで起動した。前景を強制変更していない。
2. **[Rule 1 - Bug] 新規試験spyとTk隔離**: 最初の局所は9 passed/1 failedでload_plugin名のtypo。拡大局所は107 passed/1 failedで別Tk画像owner、次は112 passed/1 failedで破棄済みdefault rootの復元を検出した。helperの生成前退避へ修正し、製品コードを触らず280局所・1789全件で確認。初期失敗も05-EVIDENCEに保持。
3. **人手gateの継続**: 05-04-02は当初計画どおり利用者の目視まで停止し、2026-10-24 JSTのH01〜H12明示回答後に継続した。自動focusを人手passへ転用していない。禁止2件はdescriptorがなく各IDとの対応を確定できず、評価根拠を付けてflagged-unverifiedを維持した。
4. **[Rule 3 - Blocking] git書込境界**: Task2のsandbox実行は`.git/objects`への書込権限不足でstage前に停止。正規require_escalated経路で通常hooks付き限定commitを実施した。共有indexのROADMAPを保持し、開発履歴の別件を含めていない。

## Checkpoint and Remaining Work

- 人手checkpointは利用者のH01〜H12明示回答で完了。文言・入力先・編集継続・通知保持は人手pass、descriptor不明の禁止2件はflagged-unverified、edge4件はunclassified/unresolved/nullを維持する。
- 初回launcher33244/実Python32632と手動6起動の状態は履歴として記録。stdout/stderrは終了時hash結果を出力していないため、全harnessの終了・原本照合完了を推定しない。製品終了操作を利用者へ案内済みで、残存processを強制終了しない。
- Task2の説明と検証記録はcommit済み。バージョン/README同期・実EXEはPhase6。
- `DEP-05-REGRESSION`、owner_missing、通知前景不一致は未解決。9384268祖先・利用者条件付き承認・過去と現在の全件証拠を照合した。今回の成功は原因修復・依存解除・出荷承認ではない。同種再発時に実装/後続/commitを止め、最初の失敗と診断を保持する。
- 05-03のTcl別thread破棄警告は今回未観測だが、05-03-deferred-items.mdのopenを解除しない。Nyquist/独立code/secure/goal-backward/Phase正式完了/DoDは親担当。
- `.planning/WINDOWS.md` entry3のunrun-verifyは12 passの証拠で親が更新する。新規製品stub、skip/TODO、未申告のnetwork/auth/schema境界なし。隔離ファイルアクセスはT-05-12で被覆する。

## Actuals and Self-Check

台帳の基点8c61ea8からd68b8c7まで実測3commits/21files（Task1・途中checkpoint metadata・Task2）。`git diff`の218767文字÷4切上げ=54692。診断manifest・人手証拠・説明も含め、実装だけに狭めて見積との差を小さくしない。今回の最終SUMMARY commitは計測境界の後となる。Task1の23分以外の人手待機・別セッションの総時間は計測していない。

## Self-Check: PASSED

主要成果物が存在し、Task1・途中checkpoint・Task2の3commitはHEAD祖先。最終入力103hash不一致0、利用者原本前後hashの既存自動証拠を保持。人手12 pass・禁止2件未解除・edge4未分類・Nyquist flags falseを照合し、git diff --check成功。独立検証とPhase正式完了・出荷を完了扱いにしていない。
