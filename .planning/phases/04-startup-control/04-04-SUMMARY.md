---
phase: 04-startup-control
plan: "04"
subsystem: startup
tags: [win32, notice, nonactivate, mutex, seqlock, dpi, i18n, deadline]
requires:
  - phase: 04-03
    provides: 前面化拒否と通信失敗を区別する復帰処理と作業継続試験
provides:
  - 確認済みの事実から3分類する日英の起動前案内
  - OS message fontとwindow DPIに従う非活性窓、手動close、初回10秒の固定期限
  - 原因別通知leaseと表示identityの検証、同原因8processの集約と異常終了回復
  - 本番5秒待機と10秒表示、閉鎖後15秒の実測証拠
affects: [04-05, startup-control, windows-uat]
actuals:
  tokens: 17420
  tasks: 2
  commits: 2
plan_head_before: 3fa2e2a2056c5ae82d29cd8172f02c27e6eecb5d
plan_head_after: ebe13fa58fb7b06854e03e0b68d4d4ae7fa722aa
tech-stack:
  added: []
  patterns: [原因別mutexと表示snapshot, 検証済み可視窓への合流, OS message font, 副作用前後のHWND観測]
key-files:
  created:
    - pagefolio/startup_notice.py
    - tests/test_startup_notice.py
    - .planning/phases/04-startup-control/04-04-NOTICE-HARNESS.py
    - .planning/phases/04-startup-control/04-04-NOTICE-RUNTIME.json
    - .planning/phases/04-startup-control/04-04-RED-task1.json
    - .planning/phases/04-startup-control/04-04-RED-task1.xml
    - .planning/phases/04-startup-control/04-04-RED-task2.json
    - .planning/phases/04-startup-control/04-04-RED-task2.xml
  modified:
    - pagefolio.py
    - pagefolio/__main__.py
    - pagefolio/startup_control.py
    - pagefolio/startup_win32.py
    - pagefolio/lang.py
    - tests/test_startup_windows.py
key-decisions:
  - 起動前案内は設定を読み書きせずOSのUI言語を使用し、アプリ設定言語との相違を許容する
  - mutexの存在やabandonedだけでは合流・再表示せず、process生成時刻と可視HWNDのclass generationまで照合する
  - 通知を検証・生成できない場合はnotification_unavailableとOSコードを返し、両Python入口で非zero終了する
  - 非活性の実測は表示とDestroyWindowの各直前直後を比較し、利用者による途中の画面切替と分離する
requirements-completed: [V110-START-03, V110-FOCUS-01]
coverage:
  - id: D1
    description: 判定不能・確認済みownerへの通信失敗・5秒時間切れの日英分類と成功/前面拒否時の案内0
    requirement: V110-START-03
    verification:
      - kind: unit
        ref: tests/test_startup_notice.py
        status: pass
      - kind: unit
        ref: tests/test_lang_parity.py
        status: pass
    human_judgment: false
  - id: D2
    description: 同原因8processの集約、初回期限維持、手動close後再表示、保持handleを伴うowner死亡回復
    requirement: V110-START-03
    verification:
      - kind: integration
        ref: tests/test_startup_windows.py#test_notice_dedup_eight_processes_keep_original_deadline
        status: pass
      - kind: integration
        ref: tests/test_startup_windows.py#test_notice_dedup_owner_crash_with_retained_handles_can_redisplay
        status: pass
    human_judgment: false
  - id: D3
    description: 非活性表示と閉鎖、本番5000/10000ms、有限終了と閉鎖後15秒の窓消失
    requirement: V110-FOCUS-01
    verification:
      - kind: integration
        ref: tests/test_startup_windows.py#test_tracer_notice_nonactivate_lifetime_and_close
        status: pass
      - kind: e2e
        ref: .planning/phases/04-startup-control/04-04-NOTICE-RUNTIME.json
        status: pass
    human_judgment: false
duration: 42min+
completed: 2026-10-22
status: complete
---

# Phase 4 Plan 4: 起動前の非活性案内と通知集約 Summary

**起動失敗を事実に応じて日英3分類し、可視通知identityで連打を集約しながら、入力先を変えず初回10秒で案内を閉じる。**

