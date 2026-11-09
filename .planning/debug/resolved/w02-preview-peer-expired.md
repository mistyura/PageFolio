---
status: resolved
trigger: "w02-preview-module-peer-expired: Phase 06 06-05-02 G1 の W02/preview@module(python -m pagefolio の二次起動)で、二次起動が一次側に受け付けられた(起動accepted b7d47b3b60e143698bd8ae655dc326dc, deadline=28860484)後、5秒で connection_failed os_error=233 となり expired 通知(elapsed 15078ms)。"
created: 2026-10-25
updated: 2026-10-28
---

# Debug: W02/preview@module 二次起動の期限切れ(os_error=233)

## Symptoms

- **expected:** 二次起動(`python -m pagefolio`)で一次PageFolioが前面に戻り、入力先が中央プレビューのCanvas(`.!panedwindow.!frame2.!frame2.!canvas`)のまま。harnessの focus-result.json が生成され focus_correct=true。
- **actual:** 二次起動は一次側の listener に接続し `起動accepted: b7d47b3b60e143698bd8ae655dc326dc / deadline=28860484` を得たが、その後 `起動連絡失敗: os_error=233`(ERROR_PIPE_NOT_CONNECTED)で terminal_result=connection_failed(elapsed 5000)、notice_reason=expired の通知を10秒表示。peer result は `{"constructed":0,"restored":0,"status_preserved":true,"result":"expired","elapsed":15078}`。一次側 stderr は `起動terminal: b7d47b3b60e143698bd8ae655dc326dc / expired / deadline=28860484 / tick=28871062`(締切の約10.6秒後に処理)。focus-result.json なし。前景は二次起動中にPageFolioへ戻らず、期限切れ後に利用者のAlt+Tab(ForegroundStaging/タスクの切り替え)でPageFolioへ移った。
- **errors:** 二次起動側 `起動連絡失敗: os_error=233`。一次側 `起動rootの後始末: cannot invoke "winfo" command: application has been destroyed`(終了時)。二次起動側 traceback.log は notice 表示中の faulthandler 10秒タイムアウトダンプ(startup_win32.py:1920 show)。一次側 traceback.log は10秒ごとの定期ダンプで main thread=tkinter mainloop(`pagefolio/__main__.py:81`)、`_serve` 8スレッド=`startup_win32.py:836` WaitForSingleObject。
- **timeline:** 2026-10-25 15:24:31〜15:25:50(source_commit 36909a8)。同手順の W02/preview@script(15:01、clean再走)、W02/settings@module(15:17)、W02/thumb@module(15:20)は直前に正常完了。初観測。
- **reproduction:** `.venv/Scripts/python.exe .planning/phases/06-release-validation/06-05-drivers/uat_row.py --row W02/preview@module`(harness: `tests/test_startup_windows.py --uat start --case preview` → `peer --entry module`)。1回のみ観測、再走未実施。

## 前提・制約

- 手順汚染なし: 入力監視で peer 完了までに PageFolio へのボタン押下・キー押下 0件(procedure_verdict=clean)。
- 元ファイル(設定/2prompt)は無変更(originals_unchanged=true)、所有PIDは回収済み(alive_after 空)。
- 過去debug(`dep-05-regression.md`, `simultaneous-owner-missing.md`)に os_error=233 / connection_failed の記録なし。別症状の可能性が高いが未確定。
- Phase 06 の受入は停止中。この行は pass にしない。DEP-05・owner_missing・通知前景不一致・Tcl警告・未分類edge の同種再発ルール(期限延長・skip・除外で通さない)を維持する。
- 証拠原本を上書き・削除しない。製品修正はユーザー承認後のみ。pyproject.toml 編集禁止。

## Evidence

- timestamp: 2026-10-25T06:30Z
  source: orchestrator(初期収集)
  - 保全コピー: `.planning/debug/w02-preview-module-peer-expired-evidence/run-pagefolio-uat-p30x89fr/`(24ファイル、原本とSHA256一致)と session JSON `W02_preview_at_module-20261025T062551Z.json`
  - 原本: `.planning/tmp/pagefolio-uat-p30x89fr/`(peer-5db1e86509e842749a3a183e67bf3fbf/ と uat-owner-preview/)
  - 一次: pid 34016, ready_tick 28845609, started_tick 28842859
  - 二次: pid 26444, started_tick 28855484, accepted deadline 28860484(=started+5000), notice shown_tick 28860562, deadline_tick 28870562
  - 一次の terminal 処理 tick 28871062 = 二次の notice 終了(28870562)の 500ms 後
  - listener 実装: `pagefolio/startup_win32.py` `_serve`(L819〜)。accepted 返信後、deadline まで25msごとに callback をポーリングし、terminal を書いて相手の確認を読む

- timestamp: 2026-10-25(debugger 継続調査・tick と壁時計の対応づけ)
  checked: 原本の更新時刻(NTFS mtime、15.6ms 量子化)と各ファイル内の tick を突き合わせた(読み取りのみ)。
  found: |
    一次 ready 書込み JST 15:24:35.0724 = ready_tick 28845609。二次 ready(notice 表示)JST 15:24:50.0255 = shown_tick 28860562。二次 result.json/resource-audit.json JST 15:25:00.0253 = closed_tick 28870562。
    壁時計差とtick差は 14953.07ms vs 14953ms、9999.83ms vs 10000ms で一致(段差なし、±16ms)。以後 wall(T) = 06:24:50.0255Z + (T-28860562)ms で換算する。
    二次開始 28855484 = 06:24:44.947Z / accepted deadline 28860484 = 06:24:49.947Z / notice 閉鎖 28870562 = 06:25:00.025Z / 一次の初回 terminal 処理 28871062 = 06:25:00.525Z。
    入力監視(session JSON)の前景遷移: PowerShell→ForegroundStaging 06:25:00.178(Alt+Tab 押下)→タスクの切り替え 00.205→ForegroundStaging 00.522→PageFolio(hwnd 987788, TkTopLevel) 00.530(8ms ポーリング検出)。この間(peer 開始 06:24:44.321〜06:25:00.178)は前景遷移ゼロ、マウスイベント 0、PageFolio 前面中のキー 0。
  implication: 一次が要求を初めて処理した瞬間(06:25:00.525±0.02)は、PageFolio が Alt+Tab 解放で活性化した瞬間(06:25:00.523〜00.531)と ±25ms で一致する。notice 閉鎖(06:25:00.025)とも正確に 500ms 差だが、一次側コードに「notice 閉鎖を起点とする 500ms 処理」は無い(startup_win32.py の 500 は PendingIO.cancel の待機と _validate_reply の合体判定のみ)。活性化との一致は強い相関であり因果の証明ではない(1観測のみ)。

- timestamp: 2026-10-25(一次の処理経路)
  checked: 一次 result.json(`restored: 0`)、focus-result.json 不在、stderr.log の行順、`pagefolio/startup_control.py` `_receive`/`_coalesce_request`/`_dispatch_pending`/`_finish`/`close`、`tests/test_startup_windows.py:2657-2667`(Backend.restore_window)。
  found: |
    Backend.restore_window は先頭で counts["restored"] += 1 し、その後 app._focus_after が focus-result.json を書く。一次の restored=0 かつ focus-result.json 無し = restore_window は一度も呼ばれていない。
    stderr の行順は「起動terminal」→「起動rootの後始末」。close() 経由の _finish は main() の finally で root 後始末より後に出るため、この terminal 行は close() ではなく _poll→_dispatch_pending(Tk スレッド)の初回実行で出ている。tick=28871062 は締切 28860484 の 10578ms 後。
    _dispatch_pending の経路は「queue の要求が _valid 不成立(締切超過)→ _finish(item, "expired", tick)」(startup_control.py:213-216)。
    _receive は accepted 返信時点で要求を queue(または active_batch)へ入れており、二次の「起動accepted」ログがあるので、要求は締切前に一次の queue に存在していた。通常行の二次 elapsed は 63/78/94ms(通過 3 行)で、要求到着は二次開始の約 0.1 秒以内と推定される。
  implication: 一次の Tk メインスレッドは、要求受理(二次開始+約0.1秒 = 06:24:45.0)から 06:25:00.525 までの約 15.5 秒間、50ms 周期の _poll→_dispatch_pending を実行しなかった。締切(5 秒)内に処理されなかったのが近因。

- timestamp: 2026-10-25(listener 側の挙動と 233 の機序)
  checked: `pagefolio/startup_win32.py` _serve L819-889、request_activation L891-997。
  found: |
    _serve は accepted を書いた後、`while not stop and tick < deadline:` で 25ms ごとに callback(request) を呼ぶ(L867-873)。_receive は pending が残る限り accepted を返し続けるため break しない。
    締切到達でループを抜けると `if self.tick_ms() < deadline and not stop.is_set()`(L874)が偽になり terminal を書かず、finally の DisconnectNamedPipe(L882)で切断する(設計どおり。listener 単独で terminal を作る経路は無い)。
    二次側は accepted ログ後に `_read_frame(deadline)`(L979)で読み待ちしており、サーバの強制切断で GetOverlappedResult が 233 を返すと PendingIO.finish が WinError を投げ、L991 の `except Exception` が last_os_error=233・connection_failed を返す。自身の締切タイムアウト(L989 TimeoutError→expired)と切断のどちらが先に起きるかは締切境界の競合で、今回は切断が先。_wait_for_terminal(startup_control.py:104-106)が tick≥started+5000 を expired に上書きするため、利用者に見える notice_reason は expired。
  implication: 233/connection_failed は「一次が締切まで terminal を作れなかった」ことの副次症状であり、独立した不具合ではない。二次側の分類は締切境界で connection_failed と expired が競合する弱点(診断上の不整合 = terminal_result と notice_reason の不一致)がある。

- timestamp: 2026-10-25(faulthandler ダンプ)
  checked: 一次 traceback.log(7 ダンプ。process 開始 15:24:32.3 起点で 10 秒周期 = 15:24:42.2 / 52.2 / 25:02.2 / 12.2 / 22.2 / 32.2 / 42.2 JST)。
  found: 7 ダンプとも 8 本の _serve スレッドが startup_win32.py:836(listen の WaitForSingleObject 50ms)、メインスレッドが tkinter/__init__.py:1649 mainloop(`__main__.py:81`)で、他の Python フレームなし。締切後(06:24:49.9)〜復帰前(06:25:00.5)の 06:24:52.2 のダンプも同じ。
  implication: 8 スレッドの 836 待ちは締切後の通常の待機状態(ブロックではない)。メインスレッドは Python コールバック内ではなく mainloop の C 層(待機または C 層処理)にいた。ただし _poll は 50ms 周期で短時間なので、1回のダンプだけで「Python が動いていない」とは言い切れない(判定は上の restored=0 / 初回処理 tick による)。

- timestamp: 2026-10-25(環境・外部要因の確認)
  checked: Windows イベントログ全 27 ログ(15:24:25〜15:25:10 JST)、VHDMP/NTFS 集計イベント。
  found: |
    Kernel-General の時刻変更(Event 1)・W32Time・Application Hang(1002)等は 0 件。事象窓内の記録は Service Control Manager 7040(BITS 開始種別変更 15:24:57)、WMI-Activity 5857(WmiPerfClass 15:24:52.5 / WMIProv 15:25:02.7 / WmiPerfInst 15:25:06.3)、PowerShell コンソール起動(15:24:35.6、driver の pids_with_marker と推定)、WinRM(145/142/161/254、15:24:57〜15:25:02)のみ。
    システムは外付けドライブ上の VHDX(Z:\BUFFALO SmartTwins\...\DISK01.vhdx)から起動しており、ページファイル 0 バイト。直前 1 時間(〜15:24:42)の VHDMP 集計は Write 平均 8ms・Read 平均 11ms・Flush 平均 92ms で、1〜5 秒の I/O が Write 42・Flush 3・Read 2 件、5 秒以上は 0 件(高待機時間 IO 0)。
  implication: 時計段差は無い(Tcl after の壁時計依存の線は支持なし)。ストレージ遅延は存在するが、観測された最大は 5 秒未満で、15.5 秒の停止を直接説明しない。因果は不明の相関データとして記録するのみ。

- timestamp: 2026-10-25(隔離実験 1: メニューモードで Tcl after が止まるか)
  checked: scratchpad `tk_menu_stall.py` / `tk_menu_stall2.py`(自プロセスの画面外窓 +メニューバー付き。PostMessage の WM_SYSCOMMAND SC_KEYMENU で Alt 単独相当のメニューモードを再現。GetGUIThreadInfo で GUI_INMENUMODE を確認)。.venv Python 3.15.1 / Tk 9.0.4。
  found: |
    control(介入なし): after(50) ビート max gap 0.064s。
    keymenu(メニューバーのメニューモード、flags=4 が 1.02〜4.03s): ビート 41 回/2.6s(control 42)、max gap 0.065s。
    sysmenu(システムメニューのモード、flags=12): ビート 42 回、max gap 0.079s。
  implication: PageFolio は tk.Menu のメニューバーを持つ(app.py:328-334)が、Windows のメニューモード(Alt 単独で入る)では Tcl after は止まらない。Alt+Tab 時の Alt 単独タップ→メニューモード仮説は反証。

