---
phase: 04-startup-control
verified: 2026-10-24T07:40:00Z
status: passed
score: 21/21 must-haves verified
covered_files: [".planning/phases/04-startup-control/04-01-PLAN.md", ".planning/phases/04-startup-control/04-01-SUMMARY.md", ".planning/phases/04-startup-control/04-02-PLAN.md", ".planning/phases/04-startup-control/04-02-SUMMARY.md", ".planning/phases/04-startup-control/04-03-PLAN.md", ".planning/phases/04-startup-control/04-03-SUMMARY.md", ".planning/phases/04-startup-control/04-04-PLAN.md", ".planning/phases/04-startup-control/04-04-SUMMARY.md", ".planning/phases/04-startup-control/04-05-PLAN.md", ".planning/phases/04-startup-control/04-05-SUMMARY.md", ".planning/phases/04-startup-control/04-06-EVIDENCE.json", ".planning/phases/04-startup-control/04-06-PLAN.md", ".planning/phases/04-startup-control/04-06-SUMMARY.md", "pagefolio.py", "pagefolio/__init__.py", "pagefolio/__main__.py", "pagefolio/app.py", "pagefolio/lang.py", "pagefolio/startup_control.py", "pagefolio/startup_focus.py", "pagefolio/startup_notice.py", "pagefolio/startup_win32.py", "tests/test_gsd_dod.py", "tests/test_startup_control.py", "tests/test_startup_focus.py", "tests/test_startup_notice.py", "tests/test_startup_windows.py"]
covered_digest: "v3:sha256:5011dcc61c28d464c999fb55d198dffacd9a78688bc34240ef1dfb67b20be168"
behavior_unverified: 0
overrides_applied: 0
human_verification: []
re_verification:
  previous_status: passed
  previous_score: 21/21
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  trigger: "Phase 5 (be8f78a..7bbb06c) とdebugコミット(be1eb19, 3925d5f)が app.py / lang.py / startup_focus.py / test_startup_focus.py / test_startup_windows.py を変更し、前回の指紋(v3:sha256:9a78307802b2...)が失効"
flagged_prohibitions: 3
unclassified_edges: 5
decision_coverage:
  honored: 16
  total: 16
  not_honored: []
deferred:
  - truth: "W01〜W12の実入力・見た目・OS拒否・DPI/UAC・別session・実配布EXEの最終人手受入"
    addressed_in: "Phase 6 / V110-QA-02"
    evidence: "2026-10-22承認済みROADMAP受入範囲改訂と06-UAT-CARRYOVER全行(全て not-run)。全必須passまでリリース停止。本報告はこれらをpassとしない"
  - truth: "並行負荷の二次終了15.5秒予算適合性の再評価(W07b)"
    addressed_in: "Phase 6 / W07b"
    evidence: "06-UAT-CARRYOVERは15609ms超過(109ms超過)と15140ms単独を両方保持し条件/契約を再評価する"
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

# Phase 4: 起動制御と既存画面への復帰 検証報告(再検証)

**目標:** 利用者が2回目に PageFolio を起動しても作業画面が増えず、進行中の作業を保ったまま既存画面へ戻れる。
**判定:** passed(Phase 4の実装/自動受入範囲 21/21)。Phase 6の実機受入は未実施のまま。
**検証種別:** 再検証。前回(2026-10-21T22:12Z、21/21 passed)の指紋が、Phase 5とdebugコミットによる `app.py` / `lang.py` / `startup_focus.py` / `tests/test_startup_focus.py` / `tests/test_startup_windows.py` の変更で失効したため、現行コミット済みコードに対してPhase 4のtruthが保たれているかを再評価した。コミットなし。

**3 flagged prohibitions — unverified-prohibition — human review recommended.** 禁止事項3件とedge5件は未解決のままPhase 6へ明示移管しており、リリース承認を意味しない。W人手項目は全行 not-run のままで、本報告はpassへ変更していない。Phase 4の合格は自動範囲に限り、最終人手受入の代替にはしない。

## 既知の未解決事項(解決済みとして扱わない)

次は調査継続中または未分類であり、本検証はいずれも解決済みと報告しない。

