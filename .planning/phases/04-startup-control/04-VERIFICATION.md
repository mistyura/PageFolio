---
phase: 04-startup-control
verified: 2026-10-21T22:12:01Z
status: passed
score: 21/21 must-haves verified
covered_files: [".planning/phases/04-startup-control/04-01-PLAN.md", ".planning/phases/04-startup-control/04-01-SUMMARY.md", ".planning/phases/04-startup-control/04-02-PLAN.md", ".planning/phases/04-startup-control/04-02-SUMMARY.md", ".planning/phases/04-startup-control/04-03-PLAN.md", ".planning/phases/04-startup-control/04-03-SUMMARY.md", ".planning/phases/04-startup-control/04-04-PLAN.md", ".planning/phases/04-startup-control/04-04-SUMMARY.md", ".planning/phases/04-startup-control/04-05-PLAN.md", ".planning/phases/04-startup-control/04-05-SUMMARY.md", ".planning/phases/04-startup-control/04-06-EVIDENCE.json", ".planning/phases/04-startup-control/04-06-PLAN.md", ".planning/phases/04-startup-control/04-06-SUMMARY.md", "pagefolio.py", "pagefolio/__init__.py", "pagefolio/__main__.py", "pagefolio/app.py", "pagefolio/lang.py", "pagefolio/startup_control.py", "pagefolio/startup_focus.py", "pagefolio/startup_notice.py", "pagefolio/startup_win32.py", "tests/test_gsd_dod.py", "tests/test_startup_control.py", "tests/test_startup_focus.py", "tests/test_startup_notice.py", "tests/test_startup_windows.py"]
covered_digest: "v3:sha256:9a78307802b2c00c17bb35c285ea10cb0b5def9c36eecceee787624130c309b9"
behavior_unverified: 0
overrides_applied: 0
human_verification: []
re_verification:
  previous_status: gaps_found
  previous_score: 19/21
  gaps_closed:
    - "SC3/D-09/V110-START-03: backend構築失敗時の独立案内、部分解放、名前付き回帰"
  gaps_remaining: []
  regressions: []
flagged_prohibitions: 3
unclassified_edges: 5
decision_coverage:
  honored: 16
  total: 16
  not_honored: []
deferred:
  - truth: "W01〜W12の実入力・見た目・OS拒否・DPI/UAC・別session・実配布EXEの最終人手受入"
    addressed_in: "Phase 6 / V110-QA-02"
    evidence: "2026-10-22承認済みROADMAP受入範囲改訂と06-UAT-CARRYOVER全行。全必須passまでリリース停止"
  - truth: "並行負荷の二次終了15.5秒予算適合性の再評価"
    addressed_in: "Phase 6 / W07b"
    evidence: "06-UAT-CARRYOVERは15609ms超過と15140ms単独を両方保持し条件/契約を再評価する"
  - truth: "禁止事項3件の明示人手解決と未分類edge5件の照合"
    addressed_in: "Phase 6 / V110-QA-02"
    evidence: "06-UAT-CARRYOVERの引受条件にflagged-unverified/unclassified/unresolved保持と実機照合を明記"
prohibitions:
  - statement: "既存の未保存作業を失う強制終了や排他の強制解除を、起動競合の解決手段にしない。"
    status: flagged-unverified
    verdict: UNCERTAIN
    classification: WARNING
    deferred_to: 06-release-validation
  - statement: "復帰や失敗案内のために他アプリの入力先を奪ったり、編集中のダイアログを閉じて作り直したりしない。"
    status: flagged-unverified
    verdict: UNCERTAIN
    classification: WARNING
    deferred_to: 06-release-validation
  - statement: "確認できていない原因や復帰成功を利用者へ断定しない。"
    status: flagged-unverified
    verdict: UNCERTAIN
    classification: WARNING
    deferred_to: 06-release-validation
---

# Phase 4: 起動制御と既存画面への復帰 検証報告

**目標:** 利用者が2回目に PageFolio を起動しても作業画面が増えず、進行中の作業を保ったまま既存画面へ戻れる。
**判定:** passed（Phase 4の実装/自動受入範囲21/21。Phase 6の実機受入は未実施）
**検証種別:** 04-06 gap closure後の再検証。前回は19/21、CR-01に由来する2truthがFAILED。コミットなし。