- timestamp: 2026-10-25(隔離実験 2: 背景の素の Tk 窓の after ソーク)
  checked: scratchpad `tk_soak.py`(非表示 / 画面外窓、各 150 秒、同時 2 本、after(50) と別スレッド sleep(0.05) のギャップ、Tcl clock と monotonic の乖離を記録)。
  found: 両方とも 2400 ビート、0.2 秒超のギャップ 0 件、スレッド sleep 側も 0 件、Tcl clock 乖離 0 件。
  implication: 素の Tk(Tcl 9.0.4 / Python 3.15.1)の after が背景で自発的に止まることはない(150 秒×2)。停止は PageFolio 固有の状態(窓の非活性化、tkinterdnd2、メニューバー、実運用の Win32 状態など)に依存するか、稀な事象。1/5 程度の頻度を直接再現できてはいない。

- timestamp: 2026-10-25(比較: 同一 harness の通過行)
  checked: 06-05-evidence の W02 preview@script(060315Z)/ settings@module / thumb@module の前景遷移と peer 結果。
  found: 通過行は Enter(peer 開始)から 0.77〜0.88 秒後に「PowerShell→PageFolio(または設定ダイアログ)」の前景遷移が起き(restore 完了)、二次 elapsed は 63/78/94ms、focus-result.json あり。失敗行だけが peer 中の前景遷移ゼロ。失敗行の Alt+Tab(awaiting-enter)は PageFolio→PowerShell が 0.62 秒で、通過行(0.9〜1.2 秒)より短かったが、これは判別要因とは言えない(1 観測)。
  implication: 同じ harness・同じ一次ロール(uat-owner-preview)・同じ手順で、1/5 だけ要求が処理されない。entry=module の二次側コードは一次の停止に関与しない(一次は同一コード)。利用者の回答(foreground=出た 等)は、期限切れ後に手動の Alt+Tab で PageFolio を前面化した後の観察であり、製品の復帰成功を示さない。

