---
phase: 04-startup-control
reviewed: 2026-10-21T22:10:39Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - pagefolio.py
  - pagefolio/__init__.py
  - pagefolio/__main__.py
  - pagefolio/app.py
  - pagefolio/lang.py
  - pagefolio/startup_control.py
  - pagefolio/startup_win32.py
  - pagefolio/startup_focus.py
  - pagefolio/startup_notice.py
  - tests/test_gsd_dod.py
  - tests/test_startup_control.py
  - tests/test_startup_focus.py
  - tests/test_startup_notice.py
  - tests/test_startup_windows.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 4 コードレビュー

基準d274ef3からの変更14ファイルをstandard深度でインライン確認した。起動前遅延import、同一thread所有、IPC identity/期限/完了ACK、取消し寿命、UI状態維持、通知集約、試験隔離を確認。製品ソースを変更せず、再委任・コミットなし。

## Narrative Findings (AI reviewer)

現在の未解消指摘はWarning 1。旧Critical CR-01は04-06後の実コードと名前付き試験で独立再確認し、解消済みとした。後述の旧再現・旧観測は経緯と差分検証のため保持する。

## 解消済み Critical Issue の再確認

### CR-01: 起動判定基盤の初期化失敗が利用者向け案内を通らず例外終了する

**File:** `pagefolio/__main__.py:20`、`pagefolio/startup_win32.py:422`

**Issue:** Win32Backend構築で_token/権限descriptor等の初期化がOSErrorになると、StartupCoordinatorに代入される前に例外が伝播する。claim内のcheck_failed変換にもmainのshow_noticeにも到達せず、GUI起動では確認できる理由/次の操作がないまま終了する。SC3、V110-START-03、D-09の実装欠落。追加画面なし/有限終了だけでは通知契約を満たさない。

**再現:** `.venv/Scripts/python.exe -c "from pagefolio.__main__ import main; main(backend_factory=lambda: (_ for _ in ()).throw(OSError(5, 'injected backend initialization failure')))"`

**実結果:** exit1、__main__.py:20からOSError traceback。通知経路なし。状態や実OS資源を変更しない決定的注入で確認した。

**Fix:** backend未完成でも判定不能を機密情報なしの固定文言で案内できる独立した失敗境界へ接続し、作成済み資源の有限cleanupを保証する。constructorのtoken/descriptor失敗を注入し、編集画面0・案内1・非活性/有界終了と例外本文非表示を検証する名前付き回帰試験を追加する。既存claim失敗テストではこの経路を通らない。

**04-06後の独立判定: resolved.** `pagefolio/__main__.py:19-42`は`_tick_ms`・`Win32Backend()`・`StartupCoordinator`の構築OSErrorをTk import前に捕捉し、`show_startup_initialization_failure()`を1回呼ぶ。`startup_notice.py:77-101`は通知専用backendを構築し、成功時だけ`check_failed`、通知生成/表示/解放の失敗時は`notification_unavailable`を返す。`startup_win32.py:428-568`の基底分離と取得直後のdescriptor登録、逆順解放を確認。今回、constructor/初期化/期限の25件を実走し25 passed/102 deselected/1 warning/9.75秒、対象skipなし。`test_constructor_failure_real_main_nonactivate_notice`は実mainからnative窓へ到達し、編集画面0、案内1、前面HWND不変をassert。`test_constructor_failure_entry_exit`は両Python入口の通知不能exit1を検査する。旧注入exit1は修正前の事実であり、現在の指摘数には含めない。

## Warnings

### WR-01: 並行負荷で二次終了の15.5秒予算超過を観測

**File:** `pagefolio/startup_win32.py:287`、`pagefolio/startup_win32.py:307`、`pagefolio/startup_win32.py:819`

**Issue:** 絶対5秒期限と最大500ms取消し待ち、固定10秒通知は実装されているが、OSスケジューリングを含む実時間上限を一律に保証しない。04-05-EVIDENCE.jsonのW07b並行負荷は15609ms（109ms超過）、同じコードの単独測定15140ms。再測定だけで最初の超過を打ち消せない。有限終了は満たしており、既知の負荷条件での厳密予算適合性が残る。

**Fix:** Phase6で負荷条件と実時間計測範囲を明記して上限契約を再評価する。必要なら取消し/通知/終了の共通予算を実装し、同じ負荷条件で回帰を行う。元の超過値を保持する。2026-10-22承認済み06-UAT-CARRYOVERにこの再評価を明記済み。

## 検証と限界

本レビュー中の短い名前指定試験は47 passed（7件/0.15秒、21件/0.07秒、19件/0.13秒）、既存PyMuPDF警告のみ。加えてCR-01注入がexit1で欠落を再現した。親が直前に完了した全件1603 passed/209.19秒とvalidate-phaseの204 passed/190.22秒は再実行していない。Windows本番固定名/権限差の旧A証拠と新通知のW未実施を分離した。

04-06後は5変更ファイルの差分をstandard深度で再点検。新規25件を独立実走し、`git diff --check ff8b9355..cf5f354`成功、TBD/FIXME/XXX/TODO/空ハンドラ/裸except検索は該当0。全件1629 passed/1 warning/217.71秒は04-06-EVIDENCEの修正後記録を参照し、本レビューでは再実行しない。初期化時のOS資源解放自体が拒否された場合、当該processの有限終了で回収する範囲に限る。Phase6の実入力・実EXE受入は未実施のまま。

試験のskipifはWindows以外に限定され、対象Windowsでの無断skipなし。期待結果の自己生成・保存値比較による循環試験は見当たらない。実PDF回転/削除/4手Undo/RedoとOCR worker完了を値とidentityでassertしている。TBDはDoDの文法上のリテラル2件で、未解決の負債コメントではない。