**3 flagged prohibitions — unverified-prohibition — human review recommended.** 禁止事項3件とedge5件は未解決のままPhase6へ明示移管しており、リリース承認を意味しない。W not-runをpassへ変更していない。元の5成功基準すべてを対象とし、実EXE/人手部分の実施時期だけを承認済みROADMAP改訂に従って分離した。Phase 4の合格はこの移管を条件とし、最終人手受入の代替にはしない。

## Goal Achievement

### Observable Truths

ROADMAP5基準を先頭に置き、全PLANの追加truthを重複統合した。表のVERIFIEDは現行Phase4自動範囲。最終実機部分は後掲Deferred Itemsを参照する。C/F/Nはそれぞれtests/test_startup_control.py / test_startup_focus.py / test_startup_notice.py、Wはtest_startup_windows.pyを指す。

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | 同一 Windows ログインセッションで、対応版同士の別版・別配置・Python/EXE 混在を含む連続・同時起動をしても、編集画面は1つだけになる。 | VERIFIED（実装/自動範囲） | __main__.py:19 claimがroot生成前、__init__.py遅延import。win32:430固定Local名。W:552同時起動、:730両入口/別配置9組、:756版/配置/frozen identity。実EXE/別sessionはPhase6 |
| 2 | 正常終了・強制終了・起動途中の異常終了後に再起動でき、終了確認をキャンセルした場合は既存画面がそのまま使用できる。 | VERIFIED | main finallyでroot破棄後close、controlのroot不存在検証。04-06では部分descriptor/tokenの取得直後登録と逆順解放を追加し、test_backend_constructor_stage_failure_releases_acquired、test_token_information_failure_closes_acquired_handle、test_constructor_failure_cleanup_allows_restartで再確認 |
| 3 | 排他判定または既存画面への連絡に失敗した場合、利用者は「起動済み」と異なる理由を認識でき、後続起動は追加画面を作らず有限時間で終了する。 | VERIFIED（04-06後） | __main__.py:19-42で構築OSErrorをTk前に捕捉し、startup_notice.py:77-101の独立Win32NoticeBackendから固定check_failedへ到達。実main→native窓、追加編集画面0・案内1・foreground不変をtest_constructor_failure_real_main_nonactivate_noticeでassert。通知不能は両入口exit1 |
| 4 | 2回目の起動で最小化した既存画面が復元され、OS が許せば前面に出る。前面化を拒否された場合も視覚通知から既存画面を見つけられる。 | VERIFIED（実装/自動範囲） | FocusRestorer.restore、_restore_placement/_foreground_window、flash3回250ms＋1000ms停止。F::test_placement_returns_to_last_non_iconic_state、test_foreground_denied_only_flashes_and_stop_never_retries。実OS目視はPhase6 |
| 5 | 未保存編集、Undo/Redo、進行中の OCR、開いているモーダル操作を保ったまま既存画面で作業を続けられる。 | VERIFIED（実装/自動範囲） | F::test_working_state_real_pdf_history_and_blobs_continueで実PDF/Blobと4手Undo/Redo、test_ocr_same_engine_worker_and_generation_complete_after_restoreで同じworkerの完了、test_modal_grab_and_native_popup_preserve_input_focus。W:999実main回帰。人手内容照合はPhase6 |
| 6 | 完了live/archiveのvalidated義務と未完了draft開発を両立する | VERIFIED | test_gsd_dod.py:149現行Phase/Progress/件数/日付照合、:234 archive継続。test_live_completion_requires_consistent_evidenceとtest_live_incomplete_does_not_require_validation実走 |
| 7 | D-01 正常復帰でヘッダー/OCR進捗を維持しterminalを確認する | VERIFIED | _dispatch_pendingはstatus/docを書かない。win32:894 acceptedだけでは戻らずterminal照合。C::test_accepted_is_not_terminal_and_eight_requests_restore_once、Fの履歴/OCR継続 |
| 8 | D-05/D-06 準備/接続/送受信/ACKが共通5秒期限を持つ | VERIFIED | started_tickをmain入口で取得、win32:820で一度だけ+5000、_ioに残余期限。C::test_each_batch_member_keeps_own_deadline、W07実測5000ms |
| 9 | D-08 失効queue/世代の要求は後で前面化しない | VERIFIED | control._validを受信/dispatch/副作用直前に適用。C::test_busy_main_thread_discards_expired_request、test_generation_change_invalidates_queued_requests、F::test_each_side_effect_rechecks_deadline_and_nested_restore_is_inert |
| 10 | D-07 確認済み初期化中process死亡後だけ原子的claimを1回試す | VERIFIED | control:78 state/handle signaled/attempted/deadline、win32:591 atomic wait。C::test_confirmed_initializing_process_death_claims_only_once、W:582競合候補 |
| 11 | D-03 要求とterminal後500ms連打を延長なしに集約する | VERIFIED | control:131固定first_terminal_tick、pending/cacheの重複照合。C::test_fixed_cooldown_does_not_extend_and_edge_is_independent、test_accepted_is_not_terminal_and_eight_requests_restore_once |
| 12 | D-02 最小化前の最大化/通常geometryへ戻す | VERIFIED | focus._remember_window_stateとrestore。F::test_placement_returns_to_last_non_iconic_state |
| 13 | D-04 直前の生存入力先を維持する | VERIFIED | focus._remember_focus/_focus_widget、completed後だけfocus_set。F::test_focus_child_preserved_and_toplevel_focus_does_not_overwrite |
| 14 | D-13 grab/native最深modalと入力/選択を維持する | VERIFIED（自動範囲） | focus._select_activation_target/owned_popup、widget再作成なし。F::test_modal_grab_and_native_popup_preserve_input_focus。実messagebox/入れ子操作はW05 |
| 15 | D-14/D-15/D-16 拒否は有限点滅だけで自動再前面化しない | VERIFIED | flash flags=2/count3/250ms、_schedule_stopはSTOPだけ。F::test_foreground_denied_only_flashes_and_stop_never_retries、N::test_success_and_foreground_denial_never_enter_notice_boundary |
| 16 | D-09 確認済み理由と次の操作で案内する | VERIFIED（04-06後） | 初期化失敗は未確認ownerを仮定せずCHECK_FAILED固定文言を既存LANG→native通知へ渡す。test_backend_constructor_failure_uses_independent_notice、実Win32 descriptor故障試験が合格。機密例外本文は表示/診断へ渡さない |
| 17 | D-10 手動閉鎖/初回10秒自動閉鎖 | VERIFIED（自動範囲） | NativeNoticeLifetime WM_LBUTTONUP/WM_CLOSE、固定deadlineとtimer。N::test_notice_fixed_deadline_9999_10000、W::test_constructor_failure_manual_close_keeps_foreground。新窓実クリックはW09 |
| 18 | D-11 同原因をprocess間で集約し期限を更新しない | VERIFIED | NoticeLeaseの原因hash、初回deadline更新拒否、visible identity検証。W::test_constructor_failure_notice_dedupは旧新両順で各8processの表示1と初回期限不変をassert |
| 19 | D-12 案内表示/閉鎖が入力先を変えない | VERIFIED（自動範囲） | NOACTIVATE/TOOLWINDOW/MA_NOACTIVATE/SW_SHOWNOACTIVATE、W::test_constructor_failure_real_main_nonactivate_noticeと手動閉鎖試験でforeground HWND前後一致。実入力/新通知再受入はW09/10へ移管 |
| 20 | D-01〜16の自動/実機/未実施を分け、Phase6へ追跡する | VERIFIED | 04-WINDOWS-UATと04-05-EVIDENCEの各W、06-UAT-CARRYOVER全行、VALIDATION実走。not-runを維持 |
| 21 | A1〜A5成立性を本番Windows API/生証拠で確認する | VERIFIED | 04-HUMAN-EVIDENCEのA3前面HWND/1937ms/10000ms、A4両順identity/全4資源、tracerのA1期限/取消し、A2部分snapshot/生成時刻拒否、A5親子tick。旧primitive証拠の適用範囲を保持 |

