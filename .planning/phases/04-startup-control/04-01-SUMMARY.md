---
phase: 04-startup-control
plan: "01"
subsystem: startup
tags: [windows, win32, ctypes, tkinter, ipc, mutex, pytest]
requires:
  - phase: v1.9.0
    provides: 出荷済みの既存PDF編集画面と回帰試験
provides:
  - 正式完了と未完了を区別するDoDゲート
  - 同一セッション所有権と期限付きIPCから実Tk callbackへ到達する本番tracer
  - 非活性案内とI/O寿命の境界、およびA1〜A5の実測証拠
affects: [04-02, 04-03, 04-04, 04-05, startup-control]
actuals:
  tokens: 30818
  tasks: 3
  commits: 5
plan_head_before: d274ef3f5f9245b749d8aadae09d8a0675f6a833
plan_head_after: 8d786405dd3b7279273f18fdff6c2598523720be
tech-stack:
  added: []
  patterns: [型付きWin32境界, メインスレッドmutex所有, 有界Tk受信queue, 完了確認付きoverlapped取消し]
key-files:
  created:
    - pagefolio/startup_control.py
    - pagefolio/startup_win32.py
    - tests/test_startup_windows.py
    - .planning/phases/04-startup-control/04-TRACER-EVIDENCE.md
    - .planning/phases/04-startup-control/04-HUMAN-EVIDENCE.json
    - .planning/phases/04-startup-control/04-01-CHECKPOINT.md
    - .planning/phases/04-startup-control/deferred-items.md
  modified:
    - tests/test_gsd_dod.py
    - .planning/PROJECT.md
    - pagefolio/__main__.py
    - pagefolio/__init__.py
key-decisions:
  - logon SIDを維持したACLで通常/昇格両順序の全4資源を実測し、ACLを拡張しなかった
  - 非活性の実クリックと無操作10秒閉鎖を利用者確認とHWND/tickの両方で確定した
  - 公開APIを維持する遅延再exportによりclaim前のGUI/OCR importを除いた
requirements-completed: [V110-START-01, V110-START-02, V110-START-03, V110-FOCUS-01, V110-FOCUS-02]
coverage:
  - id: D1
    description: 完了フェーズのvalidated義務と未完了開発を両立するDoD
    verification:
      - kind: unit
        ref: tests/test_gsd_dod.py
        status: pass
    human_judgment: false
  - id: D2
    description: 実mainと実mutex/pipeから既存Tkのterminal応答に到達する起動tracer
    verification:
      - kind: e2e
        ref: tests/test_startup_windows.py#test_tracer_e2e_real_main_terminal_ack
        status: pass
      - kind: integration
        ref: .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k tracer
        status: pass
    human_judgment: false
  - id: D3
    description: 非活性の実閉鎖・権限差全4資源・固定本番名の成立性
    verification:
      - kind: manual_procedural
        ref: .planning/phases/04-startup-control/04-HUMAN-EVIDENCE.json
        status: pass
    human_judgment: true
    rationale: 利用者が実入力継続とUAC操作を確認済み。別環境での再確認には人の操作を要する
duration: 60min+
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 1: 起動所有権・実Tk復帰と非活性案内の方式成立 Summary

**固定名mutex・共有mapping・期限付きnamed pipeから既存Tkへ復帰し、権限差と非活性案内を実測で確認した。**

## 実行結果

- Task: 3/3完了。Task3のblocking-humanゲートは利用者の実操作と生記録で解消。
- 再開後の指定tracer: **14 passed / 1 warning / 37.97秒**。
- 再開後の単一全件pytest: **1437 passed / 1 warning / 67.89秒**。
- 製品コード確定時のruff check/formatとpagefolio.py AST: 成功。Task3は文書のみ変更。
- A1〜A5は全件pass。通常/昇格両順序のowner・mapping・双方向pipe・notice leaseを照合。
- 原本設定/2種プロンプトは不存在を維持。全試験と子bootstrapで存在/SHA-256を照合。
- 生fixtureと集約JSONの24record一致、試験process残留0。原データは保持。

計測可能な最初のcommitは2026-10-21 21:27:52 JST、closeout計測は22:28:23 JST。
durationはこの間の60分以上（人手確認待ちを含む）で、Task1の着手時刻は未記録。
actuals.tokensはTask3 commitまでの実diff文字数/4、commitsは永続ledgerのbase..afterを
git rev-listで実測した5件。これから作成するSUMMARY自身のメタデータcommitを含めない。

## 成果

- DoDは現行Phase行・Phase Details・Phase進捗表を照合する。
  未完了liveのdraft/未生成を許容し、正式完了liveと対象archiveではvalidatedを要求。
  SUMMARY不足・重複・未記載・矛盾・途中件数不一致を違反として検知する。