## 実行結果

- Task 1: 単一全件 **1573 passed / 1 warning / 190.01秒**。
- Task 2 最終: 単一全件 **1597 passed / 1 warning / 193.00秒**。失敗・ERROR・skipなし。
- Task 2 指定notice単体: **42 passed / 1 warning / 0.07秒**。
- Task 2 指定Windows群: **8 passed / 45 deselected / 1 warning / 6.52秒**。選択された試験のskipなし。
- 日英parity/font guardを含むTask 1の対象群: **34 passed / 42 deselected / 1 warning / 3.03秒**。
- 最終ruff check、ruff format（100 files unchanged）、pagefolio.pyのAST確認: 成功。
- 明示harness: 起動要求の期限 **5000ms**、案内期限差 **10000ms**、二次終了 **15015ms**。
- 表示直前/直後と閉鎖直前/直後のforeground HWNDは各々 **135134** で一致。
- 閉鎖後 **15.007秒** 観測し、通知HWND消失・二次終了を維持。原本3ファイル不変。
- 最後のWindows process照会で専用bootstrap残留 **0**。

warningは既存PyMuPDFのByteString非推奨警告。通常pytestはUAC・人のクリック待ちを含まない。
全件時間は計画の120秒目標を上回るが、既存の実Windows/復帰試験を除外していない。

記録可能なRED着手は2026-10-21T14:42:45Z、closeout計測は2026-10-21T15:24:55Z。
durationはこの42分以上で、初期読込時間を含まない。actuals.tokensは永続ledgerの
base..afterに対する実diff文字数/4（端数切上げ）、commitsは同範囲のgit rev-list実測。
SUMMARY/RED証拠を記録する後続メタデータcommitはこの測定範囲外。

## Taskごとのコミット

1. Task 1: `368052e` — 起動失敗の分類と非活性の期限付き案内。
2. Task 2: `ebe13fa` — 通知所有者を検証して連打と異常終了時の集約を保証。

意図しない削除なし。新規生成物は対象を明示して記録し、他者のplanning変更はstageしていない。

## 実装の要点

- claimのOS失敗はcheck_failed、識別済みownerとの通信失敗はcontact_failed、期限到達はtimeout。
  completed/foreground_denied/primaryでは案内境界を呼ばない。
- LANGの5キーを日英対称で追加し、完全リテラルで参照する。UIは固定文言だけを使い、
  traceback・パス・SID・PID・API名を表示しない。通知不能の製品診断はreason/OSコードのみ。
- GetUserDefaultUILanguageの日本語primary languageはja、その他はen。
  設定I/Oを追加しないため、アプリ設定言語と異なる場合がある。
- WS_EX_NOACTIVATE、MA_NOACTIVATE、SW_SHOWNOACTIVATEを使い、子BUTTONを作らず
  WM_LBUTTONUPで閉じる領域を判定する。OSのmessage fontを使い、実windowのDPIとwork area、
  DrawTextの実測から寸法を求める。process-wide DPI設定は追加しない。
- 初回表示時にdeadlineを確定し、WM_TIMERとmessage loopの残余時間で閉鎖する。
  同一公開値の再確認以外の期限更新を拒否する。WndProcはclass解除まで強保持する。
- 原因別のLocal mutexとseqlock mappingは起動owner/pipeから独立する。
  snapshotはPID/生成時刻/session/generation、準備中・表示中・閉鎖済み、HWND、表示時刻/期限を持つ。
  表示窓のPIDと固有class generationも照合し、HWND再利用を合流根拠にしない。
- WAIT_TIMEOUTは検証済みの可視窓だけに合流。abandoned/取得時に旧snapshotがあれば、
  process死亡か正規closeを確認した場合だけ再表示する。thread死亡・未公開・公開途中・不明は失敗。
- mutexアクセス拒否では同じ正規名への最小権限OpenMutex/READ_CONTROL確認を一度だけ行う。
  検証不能ならnotification_unavailableで有限終了し、別名窓や成功扱いを作らない。
- timer/font/window/class、mapping/view/mutexの解放は生成/所有threadのfinallyへまとめた。
  窓生成失敗の注入では500ms以内のcleanupと再取得を確認した。