**Score:** 21/21。04-06の追加truth 6件はtruth2/3/16〜19の具体化として確認し、重複加算しない。禁止事項3件は肯定truth得点に混ぜず、UNCERTAIN（WARNING）を保持する。

### Deferred Items

| Item | Addressed In | Evidence |
|---|---|---|
| W01〜W12人手部分、別session、DPI/UAC、OS拒否、実EXE | Phase6 V110-QA-02 | ROADMAP Phase6 SC4と06-UAT-CARRYOVER全行。W11準備不能not-runを維持 |
| 15.5秒予算の負荷適合性 | Phase6 W07b | 15609ms（109ms超過）/15140ms両方保持、WR-01 deferred |
| 禁止事項3件flagged-unverified、edge5件unclassified/unresolved | Phase6 V110-QA-02 | 移管正本の照合義務。descriptor無し項目を勝手にresolvedへしない |

### Required Artifacts

CLI verify.artifactsを全6 PLANに対して実行し、宣言19件すべてexists/substantive合格（既存13件＋04-06の6件）。重複パスは実体を精読し、main/notice/win32の呼出しと実試験まで確認した。

| Artifact | Expected | Status | Details |
|---|---|---|---|
| startup_control.py | claim/queue/期限/ACK | VERIFIED | mainが構築しbackendを注入、attach_tk→poll→dispatchが使用 |
| startup_win32.py | OS所有権/IPC/native案内 | VERIFIED | 本番factoryとしてmainから使用。04-06でWin32NoticeBackend基底を追加し、起動所有権なしで同じ通知lease/ACLを再利用 |
| startup_focus.py | 同一appの復帰 | VERIFIED | main:63同じappで構築、backend.focus_restorerへ接続 |
| startup_notice.py / lang.py | 三分類の固定案内 | VERIFIED | backend.show_notice→show_startup_failure→LANG→native描画。独立初期化失敗はshow_startup_initialization_failure→Win32NoticeBackend→同じ描画へ接続 |
| test_startup_control/focus/notice/windows.py | 状態/障害/実Windows検証 | VERIFIED | pytest通常収集と手動harnessを分離。04-06のconstructor/初期化/期限25件は対象Windowsで実走しskip0 |
| 04-TRACER-EVIDENCE / WINDOWS-UAT / VALIDATION / 04-06-EVIDENCE | 実測と被覆 | VERIFIED | 生JSON参照、5製品/試験ファイルのSHA-256を独立照合し全件一致。not-run分離、validate-phase再監査25件 |