- 起動所有権はTk構築前に同じメインスレッドで取得/公開し、そのスレッドで解放する。
  workerはTk/fitzを操作せず有界queueへ渡し、Tk側が期限を再確認する。
- Win32は型・明示ACL・peer identity・生成時刻・共有snapshotを検証する。
  I/Oは絶対期限、取消し完了確認、最大32スロットのquarantineで寿命を管理する。
- 初期化例外後の再claim、無応答5秒終了、実main接続失敗から10秒案内終了を検証。
  通常pytestは名前空間と設定/プロンプト/pluginsを子ごとに隔離し、UAC/入力待ちを行わない。

## Taskごとのコミット

1. Task1 DoD: `8b5b304`。途中進捗の追加整合: `282d8fe`。
2. Task2 本番tracerと自動試験: `de27654`。
3. Task3 実機証拠照合・ゲート解消: `8d78640`。

停止点の永続化: `32868b7`。各commitに意図しない削除なし。

## A1〜A5の成立根拠

| ID | 確認した事実 |
|---|---|
| A1 | 実無応答peerがexpired、5000ms。overlapped取消しとGC後の参照保持・回収を自動確認 |
| A2 | 奇数sequence/生成時刻不一致を拒否。同時二次2件はapp構築0で同じ一次callbackへ到達 |
| A3 | 実クリック閉鎖1937ms、無操作retry10000ms。前面HWND不変、利用者が入力継続を確認 |
| A4 | 両作成順序で同SID/session、異なる認証LUID。owner/mapping/pipe/noticeの全4資源pass、ACL拡張なし |
| A5 | 親before≤子tick≤親afterとwall clock差替えを検証。GetTickCount64の起動後経過時計という公式仕様と整合 |

通常一次→昇格二次はforeground_denied/62ms、逆順はcompleted/63ms。
固定本番名retryはforeground_denied/31ms。前面化拒否を前面化成功とは記録していない。
全runの一次構築1/二次0、一次復帰1/status保持を確認した。
初回timerは利用者クリックにより自動閉鎖未成立、初回固定名はlauncher/実Python PIDの
相違を試験側の同一性ガードが検出して中断。どちらも保存しretryの成功と区別した。

## Deviations from Plan

### 自動修正

**1. [Rule2] claim前にpackage再exportがGUI/OCRをimportしていた**
- 発見: Task2。
- 対応: pagefolio/__init__.pyを公開名を維持するPEP562遅延再exportへ変更。
- 検証: 二次のapp module未import、全件回帰。
- Commit: de27654。

**2. [Rule1] 途中Progressの件数とSUMMARYの整合が不足**
- 発見: Task1の自己レビュー。
- 対応: 途中件数/対応SUMMARYの整合と太字なしPhase行の回帰を追加。
- Commit: 282d8fe。

### 計画内の実装問題と試験側の調整

- DisconnectNamedPipeが未読terminalを破棄する実挙動は、同一期限内の受信確認で修正。
- 周期的なconnect取消しによる接続競合は、停止可能なevent待機へ変更して回避。
- sandboxがpytest一時領域を拒否したため、正規の昇格実行で検証した。
- 固定名の初回中断は試験launcherのPID差。親子PIDをCIMで照合してからretryした。
- 版情報/README/開発履歴と実配布EXEの同期は、計画どおりPhase6担当。

## TDD Gate Compliance

REDはTask1で9 failed/9 passed、Task2の初期probeでassertion 1 failedを実測した。
AGENTS.mdのコミット前全件pytest成功を優先し、失敗状態のREDコミットは作成していない。
機械判定済みRED evidenceも存在しないため、RED→GREENコミット規約の完全遵守とは扱わない。

## Issues Encountered

途中の全件実行で既存OCR試験中にTk Variable.__del__のunraisable警告を1度観測した。
最終/再開後の全件では未再現。原因未確認としてdeferred-items.mdへ保存した。
最後のwarningは既存PyMuPDFのByteString非推奨警告のみ。
stub/TODO・未実行の必須verifyはない。追加の未計画trust boundaryはない。

## 後続への引き継ぎ

04-02の5秒失効・終了競合・一回引継ぎへ進める。本担当は04-02未着手。
最小化/最大化・モーダル・入力先維持の拡張は04-03、原因分類と案内集約の拡張は04-04、
広い受入は04-05が担当する。tracerの成立をPhase4全体完了と混同しない。

requirements-completedは計画宣言IDをコピーした被覆メタデータであり、要件台帳の
完了を意味しない。共有IDのready-idsは5件すべてblocked/ready空のため完了登録なし。
STATE/ROADMAPの更新は親オーケストレーターが単一書き手として実施する。

## Self-Check: PASSED

主要作成ファイル、Task1/2/3と停止点の全5コミットの祖先関係を確認した。
SUMMARYのcoverage各成果を試験または人手証拠へ対応付けた。
