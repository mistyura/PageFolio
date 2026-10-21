---
phase: 04-startup-control
plan: "02"
subsystem: startup
tags: [win32, mutex, named-pipe, deadline, coalescing, takeover, lifecycle]
requires:
  - phase: 04-01
    provides: 型付きWin32境界、期限付きIPC、A1〜A5の成立証拠
provides:
  - 二次開始から5秒の単一期限と受信側失効、acceptedとterminalの分離
  - 処理中batchとterminal後500ms固定窓による連打集約
  - 識別済み初期化processの確認済み死亡から一回だけ競争引継ぎ
  - root終了後のreleased公開と独立新規claim、例外/終了競合の回帰試験
affects: [04-03, 04-04, 04-05, startup-control]
actuals:
  tokens: 17281
  tasks: 2
  commits: 2
plan_head_before: 573986b2e22dd25f4acbe2e846f6bc1e24409a60
plan_head_after: 9633e04c651693b6f4d96497dc44ed010ce6063e
tech-stack:
  added: []
  patterns: [absolute-deadline, bounded-active-batch, terminal-cache, pinned-process-identity, seqlock-snapshot]
key-files:
  created: [tests/test_startup_control.py]
  modified:
    - pagefolio/startup_control.py
    - pagefolio/startup_win32.py
    - pagefolio/__main__.py
    - tests/test_startup_windows.py
key-decisions:
  - mutex取得、root生存、process生存を別々に判定し、初期化中の保持process handleのsignaledだけをD-07の死亡証拠とする
  - releasedは受付停止とroot不存在の確認後に完全公開し、既存mappingはACLを広げずOpenFileMappingの明示権限で再利用する
  - 連打は処理開始時のbatchとterminal後500ms固定窓で集約し、各memberの期限と拒否結果を維持する
requirements-completed: [V110-START-01, V110-START-02, V110-START-03, V110-FOCUS-01]
coverage:
  - id: D1
    description: 単一5秒期限、busy/遅延要求の失効、不正入力/ACKの拒否
    verification:
      - kind: unit
        ref: tests/test_startup_control.py
        status: pass
      - kind: integration
        ref: tests/test_startup_windows.py#test_tracer_io_lifetime_unresponsive_peer_five_second_deadline
        status: pass
    human_judgment: false
  - id: D2
    description: 8件のaccepted、処理中の追加、member別期限、固定500ms集約と端の独立要求
    verification:
      - kind: unit
        ref: tests/test_startup_control.py#test_accepted_is_not_terminal_and_eight_requests_restore_once
        status: pass
      - kind: unit
        ref: tests/test_startup_control.py#test_fixed_cooldown_does_not_extend_and_edge_is_independent
        status: pass
    human_judgment: false
  - id: D3
    description: 初期化死亡の候補2者引継ぎ、同時2/8起動、両Python入口と別配置/見かけ版差
    verification:
      - kind: e2e
        ref: tests/test_startup_windows.py#test_takeover_two_candidates_after_confirmed_initialization_death
        status: pass
      - kind: e2e
        ref: tests/test_startup_windows.py#test_simultaneous_real_processes_construct_one_editor
        status: pass
      - kind: e2e
        ref: tests/test_startup_windows.py#test_lifecycle_both_python_entries_and_relocated_version_share_owner
        status: pass
    human_judgment: false
  - id: D4
    description: 終了キャンセル、正常/強制/公開前後例外後再起動、live旧processとreaderのreleased/closing境界
    verification:
      - kind: integration
        ref: .venv/Scripts/python.exe -m pytest -q tests/test_startup_windows.py -k "lifecycle or simultaneous or takeover"
        status: pass
    human_judgment: false
duration: 23min+
completed: 2026-10-21
status: complete
---

# Phase 4 Plan 2: 絶対期限・連打集約・一回引継ぎ Summary

**5秒で復帰要求を失効し、処理中と完了後500msの連打を一回へまとめ、確認済み初期化死亡だけから一回引き継ぐ。**

## 実行結果