### Key Link Verification

CLI verify.key-linksは旧14件に加え04-06の4件も「Target not referenced in source」を返した。Pythonのドットimport/コンストラクタ注入と日本語viaの文字列検査による偽陰性であり、以下の実呼出しと名前付き実試験を精読してWIREDと判断した。CLIの否定結果自体は隠さない。

| From | To | Via | Status | Details |
|---|---|---|---|---|
| __main__ | control/backend | StartupCoordinator(Win32Backend()) | WIRED | main:19 factory注入→claim→primaryだけroot/app構築→finally close |
| control | win32 | self.backend | WIRED | claim/listen/request_activation/restore_window/closeの実呼出し。DIなのでcontrolからbackend importは不要 |
| control | Tk callback | attach_tk/_poll/_dispatch_pending | WIRED | main:66 after_idle→attach、control:196 main-thread poll→restore、terminal_cacheをworkerがACKへ返す |
| __main__/app | focus | 同じapp/root | WIRED | main:63〜65でappとbackendの両方に同一restorer登録、FocusIn/Configure観測はrestorerが所有。appにimportを増やす必要なし |
| focus | win32 | placement/popup/foreground/flash | WIRED | restore内で全副作用前currentを再照合 |
| main | notice→win32 | backend.show_notice | WIRED | main:27→win32:1089→notice.show_startup_failure→lease/display_notice |
| notice | lang | LANG[language][keys[reason]] | WIRED | notice:43〜55固定文言をnative本文/closeへ渡す |
| windows test | main | runpy/入口の実行 | WIRED | 両入口/relocated子bootstrapとexpected-ownerを使用 |
| WINDOWS-UAT | VALIDATION | W/D/要件ID | WIRED | 同一W01〜12とD01〜16、実測JSON/移管正本参照 |
| __main__ | startup_notice | show_startup_initialization_failure | WIRED | main:33で実呼出し、notice factoryは1回。構築OSErrorからcheck_failed/notification_unavailableへ分岐 |
| startup_notice | startup_win32 | Win32NoticeBackend | WIRED | notice:79-82で遅延importしたfactoryを生成し、NoticeLease/display_notice/closeへ接続 |
| startup_win32 | startup_notice | show_startup_failure | WIRED | win32:522-526のshow_noticeがStartupOutcomeを渡す。独立失敗も同じ関数を使用 |
| Windows subprocess test | mainとrunpy | 両Python入口 | WIRED | windows:311-324のmodule/script起動と実main native通知・exit結果をassert |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| ownership | snapshot identity/state | Win32 mutex/mapping＋OS process handle | yes | FLOWING |
| activation | ActivationRequest/Reply | 実pipe→queue→同じTk root→terminal ACK | yes | FLOWING |
| focus | widget/placement/popup | 既存app/rootのFocusIn/Configure/grabとOS HWND | yes | FLOWING |
| notice | reason/text/deadline | 起動結果＋検証済みowner→LANG、GetTickCount64、原因別共有snapshot | yes | FLOWING（固定文言は設計どおり） |
| 独立notice | check_failed/text/期限 | mainの構築OSError→StartupOutcome→LANG、OSのtickと共有NoticeLease | yes | FLOWING。起動backend未完成でも起動ownerを仮定しない |