- **DEP-05-REGRESSION**: `.planning/debug/dep-05-regression.md`。未解除・監視継続。
- **owner_missing**: `.planning/debug/simultaneous-owner-missing.md`。status: investigating。`test_simultaneous_real_processes_construct_one_editor[2]` で一度だけ fresh 二次が `owner_missing` となった事象は未再現・原因未確定(因果未証明)。その後の単一全件は pass だが、原因修復の証拠ではない。
- **通知前景不一致**: 通知8プロセス試験で前景HWNDが変化した事象。原因未確定。
- **Tcl warning**: `test_ocr_engine.py` のTcl interpreter別thread破棄に由来する警告。因果不明。
- **未分類edge 5件**: Phase 6で実機照合する。
- **WR-01**: 並行負荷の二次終了 15609ms(15.5秒上限を109ms超過)と単独 15140ms は両方保持。

## 再検証: Phase 5変更による回帰分析

前回検証基点 `15fde05`(2026-10-22 07:05 JST)から現行 HEAD までの、Phase 4被覆ファイルの差分を精読した。差分があるのは5ファイルのみで、`__main__.py` / `__init__.py` / `pagefolio.py` / `startup_control.py` / `startup_notice.py` / `startup_win32.py` / `test_startup_control.py` / `test_startup_notice.py` / `test_gsd_dod.py` は基点から不変。

| ファイル | 変更内容 | Phase 4 must-haveへの影響 |
|---|---|---|
| `pagefolio/app.py` (約+237行) | 設定読込結果の保持、設定通知キュー(`_enqueue_config_notice` 等)、root への `<Destroy>` / `<Unmap>` / `<Map>` を **add="+"** で追加bind、`_persist_settings`、`_quit` の順序変更 | 影響なし。下記参照 |
| `pagefolio/lang.py` (+26) | `config_load_*` / `config_save_*` の ja/en 文言追加のみ。`startup_notice_*` キーは不変 | 影響なし(additive) |
| `pagefolio/startup_focus.py` (+6/-1) | 入力先選択で、前面化により一時的に toplevel 自身へ移った focus より記憶した入力先を優先(`widget is not target` 条件) | D-04 を強化。回帰なし |
| `tests/test_startup_focus.py` | `toplevel_focused` パラメータ追加と新規2試験(現在の入力先優先・toplevel観測のみのとき last を使用) | 既存試験の主張を弱めず追加のみ |
| `tests/test_startup_windows.py` | `_finish` の診断強化(pipe保持者報告)、前景監査・終了入口監査の試験追加、同時起動試験に `slow` ケース追加、harnessの `_quit` 計装 | 既存試験の削除/skip/xfail化なし。削除行は harness 内の診断化に伴う置換のみ |

`app.py` 変更の個別確認:

- `_quit`(truth 2「終了確認をキャンセルした場合は既存画面がそのまま使用できる」): 確認ダイアログを先に出し、キャンセル時は保存・Undo解放・doc close・destroy の**どれも行わず**に return する。旧実装は `_save_window_state()` を確認前に呼んでいたため、キャンセル時の副作用はむしろ減った。cancel保持は維持・強化。
- `<Map>` / `<Unmap>` / `<Destroy>` の追加bind: すべて `add="+"` で、`FocusRestorer` の `<Configure>` / `<Map>` bind(`startup_focus.py:61-66`、キー指定で個別 unbind)と共存する。`FocusRestorer` の bind 解除は自分のキーのみなので相互に壊さない。
- 設定通知(Toast)は `toast.py` 内に `focus_force` / `focus_set` / `grab` / `lift` / `attributes` を持たず、入力先を奪わない。`_config_modal_active` は `grab_current()` を参照するだけで、モーダルの閉鎖や再作成をしない。D-12 / D-13 の「入力先・編集中ダイアログを変えない」は保たれる。
- `_rebuild_ui` に `_prepare_config_notice_rebuild()` が加わったが、子widget破棄の既存挙動は不変(設定ダイアログ呼出しの注意書きも維持)。
- `app._startup_focus = None`(`app.py:140`)と `__main__.py:63-65` の restorer 登録は不変。`__main__.py` の finally での `focus.close()` → root 破棄 → `coordinator.close()` の順も不変で、新しい `<Destroy>` ハンドラ(`_close_config_notices`)は root 破棄時に timer を取り消すだけ。