- Task 2/2完了。Task1: `164796c`、Task2: `9633e04`。意図しないtracked削除なし。
- 最終単一プロセス全件pytest: **1503 passed / 1 warning / 109.54秒**。skip/除外なし。
- 最終指定Windows試験: **14 passed / 14 deselected / 1 warning / 42.59秒**。deselectedは計画指定の`-k`選択によるもの。選択された14件にskipなし。
- 状態遷移の個別実行: **52 passed / 1 warning / 0.09秒**。最終全件にも同じ52件を含む。
- Task1コミット前単一全件: **1472 passed / 1 warning / 66.96秒**。
- ruff check: All checks passed! / ruff format: 95 files left unchanged / pagefolio.py: AST OK。
- 唯一の最終warningは既存PyMuPDFのByteString非推奨警告。
- 全spawnで設定・プロンプト・pluginsと名前空間を隔離。原本設定/2種プロンプトの存在/SHA-256不変を各fixtureでassert。
- 終了後CIM読取で`_test_scenario_bootstrap`を実行するPython子process残留 **0**。

開始時刻を厳密には記録していない。最初の保存時刻観測は22:34:55 JST、
Task2コミット後計測は22:58:01 JSTで、少なくとも23分。初期読込はそれ以前。
actualsは5つの製品/試験ファイルのbase..after実diff 69122文字÷4の切上げ17281。
commit数2は永続ledgerのbase..afterをgit rev-listで測定し、本SUMMARYのmetadata commitは含めない。

## 実装内容

- `_receive`は有界queueへ受理しacceptedを返す。workerは同じIDのterminalを待ち、Tk APIを呼ばない。
  不明op・ID/世代/issued/deadline不正・不正JSON・1024byte超過を拒否する。
- `_dispatch_pending`は最初のdispatchでactive_batchを確保し、再入中の別IDも同じbatchへ追加する。
  副作用は一回。各memberは独自のdeadlineを保持し、全member失効時は副作用ゼロ。
  completed/foreground_deniedから500msの固定窓を設け、到着によって延長しない。
  同一IDはterminalを再送し、別IDのcoalescedも拒否結果と完了tickを保持する。
- read/write/connect/readiness/accepted待ちが同じ絶対deadlineを使用する。
  `_io`は開始直前、前面化許可委譲は呼出し直前、復帰処理は各OS副作用直前に再検査する。
  送信後の不正ACKを理由に新IDで副作用を再送しない。queue32/cache128を維持する。
- 04-03で復元/モーダル操作を加える際も、`restore_window(hwnd, is_current=...)`のguardを
  各副作用直前に呼ぶ。coordinatorの有効member/世代/deadline判定を省略しない。
- `_try_takeover`はinitializingの検証済みidentityと保持process handleだけを参照する。
  signaledかつ残余時間内に一回だけ原子的claimを試す。敗者は同じ期限で新ownerへの通信へ戻る。
  WAIT_FAILED、アクセス拒否、生成時刻不一致、部分公開、無応答、threadだけの死亡では新GUIを作らない。
- readerはsnapshotごとにmappingをopen/read/closeし、確定identityとprocess handleだけを保持する。
  引継ぎ勝者は旧snapshotを照合してからseqlock内で全identity/stateを新世代として再公開する。
- root破棄確認→受付停止→pending失効→IPC取消し/寿命退避→released全公開→mapping/process handle閉鎖→mutex解放。
  正常releaseは旧identityと独立release_generationを保持し、同じmutexを所有するメインスレッドが公開する。
  root不存在を証明できなければclosingの所有をprocess終了まで保持する。
- 正しいreleasedを見て初回claimした独立起動は、旧processが試験用終了待機中でも新一次になれる。
  すでに二次待機中の要求はclosing/releasedから新GUIへ移らない。
  生存PIDの生成時刻不一致を含むreleased identity不一致もmapping上書きを拒否する。

## Windows実測

最終全件fixture: `C:/Users/shdwf/AppData/Local/Temp/pytest-of-shdwf/pytest-33`。
これは本実行中に生JSONを読み直した値であり、過去runからの転記ではない。