DB/APIからの業務データ取得は本フェーズに該当しない。空配列/ハードコード値で実状態を代用する未接続経路なし。

### Behavioral Spot-Checks

本担当は常駐サービスを起動せず、前回の名前指定試験に加え、04-06のconstructor/初期化/期限の25件を独立プロセスで実行した。新規対象試験のpytest実測は9.75秒。既存PyMuPDF ByteString警告1件のみでfailure/ERROR/対象skip0。前回の名前指定試験結果も履歴として下表に保持する。

| Behavior | Command | Result | Status |
|---|---|---|---|
| busy失効/1回引継ぎ/実PDF履歴/OCR継続/通知期限更新拒否 | pytest -q の該当5 named node IDs | 7 passed / 0.15秒 | PASS |
| terminal/cooldown/解放順/placement/focus/modal/拒否/理由/8合流/失敗cleanup | 該当10 named node IDs | 21 passed / 0.07秒 | PASS |
| DoD完了/未完了、要求別期限/世代/副作用再確認、正常時通知なし、9999/10000境界 | 該当8 named node IDs | 19 passed / 0.13秒 | PASS |
| 起動関連全204件＋修正後全件1629件 | 既存validate-phaseと04-06の実走記録（本検証では再実行なし） | 204 passed /190.22秒、修正後1629 passed /217.71秒、failure/ERROR/skip0 | PASS |
| backend constructor失敗時の案内と部分解放 | `.venv/Scripts/python.exe -m pytest -q tests/test_startup_notice.py tests/test_startup_windows.py -k "constructor_failure or backend_constructor or initialization_notice or initialization_cleanup or notice_deadline"` | 25 passed、102 deselected、1 warning、9.75秒、exit0 | PASS（CR-01解消） |

全件結果はSUMMARYの主張を証拠に代用せず、04-06-EVIDENCEのコマンド/終了値と対象5ファイルの現在SHA-256一致を照合した。本検証で25件を独立実走した。Windows実測の数値はJSON/テストassertionと照合した。全件120秒目標超過も保持する。04-06のREDはassertion失敗コマンドとexit値が記録されているが、JUnitの機械classifierは未実行であり機械判定済みと記さない。

### Probe Execution

該当probe-*.sh宣言/実体なし。Pythonの通常試験と明示A/W harnessが実行経路。外部サービス・migration shell probeフェーズではないためStep7c該当なし。

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| V110-START-01 | 01/02/05 | 同session共通ID・対応版/配置/入口 | SATISFIED（Phase4範囲） | truths1/21、同時/9組。実EXE/別session人手はPhase6 |
| V110-START-02 | 01/02/05/06 | 終了/異常終了後再起動・cancel | SATISFIED（Phase4範囲） | truths2/10、root破棄/解放順、部分初期化資源の逆順解放と再起動 |
| V110-START-03 | 01/02/04/05/06 | 判定/連絡失敗の識別・有限終了 | SATISFIED（Phase4範囲） | truths3/16、constructor失敗から独立check_failed通知と通知不能exit1を実main/両入口で確認。負荷予算は別のWR-01 |
| V110-FOCUS-01 | 01/03/04/05 | 復元/許可前面化/拒否強調 | SATISFIED（Phase4範囲） | truths4/12/15、OS実目視はPhase6 |
| V110-FOCUS-02 | 01/03/05 | 作業/Undo/OCR/モーダル維持 | SATISFIED（Phase4範囲） | truths5/7/13/14、実PDF/worker継続 |