- timestamp: 2026-10-25(利用者の決定・チェックポイント回答)
  source: orchestrator が AskUserQuestion で利用者に提示した結果
  decision: 利用者は 案A「診断を足して再走」を選択。製品コード(pagefolio/*)・tests/*・pyproject.toml は変更しない。読み取り専用の診断を driver 層(uat_row.py か隣の自己完結ヘルパー)に追加し、W02/preview@module を 5〜10 回再走して発生頻度のみを見る(受入証拠ではない)。
  constraints: |
    - 診断出力は 06-05-evidence/debug-w02-preview-peer-expired/ に分離し purpose を "debug-frequency"(受入ではない)と明記する。06-05-evidence/ の既存原本は上書きしない。
    - SendInput / SetForegroundWindow / SetCursorPos など前景・入力を変える API は使わない。SendMessageTimeoutW(WM_NULL) は別フラグ(既定 OFF、2 回目の再走以降用)。
    - 既存 driver の挙動と証拠フォーマットは維持(追加フィールドのみ)。コミットはしない。

- timestamp: 2026-10-25(案Aの実装と機構確認: 読み取り専用の診断を driver 層へ追加)
  changed: |
    `.planning/phases/06-release-validation/06-05-drivers/uat_row.py`(追記のみ。通常実行は不変)と新規 `.planning/phases/06-release-validation/06-05-drivers/ui_thread_probe.py`。pagefolio/*・tests/*・pyproject.toml・06-05-evidence/ の既存原本は未変更。コミットなし。sha256: uat_row.py f10d92d93ba1cde7ba7ef7a3e982e29dcae6ac2e82e1ed22009f2934d50d845d / ui_thread_probe.py 740a0bf709cbe19d91f7514f5e49ddfc5d4a69f40694180c5ee6a1354981eb8b(診断実行の session JSON の diagnostics に driver_sha256 / probe_sha256 として記録される。06-MANUAL-EVIDENCE.json の driver_sha256 は従来どおり旧値のまま)。
  design: |
    起動: `--diagnose-ui-thread`(`--diag-run N --diag-runs M` は記録用、`--diag-interval-ms` 既定100)。`--wm-null-probe` は別フラグ・既定OFF(OFF時は SendMessageTimeoutW を一度も呼ばない)。
    対象: harness start の manifest.expected_owner.pid(一次PageFolio)。作成時刻(FILETIME)で同一性を検証。OpenProcess は PROCESS_QUERY_LIMITED_INFORMATION、OpenThread は THREAD_QUERY_LIMITED_INFORMATION のみ。UIスレッドは EnumWindows+GetClassNameW で窓を持つスレッド(TkTopLevel 優先)。窓が無ければ最古スレッド。
    約100msごとの列: tick_ms(GetTickCount64=製品の deadline= / tick= と同じ時計)・壁時計(uat_row.now() と同書式)・elapsed_s(InputMonitor と同じ起点)・phase、GetGUIThreadInfo(flags/active/focus/capture/menu_owner/move_size)、GetThreadTimes(kernel/user)・QueryThreadCycleTime、NtQuerySystemInformation(ThreadState/WaitReason/ContextSwitches/WaitTime、プロセスの PageFaultCount/HardFaultCount/WorkingSet/IO、他スレッドの CPU 合計・実行中スレッド数)、K32GetProcessMemoryInfo(page fault の 2 系統目)、IsHungAppWindow。
    WM_NULL(ON 時のみ): awaiting-enter / peer / diag-hold / post-peer で約0.5秒ごと、タイムアウト200ms、SMTO_ABORTIFHUNG、別スレッドから。
    hold(診断のみ・既定30秒・`--diag-hold-s 0` で無効): 二次起動が completed でなかった回は、利用者に何も触らせず(クリックも Alt+Tab もしない)30 秒そのまま待たせ、phase=diag-hold の間も一次を観測し続ける(失敗時に「窓を活性化するまで止まったままか、自然に復帰するか」を見分けるため。通常の成功回には影響しない)。
    要求タイムライン: 一次の stderr.log を実時間で tail(「起動terminal」を見つけた tick を記録)。行の終了後に二次の stderr.log と合わせ、締切 tick・導出した開始 tick(=deadline-5000)・一次の terminal tick・締切からの遅れ・tick→壁時計換算・二次の os_error を作る(一次の「受理 tick」自体は stderr に出ないため推定として明記)。
    出力: 06-05-evidence/debug-w02-preview-peer-expired/ に session JSON(purpose=debug-frequency・acceptance=false)+ `.ui-samples.jsonl`(全サンプル)+ `-run-logs/`(一次/二次の stderr・traceback.log・result.json 等の写し)。`--summarize-diag` で再走の頻度表を出す。
  verification: |
    ruff check / ruff format 合格(uat_row.py は従来どおり `# ruff: noqa`、新規 ui_thread_probe.py は E501 のみ file-level noqa)、AST 合格、`--check-monitor` 28 項目合格(回帰なし)、`--check-diagnostics` 90 項目合格: 偽ネイティブ(解析・失敗経路・PID 再利用・プロセス終了・窓の出入り・分類 A〜D・サイドカー往復・timeline・WM_NULL 既定 OFF と phase 限定)、入力監視との時計/phase の整合、Row 配線(診断 OFF の行は session のキー集合が実際の前回行と同一・保存先が debug-* に分離・実 EXE 行は拒否・引数の組合せ検査)、使い捨て Tcl プロセスの実観測。scratchpad の rehearse.py(偽 harness+使い捨てプロセスで Row.run_python を通す)で session/サイドカー/ログの写しの生成も確認。
    実測値: Tk/Tcl の idle は ctx 切替 51〜78/s・CPU 0%・WM_NULL 応答あり。after コールバック内の time.sleep(6s): ctx 0/s・WM_NULL 11/11 timeout・IsHungAppWindow が 18/56 行で真・CPU 0・待機理由は idle と同じ UserRequest(=待機理由は単独では判別に使えない)。CPU バースト: cpu_share≈1.0・サイクル+2.98G。Win32 ポップアップメニュー: flags=0x14(menu|popup)・WM_NULL 応答あり・実 Tk(非表示ルート+メニューバー)の SC_KEYMENU: flags=4・ctx 125/s・WM_NULL 応答あり。UI が sleep 中に別スレッドが 1.5 秒 CPU を使うと UI ctx 0/s・他スレッド CPU 99.5%。64MB に触れる: page fault +16418・WS +65MB。サンプラ自身は 1 サンプル平均 5.4〜6.6ms(最大 49ms)・最大の空き 0.12s。tick と壁時計の差 最大 14ms。stderr の terminal 行の検出遅れ 47〜78ms。
  caveat: |
    Tk の窓は作成しただけで(withdraw でも -disabled でも)前景を一時的に奪うことを実測した(GetForegroundWindow が Tk 窓へ移り、プロセス終了で復帰)。このため機構確認の使い捨てプロセスは Tk ではなく Tcl のみ+非表示の STATIC 窓にし、前景が不変であることを確認した。実 Tk での確認は scratchpad で 1 回だけ実施(約 7 秒)。それ以前の隔離実験(tk_menu_stall*.py / tk_soak.py / menu_hidden.py / fg_check*.py)も同様に前景を一時的に奪っていた可能性がある。
  implication: 診断は未実機(実 PageFolio)では未実行。利用者の再走で、失敗回の一次 UI スレッドが (A) ctx 切替ゼロ+WM_NULL 無応答のネイティブ待機か、(B) ctx 切替は動いているのにタイマーだけ不発か、(C) CPU(UI または他スレッド)消費中か、(D) モーダルループ(flags)かを区別できる。成功回との差分(ctx 切替率・状態)も同じ列で比較できる。

- timestamp: 2026-10-25(利用者の診断再走・集計)
  source: 利用者が `--diagnose-ui-thread` 付きで W02/preview@module を再走 → orchestrator が `uat_row.py --summarize-diag` を実行 → debugger が session JSON と `.ui-samples.jsonl` を読み取り専用で再解析(scratchpad: analyze_diag.py)
  checked: `06-05-evidence/debug-w02-preview-peer-expired/` の 9 セッション(073830Z〜074610Z)。
  found: |
    073830Z = 手順汚染(awaiting-enter 中に PageFolio の窓枠操作。gui_flags=2 の 10 行と WrResource/WrUserRequest 13 行は窓移動の modal loop で、停止ではない)。頻度の母数に入れない。
    074104Z(run1・WM_NULL なし)= clean。peer completed 79ms、一次は締切前に処理(導出した要求開始 07:40:24.517 の約 63ms 後に terminal)。
    074228Z〜074610Z(run2〜8・WM_NULL あり)= peer completed 47〜94ms、一次の遅れなし。run5(074420Z)の keys-suspect は、awaiting-enter 中に PageFolio 前面で F4/F5 を計 3 回押した(キー到達確認の先行実施)ことによる。peer の結果(94ms 完了)には無関係。
    有効 8 回(clean 7 + keys-suspect 1)で期限切れの再発 0 件。WM_NULL の応答は全 7 回で 100% ok、最大 3.8ms。
  implication: 0/8 は「元の失敗が再現しなかった」ことしか示さない。修正の証拠ではない。下の run1 の停止区間と誘発形の偏りを併せて読むこと。

- timestamp: 2026-10-25(run1 の無スケジュール区間 1.901s の中身)
  checked: 074104Z の `.ui-samples.jsonl` 489 行(約 100ms 周期)・input_monitor の前景遷移・phase_log。
  found: |
    【区間】07:40:27.740(tick 33398281)〜07:40:30.2 の約 2.5 秒、phase=post-peer(peer は 07:40:26.16 に終了済み。要求処理の最中ではない)。UI スレッド(tid 16692, TkTopLevel)は Waiting / WaitReason=WrUserRequest。ctx 切替の増分は 24 行連続でほぼ 0(区間全体で 9 回のみ)、サイクル増分 0.00M、UI の CPU 0、他スレッド CPU 0(oth_cpu 125.0 のまま)、page fault 0、hard fault 0、gui_flags=0(メニュー/移動サイズ/ポップアップなし)、IsHungAppWindow は偽(5 秒未満のため当然)。
    【WaitTime】SYSTEM_THREAD_INFORMATION.WaitTime は KeTickCount(1 tick = 15.625ms)。2137490 × 15.625 = 33398281ms で、停止開始行の tick_ms と一致。つまり「27.74 に始まった 1 回の待機が約 1.95 秒続いた」ことを示す。
    【前景との対応】27.358 Alt+Tab 押下(PageFolio→ForegroundStaging)→ 27.375 切替UI(タスクの切り替え)表示 → 27.437 PageFolio の hwnd_active/hwnd_focus が 0 に(非活性化)→ 27.740 停止開始 = 27.744 切替先(PowerShell)が前景化と同時(±約 10ms)。
    【区間の中身】(1) 27.740〜29.641 の 1.9 秒は完全な無音(19 行)。(2) 29.682 の 2 回目の Alt+Tab 押下(PowerShell→ForegroundStaging)の直後、29.737 の行だけ ctx 9・サイクル +0.18M(CPU 数十マイクロ秒。Python の _poll を走らせる量ではない)・WaitTime が 2137614(= 33400218ms)に更新 = 短く起こされてすぐ同種の待機に戻った。(3) その後も 29.848〜30.136 は無音。(4) 30.213 の ForegroundStaging→PageFolio(再活性化)の直後の 30.246 の行で ctx +236・サイクル +25.4M・WaitReason=UserRequest(通常の待機)に復帰、hwnd_active/focus も復帰。
    【同形の操作でも毎回は起きない】同じ run1 の 36.832〜37.435(切替UIを 0.6 秒出して PowerShell へ移る、同形の非活性化)では UserRequest のまま ctx 4〜12/0.1s で停止なし。
  implication: |
    原本の失敗(一次が 06:25:00.525 に初めて _poll を実行 = 活性化の瞬間)と同じ形の停止が、診断付きの実 PageFolio で 1 回捕捉できた。ただし run1 では停止が要求の処理後に起きたため、期限切れには至っていない(要求は 24.58 に処理済み、締切 29.517 より前)。原本と同一機序と断定はできない(原本は未計測)が、(a) 非活性化の Alt+Tab 後に始まる、(b) 次の Alt+Tab 押下で一瞬だけ起きるが Python 層は走らない、(c) PageFolio の再活性化で通常動作に復帰、の 3 点が原本の時系列と一致する。分類(A〜D): ctx=0 かつ CPU=0 なので B(メッセージは捌くがタイマー不発)・C(CPU 消費中)は run1 の区間では否定、D は gui_flags=0 でメニュー/移動サイズ/ポップアップは否定。A(ネイティブ待機)に該当。

- timestamp: 2026-10-25(待機種別の対応づけ実験。scratchpad: syscall_feas.py / syscall_feas2.py / syscall_feas3.py。使い捨て子プロセスのみ)
  checked: 同一 .venv(Python 3.15.1 / Tcl-Tk 9.0.4)の子プロセス(窓なし、またはメッセージ専用窓のみ。前景は変えない)で、待機の種類ごとに NtQuerySystemInformation の WaitReason と NtQueryInformationThread(ThreadLastSystemCall)の syscall を同時に採取。ntdll/win32u の stub から syscall 番号→名前を引いた。実験後に子プロセスは全て終了させた。
  found: |
    Tcl の通常の待機(vwait + after 50)= NtUserMsgWaitForMultipleObjectsEx / UserRequest / ctx 約 57 回/s。PageFolio 自身の通常待機(awaiting-enter の 88 行すべて UserRequest)と同じ。
    同関数を INFINITE で待つ = 同 syscall / UserRequest / ctx 0(「Tcl にタイマーが無い」場合も UserRequest)。
    NtWaitForSingleObject・NtWaitForMultipleObjects(time.sleep)= UserRequest。
    NtUserGetMessage = WrUserRequest。
    ブロック中の SendMessage(NtUserMessageCall)= WrUserRequest。第1引数が宛先 HWND と一致し、GetWindowThreadProcessId で宛先の所有 pid/tid を引けた。WaitTime(100ns 単位)で現在の待機の長さも取れる。
    ThreadLastSystemCall は THREAD_QUERY_LIMITED_INFORMATION だけでは STATUS_ACCESS_DENIED(0xC0000022)。THREAD_QUERY_INFORMATION | THREAD_GET_CONTEXT で成功する(GetThreadContext / SuspendThread は呼ばない。スレッドを止めない)。
  implication: |
    run1 の停止中の WrUserRequest は、Tcl の通常の待機(UserRequest)とも、ユーザーモードの WaitFor*(UserRequest)とも異なる。win32k のメッセージキュー待機(NtUserGetMessage 型の独自ループ、ブロック中の SendMessage、flags に現れない modal 待機)にいたことを示す。したがって「Tcl のタイマー満了だけが落ちた」「after の連鎖が切れて INFINITE 待ちになった」は支持されない。待機先(宛先窓)は syscall と第1引数で直接特定できるが、現行の診断には未実装。
    原本側の独立した所見とも矛盾しない: 一次 traceback.log の 7 ダンプ(停止中の 06:24:52.2 を含む)は、メインスレッドが `__main__.py:81` の mainloop(C 呼出し)にいて、より深い Python フレームが無い。Python コールバック(_poll など)の内側ではなく、Tcl_DoOneEvent 配下のネイティブ層(Tk/Windows の窓プロシージャ処理など)にいたことを意味する。

- timestamp: 2026-10-25(誘発形の偏りと WM_NULL による隠蔽の検討)
  checked: 全 input_monitor の前景遷移を、PageFolio の非活性化の形で分類(可視の切替UI = PageFolio→ForegroundStaging→XamlExplorerHostIslandWindow→他、それ以外 = クリック・短押し Alt+Tab)。
  found: |
    診断再走 9 回のうち、可視の切替UIで PageFolio を非活性化したのは run1 の 3 回(27.358 / 34.616 / 36.832。34.616 は Task View で PageFolio に戻ったため実質除く)だけ。run2〜8(WM_NULL あり)と 073830Z は、クリックで PowerShell へ移るか、ForegroundStaging が約 8〜9ms の短押し(切替UIが出ない)で、可視の切替UIでの非活性化は 0 回。
    原本の W02 系列(preview@script 060315Z / settings@module 061910Z / thumb@module 062139Z / preview@module 062551Z)は、awaiting-enter の非活性化がすべて可視の切替UI(0.6〜1.2 秒)。そのうち要求の前に停止が残っていて失敗したのは preview@module の 1 回のみ(5 回中 1 回)。
    停止が観測できた 2 回(原本の失敗・run1)はどちらも「可視の切替UIで PowerShell へ移った直後」。クリック/短押しによる非活性化(診断再走で約 19 回。停止なし)では 0 回。事後に選んだ特徴で件数も少ないため(可視の切替UI 7 回で 2 回、それ以外 約 20 回で 0 回。偶然で両方が前者に入る確率は約 0.06〜0.07)、仮説生成にとどまる。
  implication: |
    (1) WM_NULL あり 7 回が 0 件だったことは、WM_NULL が停止を隠した証拠にも、停止が起きない証拠にもならない。7 回とも誘発形(可視の切替UIでの非活性化)を実行していないため、検証になっていない。
    (2) 停止中のスレッドが「ブロック中の SendMessage」の類なら、WM_NULL(外から受ける側のメッセージ)はスレッドを一瞬起こすだけで、外へ出した送信のブロックは解けない。この場合 WM_NULL は停止の発生を隠さない。ただし待機先が未特定なので断定しない。
    (3) 次回は WM_NULL を OFF のまま、誘発形を意図して実行する設計が妥当。WM_NULL は待機先が特定できてから別バッチで使う。

- timestamp: 2026-10-25(利用者の決定・チェックポイント回答 2回目)
  source: orchestrator が決定チェックポイントの回答として受領
  decision: 利用者は選択肢1「待ち先の診断を足して誘発再走」を選択。承認範囲は質問文に明記された内容に限る: (1) 権限は THREAD_GET_CONTEXT(必要なら THREAD_QUERY_INFORMATION)の追加のみ(読み取り専用。SuspendThread / GetThreadContext / DebugActiveProcess は呼ばない。前景・入力を変える API も使わない)、(2) WM_NULL は OFF のまま、(3) 8〜10 回の再走、(4) 誘発手順(切替UIを 0.5 秒以上見せて PowerShell へ移る -> 約 20 秒待つ -> Enter)。製品(pagefolio/*)・tests/*・pyproject.toml・証拠原本・06-UAT.md・06-MANUAL-EVIDENCE.json・STATE.md・ROADMAP.md は変更しない。コミットしない。
  scope_of_this_cycle: driver 層(uat_row.py / ui_thread_probe.py)の診断拡張と機構確認のみ。再走は利用者が実施する。

- timestamp: 2026-10-25(案1の実装と機構確認: 待ち先の診断を driver 層へ追加。実 PageFolio では未実行)
  changed: |
    `.planning/phases/06-release-validation/06-05-drivers/ui_thread_probe.py`(追記)と `uat_row.py`(追記。通常実行は不変)のみ。pagefolio/*・tests/*・pyproject.toml・06-05-evidence/ の既存原本・06-UAT.md・06-MANUAL-EVIDENCE.json・STATE.md・ROADMAP.md は未変更。コミットなし。
    新 sha256(診断実行の session JSON の diagnostics.driver_sha256 / probe_sha256 に記録される): uat_row.py 80e32e1143a114a55a2fd48157f8f7be18262860a00845a34b584753c6817274 / ui_thread_probe.py e9a4c9a914a4979a9492c36589c6d46b641ea3c170cc077b8536ff8ffe2e197a(前回: uat_row.py f10d92d9...845d / ui_thread_probe.py 740a0bf7...eb8b。06-MANUAL-EVIDENCE.json の driver_sha256 は従来どおり旧値のまま)。
  design: |
    権限: OpenThread を THREAD_QUERY_INFORMATION|THREAD_GET_CONTEXT(0x48)で追加するだけ(実測: ThreadLastSystemCall は THREAD_QUERY_LIMITED_INFORMATION では STATUS_ACCESS_DENIED)。SuspendThread / GetThreadContext / DebugActiveProcess / SendInput / SetForegroundWindow / SetCursorPos は使わない。check_offline の静的検査が、OpenThread の呼出しが2か所(0x800 と 0x48)だけであること、0x48 に停止/書き込み系ビット(TERMINATE/SUSPEND_RESUME/SET_CONTEXT/SET_INFORMATION/…)が無いこと、禁止名(GetThreadContext 系・NtSuspendThread 系・GetWindowText=窓へメッセージを送る、を追加)をコードが参照しないことを検査する。WM_NULL は既定OFFのまま(--wm-null-probe を付けない限り SendMessageTimeoutW を一度も呼ばない)。
    新しい列(サイドカーの末尾に追記): syscall(UIスレッドの最後のシステムコール名)/ sc_arg(第1引数)/ sc_status(0 または 0xC0000001=待機中でない。エラーにしない)/ sc_wait_ms(現在の待機の長さ。WaitTime は100ns単位)/ wait_target(第1引数が窓なら宛先の解決結果)/ others_ctx(UI以外のスレッドの [tid, ctx切替, 待機理由])。システムコール番号→名前は、この機械の ntdll.dll / win32u.dll の syscall スタブから起動時に作る(約4ms)。
    wait_target: IsWindow → GetWindowThreadProcessId → GetClassNameW → InternalGetWindowText(窓構造体から直接読む。メッセージを送らない)→ IsWindowVisible / IsHungAppWindow で宛先の所有 pid/tid・クラス・タイトルを引く。宛先スレッドの状態/待機理由/ctx/待機の長さ/CPU と宛先プロセスのイメージ名は、UIスレッド用と同じ NtQuerySystemInformation のバッファ(ImageName は UNICODE_STRING)から読むので別プロセスは開かない。宛先スレッドが待機中なら、そのスレッド自身の最後のシステムコールも読み、さらに HWND なら次の宛先へ辿る(最大3段・循環検出)。既知の HWND 先頭引数のシステムコール(NtUserMessageCall ほか)は by=known-call、それ以外は IsWindow が真のときだけ by=speculative。
    停止区間: UIスレッドの ctx が1秒/5秒/15秒増えない時点で、全スレッドの最後のシステムコール・プロセス所有のトップレベル窓の一覧(class/title/visible/enabled/owner。モーダルダイアログや IME 窓の有無を見る)・GetGUIThreadInfo の active/focus/flags を stall_snapshots に1回ずつ記録(最大8件)。区間の集計に wait{kind(blocking-sendmessage / message-loop / msgwait / kernel-wait / other:*), syscalls, targets, others_ctx_delta} とタグ A:<kind> を追加。
    uat_row.py: --induce-switcher(--induce-wait-s 既定20。W02 の行で --diagnose-ui-thread と併用)。誘発手順(Alt を押したまま Tab で切替UIを0.5秒以上見せて PowerShell へ移る -> 約20秒静止 -> Enter)を日本語で案内し、Enter 時点の静止が足りなければ不足分を自動で待ち(phase は awaiting-enter のまま=PageFolio 内のクリックは手順汚染として検出される)、成立(PageFolio に戻っていない・切替UI>=0.5秒・静止>=待ち時間-0.5秒)を session.induce_assessment、手順の種別を session.diagnostics.induce(variant=alt-tab-switcher-hold-then-quiet-wait。誘発なしの診断行は free)に記録。成立しなくても二次起動は進め、その回を誘発の母数に数えない。--summarize-diag は誘発の成立/不成立と理由、停止区間ごとの種別・最後のシステムコール・待ち先・他スレッドctx増分、誘発の母数(成立かつ clean の回)を表示する。
  verification: |
    ruff check .(リポジトリ全体)・ruff format(両 driver)合格、AST 合格。--check-monitor 28 項目合格(回帰なし)。--check-diagnostics 145 項目合格(前回 90)。リハーサル: 診断OFFの偽 harness の session キー集合と steps は前回行と同一(診断フィールド無し)。
    使い捨てプロセス3つ(窓はすべて非表示。前景は 331300 のまま不変)での実機確認: A(観測対象)が B の窓へ SendMessage でブロック、B の窓プロシージャが C の窓へ SendMessage でブロック、C は眠る。サンプラは A の UI スレッドから syscall=NtUserMessageCall・sc_arg=B の hwnd を読み、宛先1段目(B)を pid/tid/class(PfChainB)/title/image(python.exe)/状態(Waiting/WrUserRequest)に、B のスレッドの最後のシステムコール(NtUserMessageCall, arg=C の hwnd)から宛先2段目(C: pid/tid/title/Static、スレッドは NtWaitForMultipleObjects)まで解決した。C はメッセージを捌かないのに窓の情報は取れた(InternalGetWindowText 等は宛先がブロックしていても戻る)。sc_wait_ms は実時間と一致(100ns単位を確認)。1サンプルのコストは平均約7ms・最大約13ms(宛先が応答しなくてもブロックしない)。区間集計は kind=blocking-sendmessage、宛先に pf-chain-B / pf-chain-C の両方。開いた権限は 0x1000 / 0x800 / 0x48 だけ。TARGET_SCRIPT の Tcl 場面では idle=NtUserMsgWaitForMultipleObjectsEx、afterコールバック内の sleep=NtWaitForMultipleObjects で、待機理由が同じ UserRequest でも見分けられた。
    実在プロセスの読み取り確認(read-only。スレッドは止めない): 0x48 で explorer.exe(60/60)・WindowsTerminal.exe(14/14)・OpenConsole.exe・powershell.exe・TextInputHost.exe・python.exe のスレッドの ThreadLastSystemCall が読めた。ctfmon.exe は OpenThread が ACCESS_DENIED(5)(14/14)。したがって待ち先が ctfmon の窓なら、窓のクラス/タイトル/所有者/スレッドの状態・ctx・待機の長さは取れるが、そのスレッド自身の最後のシステムコールは取れない(wait_target.thread_syscall に error=winerror=5 が残る)。
    過去の診断再走9回の前景遷移で誘発判定を再生: 誘発手順を指示していない9回の peer 直前はすべて不成立(switcher-not-shown)。run1(074104Z)の 07:40:36.8「PageFolio -> 切替UI(約0.58秒)-> PowerShell」を陽性対照として、20秒静止後に成立と読めた。偽 harness(A->B->C)での Row.run_python の通しリハーサルで、session / サイドカー(列 40)/ ログの写し / --summarize-diag の表示を確認。
  caveat: |
    実 PageFolio ではまだ一度も動かしていない。誘発手順(可視の切替UI 0.5秒以上 -> 静止 20 秒)が停止を実際に誘発するかは再走で初めて分かる(「可視の切替UIで非活性化した 7 回中 2 回」は事後に選んだ特徴で仮説段階)。ctfmon.exe のスレッドは読めない。ThreadLastSystemCall は第1引数しか持たず、送ったメッセージ番号(WM_*)は分からない。
  implication: |
    再走の1回ごとに、停止が起きれば「UIスレッドが何のシステムコールで誰を待っているか」(宛先の所有者・クラス・タイトル・状態、その先の連鎖、他スレッドの動き、モーダル窓の有無)が session JSON に残る。停止が起きなければ、誘発成立の回数分だけ「この誘発手順では再現しない」という頻度データが残る(修正の証拠ではない)。

- timestamp: 2026-10-25(誘発再走10回の解析 1: 全体像。以降 scratchpad の dump_run.py / win_samples.py / landings.py / age_analysis.py / landing_burst.py。すべて読み取り専用)
  checked: `06-05-evidence/debug-w02-preview-peer-expired/` の 090705Z〜092038Z の 10 セッション(session JSON と `.ui-samples.jsonl`)。
  found: |
    誘発成立かつ clean 8 回・期限切れ(peer 失敗)0 件。停止区間は run4(091150Z)と run5(091329Z)の 2 件。どちらも peer(二次起動)とは別の時間帯に起き、peer は 110ms / 78ms で completed。run4 は awaiting-enter(peer の 42 秒前)、run5 は post-peer(peer の後)。つまり今回の 10 回は「期限切れの再現」ではなく「停止そのものの再現」。
    全 19 セッションで PageFolio から他窓へ移った回は 52 回、うち可視の切替UI(XamlExplorerHostIslandWindow が出た)経由は 31 回。停止は 3 回(074104Z run1 / 091150Z run4 / 091329Z run5)で 3 回とも可視の切替UI経由(3/31=9.7%、全体 3/52=5.8%)。クリック・短押しの移動 約 21 回は 0 件だが、偶然で 3 件すべてが可視切替UIの側に入る確率は約 0.2(Fisher)で有意ではない。切替UIが必要条件とは言えない。
    停止の条件に見えた量(PageFolio が前面だった秒数 ACT_AGE、プロセス年齢、直前 8 秒のキー数、切替UIの表示秒数)に区別できる差は無い(停止3回: ACT_AGE 2.8/4.5/5.8 秒、切替UI 0.39/0.54/0.62 秒、直前キー 0/0/4。非停止 28 回は 0.8〜6.6 秒、0.33〜4.6 秒、0〜4)。
  implication: 頻度は 1 回の切替あたり 5〜10% 程度(信頼区間は広い)。条件の特定には現データは不足。

- timestamp: 2026-10-25(解析 2: run4 の停止を終わらせたもの。真の長さは 15.4 秒)
  checked: run4 の foreground_transitions・`.ui-samples.jsonl`(09:10:34.9〜09:10:37.2 と 09:10:50.0〜09:10:51.4)・stall_episodes・stall_snapshots。
  found: |
    09:10:35.205 Alt+Tab で PageFolio→ForegroundStaging→切替UI(0.538 秒)→ 35.743 PowerShell が前景(着地)。切替UIの表示中(35.208〜35.743)の UI スレッドは NtUserMsgWaitForMultipleObjectsEx / UserRequest で ctx 切替 6〜31/0.1 秒の通常動作。着地を含む 100ms(35.708〜35.810)だけ ctx 21(通常 7〜10 の 2〜3 倍。着地時の小さなコールバック群)。35.810 のサンプルで syscall=NtUserGetMessage / WrUserRequest・sc_wait_ms=62.5(= GetMessage に入ったのは約 35.748。着地の約 5ms 後。入力監視のポーリング 8ms の誤差内)。
    以後 146 サンプル連続で NtUserGetMessage(sc_arg=第1引数は同一のスタック上の MSG ポインタ 527036183552)・ctx 切替増分 0・サイクル増分 0・CPU 0・page fault 増分 8(プロセス全体)・gui_flags=0・hwnd_active=hwnd_focus=hwnd_capture=0・IsHungAppWindow 偽 0/146。sc_wait_ms は 62.5ms → 14562.5ms まで単調増加(1 回の待機が途切れずに続いた)。
    50.309 を最後に syscall が NtCallbackReturn(WrUserRequest)に変わるが、ctx は 50.404 の 1 行で +10 のみ(次の Alt+Tab 押下 50.32 に伴う他プロセスからの SendMessage を 1 回さばいて待機に戻った「まばたき」)。sc_wait_ms は 78.1 から再び増加し、GetMessage の外には出ていない。停止エピソードの終端 50.3095 は「GetMessage ラベルの最後のサンプル」で、真の終端ではない。
    本当の再開は 51.212 のサンプル(ctx +242・サイクル +20.5M・syscall=NtUserMsgWaitForMultipleObjectsEx・hwnd_active=4001484 / hwnd_focus=1904494 に復帰)。直前の 51.112 までは停止、PageFolio への再活性化(Alt+Tab で PageFolio を選択)の foreground 遷移 #8 が 51.1590(ForegroundStaging→TkTopLevel)。再開は再活性化から 100ms 以内。停止は 35.75〜51.2 秒の約 15.4 秒。
  implication: 停止の終了要因は「PageFolio の再活性化」(原本 06:25:00.525 / run1 30.246 と同じ)。次の Alt+Tab 押下(他窓への SendMessage 1 回)では終わらない。ユーザー入力が PageFolio 以外(PowerShell)へ向かっている間は終わらない。タイマー・時間経過では終わらない(15.4 秒続いた)。

- timestamp: 2026-10-25(解析 3: run5 の停止は終わらなかった)
  checked: run5(091329Z)の foreground_transitions・stall_episodes・stall_snapshots(3 件: 1.0 / 5.1 / 15.1 秒)・steps・raw_inputs・harness_stop・cleanup・run-logs。
  found: |
    09:12:36.790 PageFolio→切替UI(0.616 秒)→ 37.406 PowerShell 前景(post-peer で F5 を 4 回押した後 1.5 秒)。37.440 のサンプルから 237 サンプル(23.6 秒)連続で NtUserGetMessage / WrUserRequest・ctx 0・サイクル 0・IsHungAppWindow 偽。以後 PageFolio への再活性化の遷移は一度も無い。利用者は PowerShell 上で回答を入力し続けた(回答 6 件 + Enter 1 回、最後の回答 09:13:00.759)。PowerShell への入力(PageFolio 以外へのキー)では解除されなかった。
    サンプラは 09:13:01.09(最後の回答の直後)で停止した。ここから harness の stop(`stop` ファイルを作り 8 秒待つ)が始まるが、run5 だけ `harness_stop.returncode=1`・`AssertionError: 停止未完了。120秒の安全終了後inspectする`(他の 9 回は returncode 0)。run-logs に primary-result.json / primary-resource-audit.json が無い(run4 には有る)。stop の検知は PageFolio 側の Tk `root.after(50, stop_poll)`(tests/test_startup_windows.py:2477-2500)なので、停止は少なくとも 09:13:01.1+8 秒 = 09:13:09 まで続いた(合計 31.6 秒以上)。driver が 14232(ランチャー)を terminate して終了(finished_at 09:13:29.56)。
    primary-traceback.log は 10 秒ごとの faulthandler ダンプ 9 回(プロセス寿命約 90 秒)。すべてメインスレッド=tkinter mainloop(`pagefolio/__main__.py:81`)、`_serve` 8 スレッド=`startup_win32.py:836`。
  implication: (1) 停止中は PageFolio の `_poll`(startup_control)だけでなく、別の Tk `after` 連鎖(harness の `stop_poll`)も止まっている = Tk/Tcl のイベントループ全体が止まっており、PageFolio の個別ロジックの問題ではない。(2) 再活性化が無ければ自然には復帰しない(31.6 秒以上)。1 回の停止が 2.5 / 15.4 / 31.6+ 秒と長さがばらつくのは、利用者が PageFolio を再活性化するまでの時間そのもの。

- timestamp: 2026-10-25(解析 4: 8 本の「他スレッド」と環境要因)
  checked: run4/run5 の others_ctx(`stall_episodes[].wait.others_ctx_delta`)と stall_snapshots の全スレッド。
  found: |
    ctx 増分のある 8 スレッドは run4 で +265〜+290(14.5 秒)、run5 で +499〜+524(23.6 秒)= 19.7〜22 回/秒。syscall はすべて NtWaitForSingleObject / UserRequest で wait_ms 15.6〜31.2(50ms 周期の待機)。= `startup_win32.py:836` の `_serve` 8 インスタンス(listener)。UI スレッドの ctx が 0 の間も、同一プロセスのこの 8 スレッドは 50ms のタイムアウトで正常に回り続けた。
    スナップショットの全スレッド(run4 は 24 本): UI=NtUserGetMessage、_serve 8 本=NtWaitForSingleObject、スレッドプール 8 本=NtWaitForWorkViaWorkerFactory(WrQueue)、NtWaitForMultipleObjects 3 本(UserRequest)、NtWaitForAlertByThreadId 1 本、そして UI 以外にもう 1 本 NtUserGetMessage / WrUserRequest のスレッド(run4 の tid 29232。最初のスナップショットで待機 6.2 秒 = PageFolio 初回活性化 30.67 の直後から待っている。別のメッセージループ)。ブロッキング SendMessage / NtUserMessageCall を持つスレッドは 1 本も無い。
    電力調整・EcoQoS・タイマー合体: プロセス全体に掛かるものなら _serve 8 本の 50ms タイマーも遅れるはずだが、20 回/秒を維持。UI スレッドの待機が MsgWait(タイムアウト付き)ではなく GetMessage(タイムアウト無し)である点も説明できない。
  implication: 外部の待ち先(別プロセスへのブロッキング SendMessage、ctfmon、explorer、ターミナル)は無い。run2 の wait-target 行(`NtUserSetTimer: hwnd 0x271262 [SystemUserAdapterWindowClass '']`)は、宛先 tid 30316 が run2 の UI スレッド自身(ui_thread_log の tid)であり、UI スレッドが自分の窓(CoreMessaging の SystemUserAdapterWindowClass)に SetTimer した自己参照。待ち先ではない。同種の行は run4 でも `NtUserDrainThreadCoreMessagingCompletions2: hwnd 0x10f1016 [SystemUserAdapterWindowClass]`(宛先 tid 856 = UI スレッド自身)。どちらも Alt+Tab の PageFolio 離脱の検出(09:07:13.533 / 09:11:23.817)と同時(サンプルは 6〜7ms 前。入力監視の検出遅れ 8ms 以内)に観測された。この UI スレッドが Windows 11 の CoreMessaging(TSF / Microsoft IME のUI基盤)と結合しており、Alt+Tab で離脱するときその部品が動く、という環境情報にはなる。

- timestamp: 2026-10-25(解析 5: UI スレッドが持つ窓と TclNotifier の不在)
  checked: run4/run5 の stall_snapshots[].windows(プロセス所有のトップレベル窓。EnumWindows)。
  found: |
    UI スレッドの窓 9 つ: GDI+ Hook Window Class / TkTopLevel / EmbeddedMenuWindowClass / MenuWindowClass / Wtk_TaskbarHandler / TtkMonitorClass / MSCTFIME UI / IME(Default IME)/ BingIMESysMessageWindow。run4(3 スナップショット中 2 件)・run5(3 件)とも同じ。モーダルダイアログ・IME 候補窓・その他のダイアログは無い。**Tcl の通知器窓 `TclNotifier` は無い**。
    検証: 同じ `process_windows()`(driver の EnumWindows)は、使い捨て子プロセスでは通知器窓を作った場合に `TclNotifier` を列挙する(plain: PfGhostWnd/IME のみ、notifier: TclNotifier/PfGhostWnd/IME)。見落としではない。
  implication: 停止した 2 プロセスは、Tcl が一度も `Tcl_SetServiceMode(TCL_SERVICE_ALL)` に入っていない状態(下の Tcl ソース読解参照)。

- timestamp: 2026-10-25(Tcl 9.0.4 / Tk 9.0.4 ソース読解。scratchpad/tclsrc, tksrc。core-9-0-4 タグ。文字列としてのみ読んだ)
  checked: `win/tclWinNotify.c`・`generic/tclNotify.c`・Tk の `win/*.c`。
  found: |
    Tcl の Windows 通知器 `TclpWaitForEvent`(tclWinNotify.c:465-559): (1) `PeekMessageW(PM_NOREMOVE)` が偽なら `MsgWaitForMultipleObjectsEx(timeout, QS_ALLINPUT)` で待つ(タイムアウトは次の after までの時間。これが after を動かす唯一の時間源)。(2) 起きたら `PeekMessageW(PM_NOREMOVE)` を再度呼び、**真なら `GetMessageW(&msg, NULL, 0, 0)`(L531)でメッセージを取り出す**。GetMessageW にはタイムアウトが無い。Peek が真と言ったメッセージが GetMessage の時点で消えていると、スレッドはここで無期限に眠る。
    Windows 通知器は `tsdPtr->hwnd`(`TclNotifier` 窓)が無いと `TclpSetTimer` が即 return する(L278-280)ため、WM_TIMER のフォールバックも無い。窓は `TclpServiceModeHook(TCL_SERVICE_ALL)` で初めて作られ、以後残る(L338-351)。Tk が service mode ALL に入る場所: メニューの WM_INITMENU(tkWinMenu.c:1171)・ウィンドウの移動/サイズ変更ドラッグ(tkWinWm.c:7865)・ダイアログ・スクロールバー(tkWinScrlbr.c:619)。窓が有れば `after` を作る度に `Tcl_SetMaxBlockTime` → `TclpSetTimer` が `SetTimer(hwnd, INTERVAL_TIMER, timeout)` を呼び、GetMessage の待ちは最長でも次の after の間隔で WM_TIMER に起こされる。
    Tk 側の GetMessage は `GetTranslatedKey`(tkWinX.c:1471、`GetMessageA(&msg, NULL, WM_CHAR, WM_CHAR)` を Peek の後)と DBCS 先行バイト(tkWinX.c:1319)のみ。キー入力処理の中でしか呼ばれない。
  implication: 観測した「NtUserGetMessage / WrUserRequest / ctx 0 / タイマー不発」は、Tcl 通知器の `GetMessageW`(L531)で無期限に待っている状態と一致する(コード上、他に PageFolio プロセスの UI スレッドが GetMessage を呼ぶ箇所は無い。Tk のキー処理は停止の開始が最後のキーの 0.4〜0.6 秒以上後で、停止の終了が文字入力無しの再活性化である点と合わない)。

- timestamp: 2026-10-25(使い捨てプロセスでの再現と対策の検証。scratchpad ghost_child.py / ghost_exp.py / pw_check.py。自プロセスのみ。窓は非表示で前景を変える API は不使用)
  checked: Python 3.15.1 / Tcl 9.0.4 の子プロセス(Tk 窓なし・非表示の WS_POPUP 窓 1 つ + Tcl `after 50` の心拍をファイルへ書く `vwait`)。親が `UiThreadProbe`(driver のもの。読み取り専用)で子の UI スレッドを 50ms 間隔で観測。「幽霊メッセージ」は、子の WH_GETMESSAGE フックが、Tcl の PeekMessage(PM_NOREMOVE) が選んだ投稿メッセージ(WM_APP+7)を PeekMessage(PM_REMOVE) で取り除くことで人工的に作った(Peek は真、直後の GetMessage には何も無い)。
  found: |
    【plain】基線: NtUserMsgWaitForMultipleObjectsEx / UserRequest、心拍 48 回/3 秒(最大間隔 64ms)、ctx 106〜125/3 秒。幽霊後: **NtUserGetMessage / WrUserRequest が 100/100 サンプル、ctx 増分 0、心拍 0(5 秒)**。窓へ SendMessageTimeout(WM_NULL) を送ると 0.1ms で返る(送信メッセージは待機中に処理される)が、syscall は **NtCallbackReturn / WrUserRequest** になり心拍は戻らない(3 秒)= run4 の 50.404 / run1 の 29.737 と同じ「まばたき」。窓へ PostMessage(WM_NULL) または PostThreadMessage(WM_NULL) を投げると即再開(MsgWait に戻り心拍再開、最大間隔 63〜64ms)。2 回目の幽霊でも同じ。別プロセスからの Post でも効く。
    【notifier】`Tcl_SetServiceMode(TCL_SERVICE_ALL)` を 1 回呼んで元に戻すだけ(ctypes で tcl90.dll)で `TclNotifier` 窓が作られる。同じ幽霊を 2 回起こしても心拍は止まらない(最大間隔 64〜66ms、GetMessage が見えるのは 1 サンプルのみ)。コスト: ctx/秒が約 3.5〜8 倍(135〜300/秒 対 plain 約 40/秒)、サイクル 16〜28M/秒 対 plain 12M/秒(1 コアの 1% 未満)。
    【watchdog】別スレッドが 150ms ごとに PostThreadMessage(tid, WM_NULL)。幽霊は最長でも 1 周期(最大間隔 68〜105ms、GetMessage が見えるのは 1〜2 サンプル)で解消。コスト: plain とほぼ同じ(ctx 約 45〜50/秒、サイクル 7〜11M/秒)。
    使い捨ての UI スレッドが持つ窓は IME と自分の窓のみ(PageFolio にある MSCTFIME UI / BingIMESysMessageWindow / SystemUserAdapterWindowClass は作られない = TSF が未活性)。実験中の前景: plain は不変(before=after)。notifier / watchdog では before≠after だが、子は非表示の窓しか持たず前景 API を呼んでいない。利用者の通常操作による変化(実験の直前直後に同じ 2 つの値が行き来している)。
  implication: |
    (1) 停止の観測シグネチャ(NtUserGetMessage + WrUserRequest + ctx 0 + 他スレッドは正常 + 送信メッセージでは NtCallbackReturn のまばたきだけ + 投稿メッセージで復帰 + Tcl の after 全停止)は、Tcl 通知器が GetMessageW で眠った状態で再現できた。待ち先の外部プロセスは不要。
    (2) 停止の致命性は「GetMessage に時間の上限が無い」ことと「TclNotifier 窓が無い(WM_TIMER が無い)」ことの 2 つに依る。どちらか一方でも欠ければ回復する(notifier / watchdog の実験)。
    (3) 「Peek が真なのに Get が空」になるきっかけは、この実験では人工(フック)。実機のきっかけは未特定。

- timestamp: 2026-10-25(幽霊の自然発生を試す: 否定的結果)
  checked: scratchpad winevent_child.py / winevent_exp.py。子プロセスで out-of-context WinEvent フック(EVENT_OBJECT_NAMECHANGE)を設定し、別スレッドが NotifyWinEvent と PostThreadMessage を 3ms ごとに繰り返し、コールバックの中でも PostThreadMessage する(MS KB2682659「WinEvent コールバック中に受けた投稿メッセージを GetMessage が認識しない」の型)。30 秒。
  found: WinEvent コールバック 6583 回・コールバック内投稿 6583 回で、Tcl の心拍が 0.5 秒を超えて止まった回は 0(最大間隔 518ms が 1 回、他は 65ms 以下)。
  implication: 単純な WinEvent コールバック + 投稿の組合せでは幽霊は起きない。実機の幽霊は別の条件(TSF / CoreMessaging / IME の実在、または前景遷移そのもの)を要する。実機のきっかけは未特定のまま。

- timestamp: 2026-10-25(利用者の決定・チェックポイント回答 3回目)
  source: orchestrator が AskUserQuestion で利用者に提示した結果
  decision: 利用者は選択肢2「製品を変えず実機で対策を検証」を選択。質問文に「PageFolio の外から介入する」「新たな承認が必要」と明記された上での承認であり、承認範囲は次に限る: driver 層(製品・tests 無変更)の外部見張り。別プロセス(driver)から一次 PageFolio の UI スレッドへ `PostThreadMessageW(tid, WM_NULL)`(投稿のみ。SendMessage は使わない)を 100〜150ms ごとに送りながら、誘発再走を約 30 回行い、機構(Tcl 通知器の GetMessageW 無期限待ち)と対策(投稿 WM_NULL による復帰)を実機で確認する。
  scope_limits: |
    - 承認範囲はこの外部見張りのみ。pagefolio/*・tests/*・pyproject.toml・証拠原本・06-UAT.md・06-MANUAL-EVIDENCE.json・STATE.md・ROADMAP.md は変更しない。コミットしない。製品側の対策(F1〜F4)はこの承認に含まれない。
    - 投稿前に tid が pid+作成時刻と一致することを確認する。SendMessage・前景/入力 API(SendInput / SetForegroundWindow / SetCursorPos)・SuspendThread / GetThreadContext / DebugActiveProcess は使わない。
    - 出力は 06-05-evidence/debug-w02-preview-peer-expired/ に分離(purpose=debug-frequency, acceptance=false)。既存ファイルは上書きしない。Phase 06 の受入は停止のまま、W02/preview@module(062551Z)は fail のまま。
  scope_of_this_cycle: driver 層に `--external-wake-ms`(既定OFF)を実装し、機械的に検証し、利用者への 30 回再走手順を返す。再走は利用者が実施する。

- timestamp: 2026-10-25(外部見張り `--external-wake-ms` の実装と機構確認。実 PageFolio では未実行)
  changed: |
    `.planning/phases/06-release-validation/06-05-drivers/ui_thread_probe.py`(追記)と `uat_row.py`(追記)のみ。pagefolio/*・tests/*・pyproject.toml・06-05-evidence/ の既存原本・.planning/tmp/*・06-UAT.md・06-MANUAL-EVIDENCE.json・STATE.md・ROADMAP.md は未変更(git status で確認)。コミットなし。
    新 sha256: uat_row.py d784c62d4259bb91c1671bd39cace4e00e1cc6c01da30d80c3b304b777a3a8d6 / ui_thread_probe.py 832cb76f9efd391ca0063d2f94d2fbdbc265756d782d2936b2e5ebf892146e6b(前回: uat_row.py 80e32e11...7274 / ui_thread_probe.py e9a4c9a9...197a。診断実行の session JSON の diagnostics.driver_sha256 / probe_sha256 に記録される)。
  design: |
    起動: `--diagnose-ui-thread --external-wake-ms MS`(既定OFF。承認範囲の 100〜150 以外は拒否。`--wm-null-probe` とは併用不可。`--diagnose-ui-thread` なしも拒否)。
    動作: UiThreadProbe の別スレッド `_run_wake` が MS ごとに `wake_once` を呼ぶ。毎回(1回の投稿の直前に)`Win32Native.verify_post_target(tid, hwnd, expected_created)` で、(1) 保持したプロセスハンドルの GetProcessTimes の作成時刻 == expected_created(manifest の process_created。probe 起動時にも identity_verified を要求)、(2) GetExitCodeProcess が STILL_ACTIVE、(3) スレッドハンドル(THREAD_QUERY_LIMITED_INFORMATION・保持中は tid も再利用されない)の GetProcessIdOfThread == 対象 pid かつ GetExitCodeThread が STILL_ACTIVE、(4) 窓が実在すれば GetWindowThreadProcessId == (tid, 対象 pid)、を確かめ、通ったときだけ `Win32Native.post_wm_null(tid)` = `PostThreadMessageW(tid, WM_NULL(=0), 0, 0)` を呼ぶ。確認が通らなければ投稿せず「拒否」として理由を記録(対象の終了は拒否ではなく「見送り」)。SendMessage 系・前景/入力 API・SuspendThread/GetThreadContext/DebugActiveProcess は使わない。新しい OpenThread/OpenProcess は無し(開く権限は従来どおり 0x1000 / 0x800 / 0x48 のみ)。投稿の上限 6000 件(スレッドメッセージキューの既定上限 10000 件の安全弁)。OFF のときはスレッドを作らず、PostThreadMessageW・宛先確認を一度も呼ばない。
    記録: session `diagnostics.external_wake=<ms>`(見張りなしの診断行は None)・`ui_thread_diag.external_wake`(posts_ok/posts_failed/refused/skipped/by_error/by_phase/failures(先頭50件)/間隔の統計(件数・平均・最大・周期の2倍超の回数)/long_gaps/health)・サイドカーの列 `wake_ok` `wake_fail`(累計)・`ui_thread_diag.getmessage`(NtUserGetMessage の連続サンプル区間: 件数・最長 length_ms・停止(>=400ms)の件数・停止の最中に投稿が流れていた件数)。purpose=debug-frequency・acceptance=false・保存先 06-05-evidence/debug-w02-preview-peer-expired/(既存ファイルは上書きしない=従来の連番付与)。見張りの動作の目安(health: 投稿 20 件以上・拒否 0・失敗は 2% か 2 件以下・間隔の最大が周期の 5 倍以下・見送り 10 以下)を満たさない回は報告に【警告】を出し、集計で印を付ける(除外はしない)。
    集計: `--summarize-diag` に見張りの有無で分けた群(誘発成立かつclean / 全回)を追加: 二次起動の未完了・ctx停止区間(件数/最長)・GetMessage 区間(件数/停止/最長ms/最長行数。syscall 列のあるセッションだけで数える=古い診断は数えた回に入らない)・停止のうち投稿が流れている最中のもの・投稿の成功/失敗/拒否/最大間隔・動作が期待どおりでない回。
  verification: |
    ruff check .(リポジトリ全体)合格・ruff format(両 driver)合格・AST 合格。`--check-monitor` 28 項目合格(回帰なし)。`--check-diagnostics` 195 項目すべて合格(前回 145)。追加分:
    (静的)ソースの構文木から、PostThreadMessageW を呼ぶ関数は Win32Native.post_wm_null(見張り)と _live_ghost(機構確認の餌)だけ・見張りの呼出しは1か所でメッセージは定数 WM_NULL(=0)・wParam/lParam は 0・post_wm_null を呼ぶのは UiThreadProbe.wake_once だけ・見張りの経路(verify_post_target / post_wm_null / wake_once / _run_wake)が使う Win32 API 風の属性名は {PostThreadMessageW, GetProcessTimes, GetExitCodeProcess, GetProcessIdOfThread, GetExitCodeThread, GetWindowThreadProcessId, IsWindow} だけで、禁止名(SendMessage 系・前景/入力系・停止/書き込み系を追加)も SendMessageTimeoutW/wm_null/OpenProcess/OpenThread も参照しない。uat_row.py 自体は PostThreadMessageW を参照しない。静的検査の感度確認(scratchpad mutation_check.py): 悪い変更を1つずつ入れた写し 7 種(確認内への SendMessageW / 投稿メッセージを WM_NULL 以外に / 見張りに送信版 wm_null / wake_once に SetForegroundWindow / 別関数からの PostThreadMessageW / 許可外 API / 宛先確認の省略)すべてで check_offline が失敗し、無変更の対照は 0 件失敗。
    (偽ネイティブ)見張り OFF はスレッド・投稿・宛先確認とも 0 回。ON は毎回 (tid, hwnd, 作成時刻) の確認の後に tid へだけ投稿し、件数・phase別・間隔(周期の2倍超は long_gaps)を記録。確認失敗は投稿せず拒否として理由を記録。投稿失敗(1444)・確認や投稿の例外・作成時刻不一致/期待値なし(identity-unverified)・投稿上限・UI未特定/対象消滅/終了(見送り)・約100msのスレッド動作(0.55秒で4〜7回)も確認。health の境界値・停止のうち投稿が流れている最中の判別・見張りの有無で分けた集計(見張りなし3回/あり3回の合成セッション)も確認。
    (実API・使い捨てTclプロセス + 幽霊メッセージ。別プロセスの外部見張り)WH_GETMESSAGE フックで餌メッセージを Peek 後に取り除いて幽霊を再現。見張りなし: 心拍の最大の空き 2700ms・GetMessage 56行(最大 2765.6ms)・停止 1 件、手動の投稿 WM_NULL で心拍が再開。見張りあり(120ms・別プロセスの投稿): 幽霊 3/3 回が起き、心拍の最大の空き 81/80/80ms(別の1回は 93/89/92ms)、GetMessage 区間 3 件(6行・最長 63〜78ms)・停止 0 件、投稿 39 回(失敗0・拒否0・間隔 平均120.1ms・最大133.2ms・health=healthy)。宛先確認の拒否も実 API で確認: 別プロセスのスレッド(thread-not-in-target-process)・作成時刻違い(process-creation-time-mismatch)・窓の持ち主違い(デスクトップ窓: window-owner-mismatch)は拒否、正しい組は通過。開いた権限は 0x1000 / 0x800 / 0x48 だけ・API エラーなし。前景窓は前後で不変(660062)。子プロセスは全て終了し、%TEMP% の一時ディレクトリも残さない。
    (通しリハーサル・scratchpad rehearse3.py)偽 harness + 幽霊の使い捨てプロセスで Row.run_python を通した。見張り ON(120ms・サンプル50ms): 無スケジュール区間 0 件・GetMessage 区間 1 件(1行・15.6ms)・投稿 59 回(失敗0・拒否0・最大間隔 134.4ms)・「外部見張りの動作: 期待どおり」。見張り OFF: 無スケジュール区間 1 件(5.452秒)・GetMessage 110 行(5468.8ms)・停止 1 件。`--summarize-diag` が両者を別の群として集計することを確認。
    サンプラのコスト(50ms間隔・使い捨て): 平均 7.6〜7.8ms・最大 15ms・最大の空き 0.06秒。
  caveat: |
    実 PageFolio ではまだ一度も動かしていない。幽霊の実機でのきっかけは未特定のままで、使い捨てでの人工幽霊で『投稿 WM_NULL が1周期内に解消する』ことを確かめただけ。実機では (a) 見張りで幽霊自体が起きにくくなる(解消ではなく予防)可能性があり、その場合『停止 0 件』は対策の効果を示すが機構の確認としては弱い(強い証拠は『GetMessage の短い区間が見え、すぐ消える』回の存在)。(b) 見張りが動かなかった回の停止を『見張りありでも停止』と読み違えないよう health と『停止のうち投稿が流れている最中のもの』を分けて出す。(c) サンプルを 50ms にすると 1 回あたり 1〜2MB(30回で最大約60MB)の証拠ファイルになる。

- timestamp: 2026-10-28(continue による再開確認)
  checked: `uat_row.py --summarize-diag` を読み取り専用で実行し、driver 2 本の SHA256 を前回記録と照合。
  found: |
    保存済み診断は 19 回で前回から増加なし。外部見張りあり群は全回・誘発成立かつ clean ともに 0 回。
    見張りなし群は誘発成立かつ clean が 8 回、ctx 停止区間 2 件(最長 23.605 秒)、GetMessage 停止 2 件(最長 23640.6ms)。二次起動の未完了は 0 回だが、UI の停止が無かったことを意味しない。
    uat_row.py SHA256 d784c62d4259bb91c1671bd39cace4e00e1cc6c01da30d80c3b304b777a3a8d6 / ui_thread_probe.py SHA256 832cb76f9efd391ca0063d2f94d2fbdbc265756d782d2936b2e5ebf892146e6b は前回と一致。コード・入力・環境を変えた検証は実施しておらず、成功済みの機械的検証は再実行しない。
  next: |
    CHECKPOINT(human-action): 既に承認された外部見張り(120ms)の実機誘発再走 30 回を利用者が実施する。各回は --row W02/preview@module --diagnose-ui-thread --induce-switcher --external-wake-ms 120 --diag-interval-ms 50 --diag-run N --diag-runs 30 を指定し、完了後 --summarize-diag で集計する。
    利用者による Alt+Tab(一覧を約1秒表示)、PowerShell へ移動後の約20秒静止、Enter、driver の案内に沿った操作・目視回答が必要。結果が保存されたら既存 Current Focus の判定基準で解析する。製品・tests・受入記録は変更せず、Phase 06 の受入停止を維持する。今回はこの debug 記録だけを更新し、コミットしない。

- timestamp: 2026-10-28(利用者が実機再走の回数短縮を指定)
  decision: 利用者の「30回は長いのでこのぐらいにしませんか？」を受け、30回の再走要求を取り下げ、現在の結果で今回の実機検証を終了する。追加の再走は求めない。
  checked: `uat_row.py --summarize-diag` を実行。外部見張りありの新規13セッション(20261027T232527Z〜233948Z)を集計し、最後のセッションの outcome と harness_stop を確認。
  found: |
    外部見張り120msで12回完了・13回目は中断。完了12回は二次起動がすべて completed(47〜94ms)・focus_correct=true。全13セッションでctx停止区間0件、GetMessage停止(400ms以上)0件。中断回は二次起動の成功回に数えない。中断回の harness_stop.returncode=0。
    誘発成立かつcleanは3回(9・10・12回目)。誘発不成立3回(1・2・11回目)、誘発成立だがkeys-suspectが6回(3〜8回目)、中断1回を区別する。厳密比較の3回は停止0件・二次起動未完了0回。見張りの投稿は全13セッションで成功7096回・失敗0・拒否0・最大間隔139.2ms、health不良0回。厳密比較の3回では成功1962回。
    見張りなしの既存比較群(誘発成立かつclean)は8回中2回でctx/GetMessage停止を観測。見張りあり群には短いGetMessage区間が1回(1サンプル、誘発不成立回)あるが、幽霊の発生・解消を直接証明する情報ではない。
  conclusion: |
    今回の実機試験は良好で、外部見張りが正常動作していたことを確認。比較条件を満たす回は3回に限られ、停止が自然発生しなかった可能性や手順差を排除できないため、効果の確定・根治・製品修正完了とは扱わない。元の30回の基準を達成したとも扱わない。
    製品側の修正は未適用。今回の診断試験はここで終了し、既存証拠を保存する。Phase 06受入停止・元のW02失敗の扱いは維持する。今回はdebug記録のみ更新し、コード・tests・受入記録・バージョンは変更せず、コミットしない。

- timestamp: 2026-10-28(F1案の製品修正を承認)
  decision: 利用者は「F1案で製品修正へ進む（推奨）」への回答として「1」を指定。製品内での120ms周期WM_NULL投稿・終了処理・停止回復/既存機能の検証を承認。既存の外部見張りだけという制限をこの製品修正について更新する。追加の30回誘発再走・コミット・受入合格への変更・出荷は行わない。

- timestamp: 2026-10-28(F1実装・自動検証)
  changed: |
    pagefolio/startup_wake.py に UiThreadWake を追加。Tk初期化後、生成元UIスレッドのnative IDを保持し、補助スレッドがEvent.wait(0.120)の周期でPostThreadMessageW(tid, WM_NULL, 0, 0)だけを呼ぶ。Tk API・送信/入力/前面化APIは呼ばない。投稿失敗は連続する最初の1回を警告へ記録し次周期で再試行する。
    __main__.main の一次プロセスだけで開始し、finallyでroot破棄前に停止Eventをセットしてjoinする。起動途中の例外時も回収する。Win32 _API にポインター幅を保つWPARAM/LPARAM付きの投稿関数をバインドする。
    APP_VERSION・README・開発履歴をv1.10.1へ同期。配布ガイドの版例と版固定テストも更新。配布EXEは再生成しない。
  verification: |
    新規 tests/test_startup_wake.py の12件成功。生成元スレッドへのWM_NULL限定・二重開始・停止/開始失敗・異なるスレッドからの開始拒否・投稿失敗の再試行/警告抑制・生成元終了・正常/異常起動時の回収順・実Tclの人工停止と回復を確認。
    起動制御/フォーカス/通知/見張り/配布契約の対象185件中184件成功、配布ガイドの版例1件が不一致だったためガイドだけ修正し、その1件を再検証して成功。その後の単一プロセス全件pytestは2036 passed / 1 warning、435.92秒。警告は既知のPyMuPDF ByteString非推奨のみ。ログ: w02-preview-module-peer-expired-evidence/f1-20261028/pytest-full.txt。
    隔離コピーで製品のPostThreadMessageW呼出し1か所をTrueへ置換した場合、人工幽霊後の心拍再開は800.86ms（救済投稿待ち、製品投稿0回）。実製品は122.73ms（投稿7回）で再開。両方で前景不変・見張りスレッド回収を確認。リポジトリ本体をstash/revertせず、コピーだけを無効化して比較した。スクリプトと結果: f1-20261028/verify_fix_guardrail.py / guardrail.json。
    Ruff check . / Ruff format . 成功。全体formatが範囲外の既存文書コード例等61ファイルも整形したため、開始時にGit差分の無かった対象だけをHEADの作業ツリー形式へ復元した（整形差分はformatter-unrelated.patchに保管）。復元後の全体Ruff check . と変更Python8ファイルのformat --checkは成功。既存driver2本のSHA256は元のd784c62d... / 832cb76f...と一致。pagefolio.pyのAST成功。
  limits: |
    人工的なメッセージ消失からの回復を確認した。Windows実機で自然発生するきっかけの特定、製品内見張りでの元の実操作の解消確認、配布EXE再生成/実機受入は未実施。Phase 06受入停止・元W02失敗・既存証拠の扱いは維持。追加の30回再走は要求しない。利用者の通常操作での確認が届くまでresolvedにはしない。

- timestamp: 2026-10-28(通常操作での利用者確認・解決確定)
  source: 利用者の回答「確認できた」。直前の確認依頼は、ソース版でAlt+Tab後に二次起動し、画面と元の入力先へ戻ることの確認。
  decision: F1修正の通常操作確認を受領し、本デバッグをresolvedにする。正式なPhase 06受入・元のW02失敗記録の更新・配布EXE再生成・コミット・出荷はこの回答の対象に含めない。
  verification: 直前の自動検証2036 passed / 1 warning、Ruff/AST成功を維持。今回は確認記録・開発履歴・再発防止記録の更新だけであり、製品コード・入力・環境に変更がないため成功済み試験は再実行しない。

## Eliminated

- hypothesis: listener 側の欠陥(8 インスタンスの枯渇、過去行の二次が残した古いインスタンス、listener が terminal を返せない)
  evidence: 二次は接続し accepted を受信(ログ)。pipe 名は行ごとの namespace(uuid)と generation を含み、過去行のプロセスは回収済み。8 本の _serve は締切後のダンプで全て 836 の待機に復帰している。listener は締切まで 25ms 周期で callback を呼び、締切時に設計どおり切断した(233 の機序と整合)。terminal を作るのは Tk スレッドの _finish だけで、listener 単独では作れない設計。
  timestamp: 2026-10-25

- hypothesis: Tk への受け渡し(Queue / RLock / active_batch)のロジック欠陥で要求が滞留した
  evidence: _receive→queue.put_nowait は accepted と同時。_dispatch_pending は無例外で、初回実行で要求を回収し期限切れとして終端した(terminal ログ)。例外・TclError の出力は stderr に無い。active_batch が残っていた形跡も無い(restore_window 未呼出 = restored=0)。ロジックは「実行されれば」正しく動いており、実行されなかったことが問題。
  timestamp: 2026-10-25

- hypothesis: 手順汚染(PageFolio 内のクリック・キー)
  evidence: input_monitor で peer 完了までのマウスイベント 0・PageFolio 前面中のキー 0。peer 中の前景遷移は 06:25:00.178 の Alt+Tab のみ(締切 06:24:49.947 より後)。procedure_verdict=clean。
  timestamp: 2026-10-25

- hypothesis: Alt 単独タップによる Windows メニューモード(モーダルループ)が Tcl after を止めた
  evidence: 隔離実験 1 で、メニューバーのメニューモード(flags=4)・システムメニューモード(flags=12)の最中も after(50) は max gap 0.065〜0.079s で継続。
  timestamp: 2026-10-25

- hypothesis: システム時計の段差・調整で Tcl after が遅延した(after は壁時計依存という報告がある)
  evidence: ファイル mtime と tick の差が 14953.07 vs 14953ms、9999.83 vs 10000ms で一致(段差なし)。イベントログに時刻変更・W32Time の記録なし。
  timestamp: 2026-10-25

- hypothesis: 素の Tk が背景(非表示 / 画面外)で自発的に after を止める(Tcl 9.0.4 / Windows 11 の一般不具合)
  evidence: 隔離実験 2、150 秒×2 でギャップ 0。PageFolio 通過行 3 件も非活性状態で 0.1 秒以内に処理されている。
  timestamp: 2026-10-25

- hypothesis: preview ケース固有(中央プレビューCanvas の focus_set / tkdnd 登録が Tk ループに干渉)
  evidence: harness の preview ケースは `widget.focus_set()` と focus-ready の touch だけ(test_startup_windows.py:1845-1848, 1861)。W02/preview@script は同一手順で 2 回(055841Z, 060315Z)復帰成功。tkdnd の drop_target_register は preview / thumb 両方に行われる(file_drop.py)。preview 固有の機序は見当たらない(弱い反証: 母数が小さい)。
  timestamp: 2026-10-25

- hypothesis: 二次側(entry=module / Python 起動 / notice)が一次の Tk スレッドを止めた
  evidence: 二次の native 呼出しは AllowSetForegroundWindow(34016)・CreateFileW(pipe)・WriteFile/ReadFile・notice 窓の生成のみで、他プロセスのウィンドウへ SendMessage する経路は startup_win32.py に無い(grep 済み)。停止の開始が二次の要求より前か後かも保全証拠では区別できないが、通過行(同一二次コード)では停止しない。
  timestamp: 2026-10-25

- hypothesis: B「メッセージは捌くが Tcl のタイマーだけ不発」(Tcl の MsgWait のタイムアウト満了の取りこぼし・after の連鎖切れ)
  evidence: run1 の停止区間は ctx 切替がほぼ 0・サイクル 0 で、WaitReason が Tcl の通常待機(UserRequest)ではなく WrUserRequest。実験で Tcl の通常待機・INFINITE の MsgWait はどちらも UserRequest になることを確認済み。よって run1 の区間は Tcl の待機の外にいた。※原本の失敗は ctx 未計測なので、run1 と同一機序と仮定した上での否定。
  timestamp: 2026-10-25

- hypothesis: C「UI または他スレッドが CPU を使い続けていた(GIL 待ち・busy loop)」
  evidence: run1 の停止区間で UI の CPU/サイクル増分 0、他スレッド CPU 増分 0、実行中スレッド数 0。
  timestamp: 2026-10-25

- hypothesis: D「メニュー・移動サイズ・ポップアップの modal loop(gui_flags に現れるもの)」
  evidence: 停止区間の gui_flags=0、hwnd_menu_owner / hwnd_move_size / hwnd_capture も 0。窓移動の modal loop は 073830Z の gui_flags=2 の行で別に観測され、そこでは ctx 切替が動いていた(停止とは別物)。ただし flags に現れない win32k 内部の待機(独自 GetMessage ループ、ブロック中の SendMessage)は残る。
  timestamp: 2026-10-25

- hypothesis: ページング待ち・ストレージ遅延(外付け VHDX 起動・ページファイル 0)が停止の直接原因
  evidence: 停止区間の WaitReason は WrUserRequest(PageIn 系ではない)、プロセスの page fault / hard fault の増分も 0。I/O 待ちでスレッドが止まっていた形ではない。※ストレージ遅延が間接的に他プロセス(待機先)を遅らせた可能性までは否定できない。
  timestamp: 2026-10-25

- hypothesis: (a) UI スレッドが他スレッド/他プロセスの窓へのブロッキング SendMessage(NtUserMessageCall)で待機し、宛先(explorer・ctfmon・ターミナル・IME・OLE/tkdnd)が活性化まで返さない
  evidence: 停止中の syscall は NtUserGetMessage(msg ポインタが第1引数)で、NtUserMessageCall ではない(run4 146/146、run5 237/237)。全スレッドのスナップショットにブロッキング SendMessage を持つスレッドは無い。使い捨てプロセスで外部の待ち先が一切無くても同一シグネチャが再現できた。run2 の wait-target 行(SystemUserAdapterWindowClass)は宛先 tid が run2 の UI スレッド自身(自己参照の SetTimer)。※「待ち先が無い」ことの否定ではなく、「外部への同期待ちは不要」という否定。
  timestamp: 2026-10-25

- hypothesis: (b) Tk 以外の独自 GetMessage ループ(ネイティブダイアログ・COM/OLE・tkdnd のネスト ループ)に入っている
  evidence: UI スレッドの窓 9 つにモーダルダイアログ・候補窓の類は無く、gui_flags=0。GetMessage 呼び出し元は Tcl 通知器(tclWinNotify.c:531)で説明できる。tkdnd の DoDragDrop は呼ばれていない(ドラッグ操作無し)。※ GetMessage の呼出元スタックは未採取(GetThreadContext 不使用の制約)なので、Tcl 通知器であることは「ソース読解 + 使い捨てでの同一シグネチャ再現」による推定。
  timestamp: 2026-10-25

- hypothesis: 電力調整・EcoQoS・タイマー合体(Windows 11 のバックグラウンド省電力)がタイマーを不発にした
  evidence: 同一プロセスの _serve 8 本の 50ms タイムアウトが停止中も 19.7〜22 回/秒で正常に回り続けた(run4/run5)。UI スレッドの待機は MsgWait のタイムアウトではなく GetMessage(タイムアウト無し)で、タイマー精度の問題ではない。タイマー合体は遅らせるだけで 15〜30 秒止めない。
  timestamp: 2026-10-25

- hypothesis: Tk のキー処理(GetTranslatedKey の GetMessageA(WM_CHAR))で止まった
  evidence: 停止の開始は最後のキー入力の 0.4〜0.6 秒以上後(run4 はキー無し)、終了は文字入力を伴わない再活性化。フィルタ付き GetMessage は WM_CHAR 以外では復帰しないはず。低確度の否定(コードでは完全には除外できない。投稿 WM_NULL での回復を実機で確かめれば確定する)。
  timestamp: 2026-10-25

- hypothesis: 単純な WinEvent コールバック + 投稿メッセージで Tcl の GetMessage が眠る(MS KB2682659 型)
  evidence: 使い捨てで 6583 回のコールバック内投稿を行っても 0.5 秒超の停止は 0 回。実機の幽霊のきっかけとしては支持されない。
  timestamp: 2026-10-25

## Current Focus

- next_action: (2026-10-28 利用者確認後) 利用者の通常操作確認を受領し、本デバッグは解決済み。resolved/w02-preview-peer-expired.mdへ保管し、再発防止知見をknowledge-base.mdに記録して完了。追加再走は求めない。Phase 06受入停止・元W02失敗の扱いと既存証拠を維持。コミット/EXE再生成/出荷は未実施。

- previous_next_action(2026-10-28・再走短縮時): 利用者の指定で実機再走を12回完了・1回中断で終了。追加再走を求めず、外部見張りの暫定的な良好結果と検証限界を申し送る。製品修正は未承認・未適用。修正へ進む場合は既存F1〜F4の製品対策案から方針を決める。Phase 06の受入は停止のまま。

- test: F1の投稿境界・寿命・実Tcl回復12件、単一プロセス全件2036件、隔離コピーでの投稿無効化比較、Ruff/ASTは完了。
- expecting: 利用者がソース版のAlt+Tab後の二次起動と入力先復帰を「確認できた」と回答済み。本デバッグの追加確認は不要。

- hypothesis: |
    【確定(機構)】一次の Tk/Tcl(9.0.4)イベントループが、Tcl の Windows 通知器 `TclpWaitForEvent`(win/tclWinNotify.c:526-531)の `PeekMessageW(PM_NOREMOVE)` 真 →  `GetMessageW(&msg, NULL, 0, 0)` で無期限に眠り、その間 Tcl の `after` 連鎖(PageFolio の `_poll`、harness の `stop_poll`)がすべて止まる。GetMessage にはタイムアウトが無く、`TclNotifier` 窓(WM_TIMER フォールバックの前提。Tk がメニュー/ドラッグ/ダイアログで service mode ALL に入ったときに初めて作られる)も停止した 2 プロセスには存在しなかったため、次の「投稿メッセージ」が来るまで復帰しない。復帰は PageFolio の再活性化(WM_ACTIVATE 周辺で投稿・入力メッセージが届く)で起きる。原本(06:24:45〜06:25:00.525、約 15.5 秒)・run1(2.5 秒)・run4(15.4 秒)は再活性化で復帰、run5 は再活性化が無く 31.6 秒以上止まったまま。
    【未特定】「PeekMessage が真と言ったのに GetMessage には何も無い」状態(幽霊)を実機で起こすきっかけ。観測では Alt+Tab で他窓へ移り、着地(切替先が前景になる)と同時(±10ms)に発生し、可視の切替UI経由 31 回中 3 回(約 10%)。PageFolio の UI スレッドは Windows 11 のテキスト入力基盤(MSCTFIME UI・Default IME・BingIMESysMessageWindow・CoreMessaging の SystemUserAdapterWindowClass)と結合しており、離脱時にその部品が動く(NtUserSetTimer / NtUserDrainThreadCoreMessagingCompletions2 が離脱と同時に観測される)ため第一候補だが、直接証拠は無い。単純な WinEvent コールバック + 投稿メッセージでは自然発生しなかった。
- previous_test: (済)ソース読解(Tcl/Tk 9.0.4)、停止2件(run4/run5)の全スレッド・窓・syscall・ctx の再解析、使い捨てプロセスでの幽霊の人工再現(シグネチャ一致)と 2 種の対策(notifier 窓の作成 / 投稿 WM_NULL の見張り)の検証。(済・今回)driver 層の外部見張り `--external-wake-ms`(利用者承認済み 100〜150ms・PostThreadMessageW(WM_NULL) のみ)の実装と、別プロセスの投稿で使い捨ての人工幽霊が 1 周期内に解消すること・静的検査・拒否経路の機械的検証。(未)実機での幽霊の原因特定、対策の実機での効果確認(利用者の誘発再走 30 回で停止 0 件になるか)。
- previous_expecting: 対策を入れた実機(または driver 層の外部見張り)で誘発再走を 30 回前後(切替UI経由の離脱 30 回で、停止率 10% なら 0 件になる確率は約 4%、5% なら約 21%。1 回に離脱が平均 1.6 回あるので実際は約 1〜8%)行い、停止が 0 件で、診断(GetMessage の連続サンプル長)が見張り周期以内に収まれば、機構と対策が実機で確認できる。停止が残れば Tk の GetTranslatedKey 経路(フィルタ付き GetMessage)を疑う。
  確認の判定基準(見張りあり群・誘発成立かつclean・30 回以上): 二次起動の未完了 0 回、ctx 停止区間(1秒以上)0 件、GetMessage 停止(400ms 以上)0 件で最長が周期+誤差程度(目安 250ms 以下)、投稿の失敗/拒否が 0 か僅か、投稿の最大間隔が周期の約 2 倍以下、見張りが期待どおりでない回 0。さらに『GetMessage の短い区間が見えて直ちに消える』回があれば幽霊が起き、解消された直接証拠(予防ではなく解消)。停止が出ても『投稿が流れている最中の停止』が 0 なら見張りの不備(機構の否定ではない)。『投稿が流れている最中の停止』が出たら、WM_NULL で解けない別経路(Tk の GetTranslatedKey のフィルタ付き GetMessage など)。
- previous_next_action(2026-10-25 第3チェックポイント回答後・現在): 実装・機械的検証・sha256 記録は完了(Evidence「外部見張りの実装と機構確認」)。利用者へ 30 回の誘発再走手順を CHECKPOINT(human-action)で返し、利用者が `--external-wake-ms 120` 付きの再走 30 回(+ `--summarize-diag`)を実施するのを待つ。結果が届いたら 06-05-evidence/debug-w02-preview-peer-expired/ の新セッションを読み取り専用で解析し(見張りありの群: 停止0件・最長 GetMessage<=周期程度・見張りの health・GetMessage 短区間=解消された幽霊の有無)、機構と対策の確認可否を判定する。停止が残れば『停止のうち投稿が流れている最中のもの』と GetMessage の呼出し元(Tk GetTranslatedKey のフィルタ付き GetMessage)を次の仮説にする。以下は旧 next_action(参考): 呼び出し元へ ROOT CAUSE FOUND(機構確定・きっかけ未特定)を返し、(1) 製品側の対策を入れてよいか(推奨: UI ループの見張り。pagefolio/* の変更は利用者の承認が必要)、(2) 承認前の確認として driver 層の外部見張り(別プロセスから PageFolio の UI スレッドへ投稿 WM_NULL。製品・tests 無変更)で誘発再走を行うか、(3) 幽霊の原因を特定する実機計測(WH_GETMESSAGE フックでメッセージを記録するカナリア)を行うか、の判断を求める。Phase 06 受入は停止のまま、W02/preview@module(062551Z)は fail のまま。

## Resolution

- root_cause: |
    【近因(確定)】一次の Tk メインスレッドが、要求受理後の約 15.5 秒間、50ms 周期の `_poll`→`_dispatch_pending`(startup_control.py:196-247)を実行しなかった。要求は `_receive`(同 146-189)で accepted を返して queue に入ったまま締切(28860484)を超え、listener は設計どおり締切で terminal を書かず切断(startup_win32.py:874-882)、二次は 233 を connection_failed として受け(同 991-996、締切境界の競合で expired でなく connection_failed)、notice は expired で表示された。一次が初めて要求を処理したのは tick 28871062(06:25:00.525Z)で、既に期限切れのため `restore_window` は呼ばれず(restored=0、focus-result.json なし)、_finish が expired を出しただけ。この時刻は利用者の Alt+Tab 解放による PageFolio 窓の活性化(06:25:00.523〜00.531Z)と ±25ms で一致する。
    【根因(機構は確定、きっかけは未特定)】Tk/Tcl 9.0.4 の通知器が、Windows 11 build 26300 上で Alt+Tab の着地直後に、タイムアウトの無い `GetMessageW` に入って起きなくなる。
      1. 通知器の構造: `TclpWaitForEvent` は `MsgWaitForMultipleObjectsEx(timeout)` で after の満了を待つが、起きた後に `PeekMessageW(PM_NOREMOVE)` が真なら `GetMessageW` を呼ぶ。GetMessage はタイムアウトを持たない(tclWinNotify.c:504-531)。
      2. 欠けている安全網: `TclNotifier` 窓が無いと `TclpSetTimer` は何もせず WM_TIMER が無い(同 278-280)。この窓は Tk がメニュー(WM_INITMENU)・ウィンドウ移動/サイズ変更・ダイアログ・スクロールバー操作で service mode ALL に入ったときに初めて作られる(tkWinMenu.c:1171、tkWinWm.c:7865 ほか)。停止した run4/run5 のプロセスにこの窓は無く(EnumWindows)、UAT 手順(PageFolio を触らない)では未作成のままになる。
      3. きっかけ(未特定): Alt+Tab 後の着地で Peek は真だが GetMessage には取り出すものが無い、という食い違いが約 10%(可視の切替UI経由 31 回中 3 回)で起きる。UI スレッドは Windows 11 のテキスト入力基盤(MSCTFIME UI / Default IME / BingIMESysMessageWindow / CoreMessaging の SystemUserAdapterWindowClass)と結合している。
      4. 結果: GetMessage で眠り続け、ctx 0・CPU 0・サイクル 0・IsHungAppWindow 偽。after 連鎖(`_poll`、`stop_poll`)が全停止。送信メッセージ(他プロセスからの SendMessage)には応じるが GetMessage の外には出ない(NtCallbackReturn のまばたき)。投稿メッセージ(再活性化に伴うもの)で復帰する。
    【反証済み】Python 層、listener、手順汚染、時計段差、Alt メニューモード、Tcl タイマーの取りこぼし(B)、CPU 消費(C)、flags に現れる modal(D)、ページング待ち、外部へのブロッキング SendMessage、電力調整・EcoQoS、Tk キー処理の GetMessage(低確度)、単純な WinEvent コールバック。
    【影響範囲】停止の間は PageFolio の Tk `after` 全般(バックグラウンド処理の進捗ポーリング・トースト・二次起動の前面化要求の処理)が止まる。利用者が PageFolio を触る(メニュー・ドラッグ等)前の状態で Alt+Tab し、約 5〜10% の確率でこの状態になる。二次起動の前面化は 5 秒期限内に処理できず expired になる(今回の失敗)。一度でもメニュー等で TclNotifier 窓ができたプロセスは WM_TIMER が GetMessage を最長でも次の after の間隔で起こすので影響を受けない(使い捨てで確認。実機では未確認)。
- fix: F1を利用者承認後に適用。UiThreadWakeが一次プロセスのUIスレッドへ120ms周期でWM_NULLを投稿し、Tk通知器の無期限GetMessage待ちを起こす。Tk初期化後に開始し、root破棄前に停止・回収する。Tk APIや入力/前面化APIは使わない。二次起動の5秒期限は維持。ソース版v1.10.1、EXE未再生成。
- verification:
    target_test: { result: pass, suite: tests/test_startup_wake.py, tests: 12 }
    mutation_check: { result: skipped, reason_if_skipped: "PythonプロジェクトにStryker設定なし。補助検証として投稿1か所を無効化したコピーを使い、回復の400ms基準を満たさなくなることを確認（800.86ms）" }
    no_op_deletion: { result: pass, deletion_justified_by_rca: false, detail: "製品の振る舞い削除・期限延長・合否条件緩和なし。投稿と寿命管理を追加" }
    adjacent_tests: { result: pass, suites_run: ["単一プロセス全件pytest: 2036 passed / 1 warning", "Ruff check .", "変更Python8ファイルformat --check", "pagefolio.py AST"] }
    revert_and_reconfirm: { result: pass, bug_returned_on_revert: true, fixed_on_reapply: true, method: "製品投稿1か所を隔離コピーで無効化（800.86ms停止）→実製品（122.73msで回復）。既存作業をstashしない" }
    guardrail_verdict: accepted
    human_verification: { result: pass, date: 2026-10-28, source: "利用者回答: 確認できた", scope: "ソース版での通常操作。Phase 06正式受入とは別" }
- driver_files_from_previous_cycles: [.planning/phases/06-release-validation/06-05-drivers/uat_row.py (sha256 d784c62d4259bb91c1671bd39cace4e00e1cc6c01da30d80c3b304b777a3a8d6。--external-wake-ms 引数・session 記録・配線・報告・--summarize-diag の群別集計・--check-diagnostics (3c)), .planning/phases/06-release-validation/06-05-drivers/ui_thread_probe.py (sha256 832cb76f9efd391ca0063d2f94d2fbdbc265756d782d2936b2e5ebf892146e6b。verify_post_target / post_wm_null / WakeLog / wake_once / getmessage 区間 / wake_health / 群別集計 / 静的検査 / 幽霊の実API確認)] (いずれも未コミット・driver 層のみ。製品・tests・pyproject.toml・証拠原本は無変更。前サイクルの driver は uat_row.py sha256 80e32e1143a114a55a2fd48157f8f7be18262860a00845a34b584753c6817274 / ui_thread_probe.py sha256 e9a4c9a914a4979a9492c36589c6d46b641ea3c170cc077b8536ff8ffe2e197a で、scratchpad に写し uat_row.v2.py / ui_thread_probe.v2.py を保存。今回の scratchpad: run_ghost_only.py / mutation_check.py(+ mut/)/ rehearse3.py(+ rehearse_wake_out/)/ offline_v*.txt / check_diagnostics_v4〜v6.txt / check_monitor_v4,v5.txt。前サイクルまでの解析・実験の scratchpad: dump_run.py / win_samples.py / landings.py / age_analysis.py / landing_burst.py(解析、読み取り専用)、ghost_child.py / ghost_exp.py / winevent_child.py / winevent_exp.py / pw_check.py(使い捨て子プロセスでの再現・対策検証。出力は scratchpad の ghost-* / we-* / pw-* ディレクトリ)、tclsrc/ tksrc/(Tcl/Tk 9.0.4 ソースの写し。読解のみ))

- files_changed: [pagefolio/startup_wake.py, pagefolio/__main__.py, pagefolio/startup_win32.py, tests/test_startup_wake.py, tests/startup_wake_child.py, pagefolio/constants.py, tests/test_release_contract.py, README.md, distribution/はじめに.md, 開発履歴.md, .planning/debug/resolved/w02-preview-peer-expired.md, .planning/debug/knowledge-base.md, .planning/debug/w02-preview-module-peer-expired-evidence/f1-20261028/]

## Prevention

- コード側の因果: 起動要求がacceptedのまま残る → UIのafterポーリングが止まる → TclのGetMessageに時間上限がない → afterだけではその待ちを起こせない。UIループとは独立した投稿で回復させる。
- 環境側の因果: WindowsでAlt+Tabの切替先が前景になる直後に停止を観測 → メッセージの有無の食い違いを人工再現できる → 自然発生のきっかけは未特定。IMEやストレージ等を確定原因として扱わず、通知器の待機停止そのものを再発防止の対象とする。
- why_not_caught: 従来の期限処理試験ではWindows通知器のメッセージ消失による無期限待ちからの回復を検証していなかった。
- recurrence_guard: tests/test_startup_wake.py:test_native_tcl_getmessage_stall_recovers_with_product_wake と test_entry_stops_wake_before_root_destruction。人工停止からの回復と寿命管理を検証し、全件2036件成功。
- semantic_index: skipped（利用可能なMemPalace連携ツールがないため、knowledge-base.mdを永続的な参照先とする）。
- commit: skipped（この調査でのコミット禁止を維持）。