結論: Phase 5の変更はPhase 4のtruth 1〜21のいずれも回帰させていない。

## Goal Achievement

### Observable Truths

ROADMAP5基準を先頭に置き、全PLANの追加truthを重複統合した。VERIFIEDは現行Phase 4自動範囲。C/F/Nはそれぞれ tests/test_startup_control.py / test_startup_focus.py / test_startup_notice.py、Wは test_startup_windows.py を指す。

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | 同一 Windows ログインセッションで、対応版同士の別版・別配置・Python/EXE 混在を含む連続・同時起動をしても、編集画面は1つだけになる。 | VERIFIED(実装/自動範囲) | `__main__.py:19-42` で claim が root 生成前、`pagefolio/__init__.py` 遅延 import。win32 の固定 Local 名。W の同時起動(2/8/slow)、両入口/別配置9組、版/配置/frozen identity 試験。現行バイトの全件 pass。実EXE/別sessionはPhase 6。owner_missing 単発事象は未解決のまま(上記) |
| 2 | 正常終了・強制終了・起動途中の異常終了後に再起動でき、終了確認をキャンセルした場合は既存画面がそのまま使用できる。 | VERIFIED | main finally で root 破棄後 close。部分 descriptor/token の逆順解放と再起動試験。現行 `app._quit` は確認キャンセル時に副作用なしで return(回帰分析参照) |
| 3 | 排他判定または既存画面への連絡に失敗した場合、利用者は「起動済み」と異なる理由を認識でき、後続起動は追加画面を作らず有限時間で終了する。 | VERIFIED | `__main__.py:19-42` の構築 OSError 捕捉、独立 Win32NoticeBackend、固定 check_failed。実 main→native 窓、追加編集画面0・案内1・foreground 不変。通知不能は両入口 exit1。W の constructor 系を今回14件の対象実走で再確認 |
| 4 | 2回目の起動で最小化した既存画面が復元され、OS が許せば前面に出る。前面化を拒否された場合も視覚通知から既存画面を見つけられる。 | VERIFIED(実装/自動範囲) | FocusRestorer.restore、placement/foreground、flash3回250ms＋1000ms停止。F の placement/foreground-denied 試験(今回 pass)。実OS目視はPhase 6 |
| 5 | 未保存編集、Undo/Redo、進行中の OCR、開いているモーダル操作を保ったまま既存画面で作業を続けられる。 | VERIFIED(実装/自動範囲) | F の実PDF/Blob と4手 Undo/Redo、OCR 同一 worker 完了、modal grab/native popup の入力先維持。startup_focus の入力先優先修正は追加試験2件で補強。人手内容照合はPhase 6 |
| 6 | 完了live/archiveのvalidated義務と未完了draft開発を両立する | VERIFIED | `test_gsd_dod.py` を今回実走(下記 164 passed の内数) |
| 7 | D-01 正常復帰でヘッダー/OCR進捗を維持しterminalを確認する | VERIFIED | `_dispatch_pending` は status/doc を書かない。accepted だけでは戻らず terminal 照合。C/F 実走 |
| 8 | D-05/D-06 準備/接続/送受信/ACKが共通5秒期限を持つ | VERIFIED | `started_tick` を main 入口で取得し一度だけ +5000。C の要求別期限試験 |
| 9 | D-08 失効queue/世代の要求は後で前面化しない | VERIFIED | `control._valid` を受信/dispatch/副作用直前に適用。C/F 実走 |
| 10 | D-07 確認済み初期化中process死亡後だけ原子的claimを1回試す | VERIFIED | control の state/handle と win32 の atomic wait。C 実走 |
| 11 | D-03 要求とterminal後500ms連打を延長なしに集約する | VERIFIED | 固定 first_terminal_tick。C の cooldown/8要求合流試験 |
| 12 | D-02 最小化前の最大化/通常geometryへ戻す | VERIFIED | focus の `_remember_window_state` と restore。F 実走 |
| 13 | D-04 直前の生存入力先を維持する | VERIFIED(強化) | `_focus_widget` は `widget is not target` を条件に記憶した入力先を優先(Phase 5後の修正)。F の `toplevel_focused` 2値パラメータ化試験と新規2試験が pass |
| 14 | D-13 grab/native最深modalと入力/選択を維持する | VERIFIED(自動範囲) | `_select_activation_target` / owned popup、widget 再作成なし。F 実走。実 messagebox/入れ子操作は W05(Phase 6) |
| 15 | D-14/D-15/D-16 拒否は有限点滅だけで自動再前面化しない | VERIFIED | flash flags=2/count3/250ms、STOP だけ。F/N 実走 |
| 16 | D-09 確認済み理由と次の操作で案内する | VERIFIED | 初期化失敗は未確認 owner を仮定せず CHECK_FAILED 固定文言を既存 LANG→native 通知へ。`startup_notice_*` キーは lang.py で不変(Phase 5は config_* の追加のみ) |
| 17 | D-10 手動閉鎖/初回10秒自動閉鎖 | VERIFIED(自動範囲) | NativeNoticeLifetime、固定 deadline と timer。N の9999/10000境界。新窓実クリックは W09(Phase 6) |
| 18 | D-11 同原因をprocess間で集約し期限を更新しない | VERIFIED | NoticeLease の原因 hash、初回 deadline 更新拒否。W の旧新両順8process集約 |
| 19 | D-12 案内表示/閉鎖が入力先を変えない | VERIFIED(自動範囲) | NOACTIVATE/TOOLWINDOW/MA_NOACTIVATE/SW_SHOWNOACTIVATE。W の実 main 非活性案内試験(今回 pass)。前景不一致の別事象は未解決(上記) |
| 20 | D-01〜16の自動/実機/未実施を分け、Phase6へ追跡する | VERIFIED | 04-WINDOWS-UAT と 04-05-EVIDENCE の各 W、06-UAT-CARRYOVER 全行(not-run 維持) |
| 21 | A1〜A5成立性を本番Windows API/生証拠で確認する | VERIFIED | 04-HUMAN-EVIDENCE / TRACER-EVIDENCE の生証拠。旧primitive証拠の適用範囲を保持 |