| ケース | 観測 |
|---|---|
| 無応答peer | expired / 5000ms / app構築0 |
| 実mainの即時接続拒否→本番10秒案内 | connection_failed / 10015ms / app構築0 |
| 同時8起動 | 一次構築1、二次7件は構築0、同じ一次callback1回、status保持 |
| 同時8起動の二次 | foreground_denied / 1844〜1922ms。前面化成功とは扱わない |
| 候補2者 | 両方が同じ旧PID32000・生成時刻134370644770380828・initializing世代を保持し、死亡確認true |
| 候補0 | claim existing / app構築0 / 新ownerからforeground_denied / 3437ms |
| 候補1 | claim acquired / primary移行1 / claim側応答31ms。GUI寿命を含む最終elapsed3750ms |
| 終了No→Yes | No後はmutex保持・二次は既存画面へ復帰、Yes後の独立起動は新一次構築1 |
| released・旧process生存・古いreader | released snapshotを照合し、独立起動だけが新世代を公開 |
| 公開前例外・公開後初期化例外・所有PID強制終了 | 後続の独立起動成功。所有PIDの強制終了は試験自身がspawnしたPIDのみ |
| 所有threadだけ死亡 | 仮取得mutexを返し、生存processの既存pipeへ連絡。引継ぎなし |
| 部分公開・release公開失敗 | 有限失効/closingを維持。全reader閉鎖後の独立claimは通常一次 |
| 両Python入口・別配置・見かけ版差 | 実runpy入口、コピーした別package、試験版表示でも同じ名前空間の一次へ復帰 |

部分公開などの長い組合せは残余80msやfake clockで検証した。これを本番5秒の実測とは扱わない。
本番5秒と10秒の代表観測は上表に分離した。5秒待機＋案内の全体受入やモーダル/入力先/実OCR状態は
04-03〜05で継続する。実EXEと版情報/README/開発履歴同期はPhase6担当。

## Deviations from Plan

**1. [Rule1 - 回帰調整] Task1で既存Windows tracerの期待値とoverrideを更新**
- 新しい集約仕様では同時二次2件の復帰callbackは1回。旧`>=2`を1へ更新した。
- `is_current`引数を試験backendへ引き渡し、実OS直前のguardを保った。
- Task1のfiles欄外にあるtests/test_startup_windows.pyを、同タスク由来の回帰修正として変更。
- Commit: 164796c。全件1472件成功。

計画内で解消した実装問題:
- 既存mappingに対するCreateFileMappingの暗黙要求権限が最小ACLと一致せず、実プロセスでWinError5。
  ACLを広げずOpenFileMapping(READ_CONTROL|6)で既存mappingを再利用して解消。
- 後続coalescedのcompleted_tickは新要求のissuedより前になり得る。
  500ms固定窓に沿って検証し、拒否を成功へ変換せず同じterminalを維持。
- released snapshotも生存processの生成時刻を照合し、PID再利用相当の上書きを拒否。

## TDD Gate Compliance

Task1はaccepted分離のassertionで1 failed（5.11秒）、Task2は既存closeのroot_absent未伝達のassertionで
1 failed（0.10秒）を実測してから実装した。Task2の初回AttributeError probeは有効なRED証拠に数えない。
AGENTS.mdの「コミット前に全件pytest成功」を優先して失敗REDコミットを作成していない。
形式別RED evidenceの機械判定も実施していないため、RED→GREENコミット規約の完全遵守とは扱わない。
workflow.tdd_modeはfalse。各タスクのGREEN全件成功後に個別コミットした。

## 未解決点と引き継ぎ

本プランの未解決障害、必須verify未実行、製品stub、追加依存はない。pyproject.tomlは無変更。
新しいネットワークendpoint/auth/schemaなど、計画外のtrust boundaryは追加していない。
SID・PID・request_id・期限/結果以外の設定値や機密値を診断へ出していない。

requirements-completedは計画IDの被覆メタデータであり、Phase4全体の要件完了を宣言しない。
STATE/ROADMAP更新と要件のready判定は親オーケストレーターが単一書き手として実施する。
04-03は本担当で開始していない。

一次資料: [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)、
[CreateFileMapping](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createfilemappinga)。
threadのabandonedとprocess signaledを区別し、既存mappingの権限要求を確認した。

## Self-Check: PASSED

5つの製品/試験ファイルと本SUMMARYの存在、2つのtask commitのHEAD祖先関係、
永続ledgerのbase/afterと実測commit数を確認した。
evaluation-scopeは現行2commitを含むが、過去milestoneの同じ04-02 scopeも混在するため、
本実行の集計は573986b..9633e04の2commitへ明示的に限定した。