全PLANの宣言を合併すると5件、要件台帳のPhase4割当も同じ5件。ORPHANED 0。台帳更新/Shared-ID判定は親の担当。

### Decision Coverage

CLI check.decision-coverage-verifyを再実行: honored16/total16、not_honored=[]。
All trackable CONTEXT.md decisions are honored by shipped artifacts.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped on Windows | Circular | Assertion Level | Verdict |
|---|---|---|---|---|---|---|
| startup_control | START01〜03/FOCUS01 | yes | 0 | no | Behavioral、期限/副作用回数/順序 | 合格 |
| startup_focus | FOCUS01/02 | yes | 0 | no | Behavioral、実PDF hash/Blob identity/worker完了 | 合格 |
| startup_notice | START03 | yes | 0 | no | Value/Behavioral、初期化失敗・部分descriptor/token解放・理由/期限/所有権 | 合格 |
| startup_windows | 全5件 | yes | 0 | no | 実main/Win32/PID/画面数/状態比較、旧新8process集約と両入口 | 合格（人手部分別） |
| gsd_dod | 品質ゲート | yes | 0 | no | 合成負例で違反理由と完了状態 | 合格 |

Windows外skipifはOS固有試験の条件であり対象Windowsの検証免除にはしない。fixture生成は入力の一時PDF/設定等であり、実装から正解値を自己生成する循環比較ではない。strong assertion不足0、coincidental-relianceとして特定すべき未宣言前提なし。

**反証確認:** 旧`test_tracer_e2e_api_denial_does_not_construct_app`はbackend完成後のclaim拒否だけを検査し、constructor拒否時の案内を証明しなかった。04-06の新試験はこの経路を実main/実Win32で通し、token/descriptor部分失敗、通知factory/lease/表示/解放/診断失敗を別々に検査した。実クリック/DPI/UACは自動試験の範囲外としてPhase6へ保持する。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| tests/test_gsd_dod.py | 216/225 | TBDという文法リテラル | Info | 未完了件数表記の解析用。負債コメントではない |
| startup_win32.py | 287/307/819 | 並行負荷で予算超過 | WARNING / WR-01 | 承認済みPhase6再評価へ移管、元数値保持 |
| __main__.py | 旧20 | backend構築失敗が案内境界を迂回 | 解消済み / CR-01 | 04-06の独立案内と25件実走で閉鎖。旧exit1再現は履歴としてREVIEWに保持 |

未参照FIXME/XXX/TBDコメント、placeholder、空handlerによる未実装は検出なし。SECURITYは22/22 closed、blocking high0。UIは静的6柱監査済み、実表示not-runを明示。

### Human Verification Required

現在のPhase4範囲には残件なし。ユーザー操作が必要なW全行・3禁止事項・5edgeは、承認済み再計画により06-UAT-CARRYOVERを単一の引受先とする。人手検証不要という判定ではない。実EXE、別session、DPI/UAC、新通知実クリック/入力継続、OS拒否と15秒後の観測が全件passするまでPhase6完了・リリースを停止する。

### Gaps Summary

現在のPhase4実装/自動受入範囲にBLOCKERはない。前回FAILEDだったSC3/D-09の2truthは04-06で解消し、constructor失敗時の独立案内・部分資源解放・通知不能の非zero終了を実コードと25件の独立実走で確認した。3禁止事項はflagged-unverified、5edgeはunclassified/unresolved、W人手部分はnot-runを維持し、承認済みPhase6のリリース停止条件へ引き継ぐ。WR-01の並行負荷15609ms超過と単独15140msも維持する。コミットなし。

_Verifier: gsd-verifier（インライン、再委任なし）_