**Score:** 21/21。禁止事項3件は肯定truth得点に混ぜず、UNCERTAIN(WARNING)を保持する。

### Deferred Items

| Item | Addressed In | Evidence |
|---|---|---|
| W01〜W12 人手部分、別session、DPI/UAC、OS拒否、実EXE | Phase 6 V110-QA-02 | 06-UAT-CARRYOVER 全行 `not-run`。W11 は別アカウント準備不能で not-run を維持。**Phase 4では pending 扱いにせず、Phase 6が所有する** |
| 15.5秒予算の負荷適合性 | Phase 6 W07b | 15609ms(109ms超過)/15140ms 両方保持、WR-01 deferred |
| 禁止事項3件 flagged-unverified、edge5件 unclassified/unresolved | Phase 6 V110-QA-02 | 移管正本の照合義務。descriptor 無し項目を resolved へ変更しない |

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `pagefolio/startup_control.py` | claim/queue/期限/ACK | VERIFIED | 基点から不変。main が構築し backend 注入 |
| `pagefolio/startup_win32.py` | OS所有権/IPC/native案内 | VERIFIED | 基点から不変。本番 factory として main から使用、Win32NoticeBackend 基底 |
| `pagefolio/startup_focus.py` | 同一appの復帰 | VERIFIED | 入力先優先の+6/-1行のみ変更。main:63-65 で同じ app/backend へ接続 |
| `pagefolio/startup_notice.py` / `lang.py` | 三分類の固定案内 | VERIFIED | notice は不変。lang は additive(config_*)のみで startup_notice_* 不変 |
| `pagefolio/app.py` | 既存画面(終了/再構築/設定通知) | VERIFIED | `_quit` cancel 保持。bind は add="+"。Toast は入力先を奪わない |
| `tests/test_startup_{control,focus,notice,windows}.py` / `test_gsd_dod.py` | 状態/障害/実Windows検証 | VERIFIED | 収集: windows 74件、focus+control 84件。削除/skip/xfail 化なし |
| 04-TRACER-EVIDENCE / WINDOWS-UAT / VALIDATION / 04-06-EVIDENCE | 実測と被覆 | VERIFIED | 前回照合済み。生JSON/not-run 分離を保持 |