## 証拠

- 本番値: `04-04-NOTICE-HARNESS.py` → `04-04-NOTICE-RUNTIME.json`。
- 成功生データ: `.planning/tmp/notice-production-4f5d0867e6884c1db68d4b57265dc980/`。
- 初回harnessの前面全体比較不合格:
  `.planning/tmp/notice-production-98240e34fcf04c23a27b339003d4ebd0/`。
  表示時は135134で不変、閉鎖後593514。途中の前面切替を閉鎖の副作用と区別できない測定だったため、
  表示/DestroyWindowそれぞれの直前直後を記録して再実測した。初回結果を消去/合格化していない。
- 各spawnは設定、2種プロンプト、plugins、名前空間を初回import前に隔離する。
  bootstrapで原本の存在/SHA-256を再照合する。

## Deviations from Plan

**1. [Rule 2 - 必須経路の補完] 薄いpagefolio.py入口にも通知不能時の非zero終了を適用**
- module入口だけではscript入口が正常終了してしまうため、両入口を揃えた。
- 通常終了は従来どおりreturnを維持する。初期実装のsys.exit(0)はrunpyの既存試験21件を
  中途終了させたため修正し、単一全件1573件を再実行してからTask 1をcommitした。
- ファイル: pagefolio.py、pagefolio/__main__.py。Commit: 368052e。

その他の追加構造は計画済みの通知同期・診断・実時間harnessである。
版番号/README/開発履歴と実EXEは計画どおりPhase 6担当。

## TDD Gate Compliance

- Task 1 RED: claim失敗がcheck_failedにならずunhandled_exceptionとなる対象assertionを実測。
- Task 2 RED: 未表示mutexをcoalescedと誤認する対象assertionを実測。
- 各JSON/XMLに実コマンド、終了コード、未改変JUnit、console、期待/実際、semanticAssessmentを保存。
  両方とも`check tdd-red-evidence`が **RED_EVIDENCE_OK**。収集/構文/fixture失敗をREDにしていない。
- AGENTS.mdのコミット前全件pytest成功を優先し、失敗RED状態の単独commitは作成していない。
  RED→GREENの別commit規約の完全遵守とは扱わない。workflow.tdd_mode=false。

## Issues Encountered

- pytestの既存一時領域がsandboxに拒否された実行は、正規昇格で同じコマンドを再実行した。
  拒否によるfixture ERRORを製品失敗や合格へ読み替えていない。
- Git管理領域への台帳保存/stage/commit、process照会も必要な正規昇格で実施した。
- 新依存、pyproject.toml変更、未接続UI、Known Stub、未実行の本task必須verifyはない。
  追加の未計画trust boundaryもない。

## 後続への引き継ぎ

- 04-05で新しい通知窓の実クリック/入力継続、100/150/200%の可読性とclose領域、
  通常/昇格双方の作成順序で新leaseの集約を実機確認する。今回の自動試験は同一integrity。
  過去A3/A4の旧primitive結果だけを新実装の再受入としない。
- `notice-case-production-owner`は本番10秒の可視通知とsnapshot/dpi/close_rectをreadyへ記録。
  `notice-case-peer-*`で同原因に合流できる。旧manual-ownerのA4-resource-checkは窓未公開のため、
  新leaseの合流証明には使わない。
- 明示起動用`notice-production-check/contact/timeout`は本番10秒を使う。
  timeoutには既存のinitializing-owner等を組み合わせる。通常pytestは短縮timerのみ。
- 前面化拒否と通信失敗、通知不能と表示成功を引き続き分離する。
- requirements-completedは計画宣言の被覆メタデータ。共有要件の台帳完了は親のready-ids判定待ち。
  STATE/ROADMAP/REQUIREMENTSは親オーケストレーターが単一書き手として更新する。
- 本担当は04-05を開始していない。未分類probe/未解決prohibitionを自動resolvedにしない。

## Self-Check: PASSED

主要成果物と4つのRED証拠の実在、両task commitのHEADへの祖先関係を確認した。
永続ledgerの開始HEADと終了HEAD、実コミット数2を照合した。専用bootstrap残留0、原本不変。