### Key Link Verification

前回報告の13リンクについて、基点以降に変更のあった focus↔main↔app の経路のみ再確認した。CLI `verify.key-links` の「Target not referenced」は Python のドット import/コンストラクタ注入と日本語 via の文字列検査による偽陰性(前回と同じ)で、実呼出しと名前付き実試験で WIRED と判断した。

| From | To | Via | Status | Details |
|---|---|---|---|---|
| __main__ | control/backend | StartupCoordinator(Win32Backend()) | WIRED | `__main__.py:19-42` 変更なし |
| __main__/app | focus | 同じ app/root | WIRED | `__main__.py:61-66` で `app._startup_focus` と `backend.focus_restorer` に同一 restorer 登録、`attach_tk` は after_idle |
| focus | app の bind | `<Map>` / `<Configure>` add="+" | WIRED | app の `<Map>`/`<Unmap>`/`<Destroy>` も add="+"、focus はキー指定 unbind で共存 |
| main | notice→win32 | backend.show_notice / show_startup_initialization_failure | WIRED | 不変 |
| notice | lang | LANG[language][keys[reason]] | WIRED | `startup_notice_*` キー不変 |
| windows test | main | runpy/入口の実行 | WIRED | 両入口/relocated 子 bootstrap |
| その他(control↔win32, focus↔win32, WINDOWS-UAT↔VALIDATION, notice↔win32 等) | | | WIRED | 対象ファイル不変のため前回結論を維持 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| ownership | snapshot identity/state | Win32 mutex/mapping＋OS process handle | yes | FLOWING |
| activation | ActivationRequest/Reply | 実pipe→queue→同じTk root→terminal ACK | yes | FLOWING |
| focus | widget/placement/popup | 既存 app/root の FocusIn/Configure/grab と OS HWND。入力先は現在 focus_get/記憶値/last の順で生存 widget のみ | yes | FLOWING |
| notice | reason/text/deadline | 起動結果＋検証済み owner→LANG、GetTickCount64、原因別共有 snapshot | yes | FLOWING |
| 独立notice | check_failed/text/期限 | main の構築 OSError→StartupOutcome→LANG、OS tick と共有 NoticeLease | yes | FLOWING |

### Behavioral Spot-Checks

回帰証拠は次の2系統。(a) 現行バイトに対する単一プロセス全件 pytest(06-03、本検証では再実行せず引用)、(b) 本検証で独立実走した対象試験。

(a) の対応: `pagefolio/` の最終変更は 2026-10-24 15:09 JST(`constants.py` の `APP_VERSION` のみ、コミット c09baea)、`app.py` は 01:49、`startup_focus.py` は 2026-10-22、`tests/test_startup_windows.py` のファイル更新時刻は 2026-10-23 22:35 で、全件ログ(2026-10-24 15:51 JST)より前。全件ログ以降に変更されたバイトはなく、3925d5f は同一バイトのコミットである。

| Behavior | Command | Result | Status |
|---|---|---|---|
| 現行バイトの単一プロセス全件 | `.planning/phases/06-release-validation/06-03-task2-full.txt`(basetemp `C:\Users\shdwf\AppData\Local\Temp\pf06_03_t2_full_a415ec3d9adf4122`) | 1969 passed, 1 warning in 361.39s / EXIT=0。除外なし | PASS(引用) |
| control/focus/notice/DoD | `.venv\Scripts\python.exe -m pytest -q tests/test_startup_control.py tests/test_startup_focus.py tests/test_startup_notice.py tests/test_gsd_dod.py --basetemp=%LOCALAPPDATA%\Temp\pf04_reverify_<ts>` | 164 passed, 1 warning, 0.41s | PASS(本検証で実走) |
| 実Windows 対象(constructor失敗・初期化通知・期限・同時起動・再起動・最小化) | `... pytest -q tests/test_startup_windows.py -k "constructor_failure or backend_constructor or initialization_notice or initialization_cleanup or notice_deadline or simultaneous_real or two_launch or restart or minimized"` | 14 passed, 60 deselected, 1 warning, 90.83s | PASS(本検証で実走) |

警告1件は既存の PyMuPDF `typing.ByteString` 非推奨で、failure/ERROR/対象 skip は0。症状①(TclError セットアップ ERROR)は CLAUDE.md の通り再発し得る既知の環境症状であり、今回の実走では観測されなかったが「非再現」とは扱わない。

### Probe Execution

該当 probe-*.sh の宣言/実体なし。Python の通常試験と明示 A/W harness が実行経路。Step 7c 非該当。

### Requirements Coverage

PLAN frontmatter の `requirements` 宣言(01〜06 の合併)は5件で、REQUIREMENTS.md の Phase 4 割当(START-01〜03、FOCUS-01/02)と一致。ORPHANED 0。

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| V110-START-01 | 01/02/05 | 同session共通ID・対応版/配置/入口 | SATISFIED(Phase 4範囲) | truth 1/21。実EXE/別session人手は Phase 6 |
| V110-START-02 | 01/02/05/06 | 終了/異常終了後再起動・cancel | SATISFIED(Phase 4範囲) | truth 2/10。`_quit` cancel の副作用なし |
| V110-START-03 | 01/02/04/05/06 | 判定/連絡失敗の識別・有限終了 | SATISFIED(Phase 4範囲) | truth 3/16。負荷予算 WR-01 は別途 Phase 6 |
| V110-FOCUS-01 | 01/03/04/05 | 復元/許可前面化/拒否強調 | SATISFIED(Phase 4範囲) | truth 4/12/15。OS実目視は Phase 6 |
| V110-FOCUS-02 | 01/03/05 | 作業/Undo/OCR/モーダル維持 | SATISFIED(Phase 4範囲) | truth 5/7/13/14 |

REQUIREMENTS.md は5件とも `[x]` / Complete だが、これは Phase 4 の自動範囲の完了であり、最終実機受入(V110-QA-02)は Phase 6 で未実施。

### Decision Coverage

前回の `check.decision-coverage-verify` 結果(honored 16 / total 16、not_honored=[])を引き継ぐ。CONTEXT.md の決定に影響する変更は D-04(入力先維持)の強化のみで、honored のまま。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| tests/test_gsd_dod.py | 216/225 | TBD という文法リテラル | Info | 未完了件数表記の解析用。負債コメントではない |
| startup_win32.py | 287/307/819 | 並行負荷で予算超過 | WARNING / WR-01 | Phase 6 再評価へ移管、元数値保持 |
| tests/test_startup_windows.py | 計装 | debug 用の終了/前景監査 harness が本番試験ファイルに同居 | Info | 既存 assertion は不変。製品コードへの影響なし |

未参照 FIXME/XXX/TBD コメント、placeholder、空 handler による未実装は検出なし(Phase 4被覆ファイルの変更差分範囲)。

### Human Verification Required

現在の Phase 4 範囲に未了の自動項目はない。W01〜W12 の人手部分(実入力・目視・OS拒否・DPI/UAC・別session・実EXE)は**承認済み再計画により Phase 6 の 06-UAT-CARRYOVER が単一の引受先**であり、全行 not-run のまま。Phase 4 ではこれらを pass と記録せず、Phase 4 側の保留項目(`human_verification`)としても持たない。人手検証不要という判定ではなく、全必須項目に実測根拠付き pass が揃うまで Phase 6 完了・v1.10.0 リリースは停止される。

### Gaps Summary

BLOCKER なし。Phase 5 と debug コミットによる `app.py` / `lang.py` / `startup_focus.py` の変更は、Phase 4 の21 truth のいずれも回帰させていない(`_quit` のキャンセル保持は強化、focus の入力先維持も強化、lang は additive、bind は add="+" で共存)。現行バイトの単一プロセス全件(1969 passed)と本検証の対象実走(164 + 14 passed)で確認した。DEP-05-REGRESSION、owner_missing、通知前景不一致、Tcl warning、未分類 edge 5件、WR-01 は解決済みと扱わず、禁止事項3件は flagged-unverified、W 人手部分は not-run を維持して Phase 6 へ引き継ぐ。

---

_Verified: 2026-10-24T07:40:00Z_
_Verifier: Claude (gsd-verifier、再検証)_
