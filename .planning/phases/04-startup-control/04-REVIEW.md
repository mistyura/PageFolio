---
phase: 04-startup-control
reviewed: 2026-11-06T13:50:25Z
depth: standard
files_reviewed: 27
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
  - pagefolio/startup_wake.py
  - tests/test_gsd_dod.py
  - tests/test_startup_control.py
  - tests/test_startup_focus.py
  - tests/test_startup_notice.py
  - tests/test_startup_windows.py
  - tests/test_startup_wake.py
  - tests/startup_wake_child.py
  - tests/startup_foreground_audit.py
  - tests/test_startup_foreground_audit.py
  - tests/w05c_evidence.py
  - tests/w05c_runner.py
  - tests/test_w05c_evidence.py
  - tests/test_w05c_runner.py
  - .planning/phases/06-release-validation/06-05-w05c-v3.cjs
  - .planning/phases/06-release-validation/06-05-w05c-evidence.cjs
  - .planning/phases/06-release-validation/06-05-record-w05c-python.cjs
  - .planning/phases/06-release-validation/06-07-quality.cjs
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
  necessity: 0
status: issues_found
---

## 2026-11-06 constructor 通知 dedup 試験の独立差分再監査（現行判定）

新たな Critical / Warning は検出しなかった。`tests/test_startup_windows.py:471-516,2514-2529,2531-2565,2577-2589` の変更を、既存 lease 契約 `pagefolio/startup_win32.py:1399-1423,1455-1468,1893-1906` と `pagefolio/startup_notice.py:103-113` に照合した。7子を `constructor-join-ready` まで bootstrap してから owner の可視 `ready` を待ち、一斉に release する。子の実 `notice_call_tick` が同一 owner の `shown_tick <= call_tick < deadline_tick` に入り、result が `check_failed`、新規 notice 0、snapshot の deadline が owner と一致することを全7子に assert する。通常経路と legacy 経路の双方がこの条件を通る。遅延2.1秒は join-6 の呼出前 bootstrap にだけ入り、owner 表示寿命1800ms (`同:2551,2623-2625`) と製品の期限は変更されていない。`finally: _reclaim(children)` と `_finish` の失敗時診断・所有PID回収 (`同:188-210,999-1012`) を確認した。

`controlled-red-timeline.json` は旧順序の遅い子が元期限後981msに呼び出し、新規表示1回と別deadlineになったことを示す。`controlled-red.xml` は1件失敗、修正後 `controlled-green.xml` は遅延0/2.1秒×通常/legacyの4件、`constructor-others.xml` は周辺5件で failure/error/skip 0。今回の全件初回 `04-reverify-20261106-exe-closeout/` は2397 passed / 2 failed の不合格として保持し、成功へ読み替えない。`fix-input-scope.json` は失敗時から製品不変、変更は対象試験と開発履歴だけ、全体 Ruff check・149件format・AST成功を記録する。新しい単一全件は親が後続で実施予定であり、現行 Phase04独立verificationをpassedと再宣言しない。G3の正式受入30pass/78not-run/対象外2、`release_allowed=false`、CR-01/02 fixed、WR-01 deferred（15609ms/15140ms）を維持し、DEP-05・owner_missing・極端負荷下のNo無視の未解明事項を解除しない。レビューではGUI・pytestを再実行していない。根拠は `04-REVALIDATION-CONSTRUCTOR-20261106.md` と `.planning/debug/constructor-notice-dedup-20261106.md`。

## 2026-11-06 CR-02修正後の独立再監査（当時の判定）

**CR-02 は fixed。** `.planning/phases/06-release-validation/06-05-w05c-v3.cjs:56-58` の採用時刻検査と `.planning/phases/06-release-validation/06-05-record-w05c-python.cjs:25` の正式記録入口が、ともに `decision === '採用'` を要求することを再読した。正式 helper の `row.status = 'pass'`（同`:252`）へ否認値が到達しない。`tests/test_w05c_runner.py:353-389` は v2/v3 × 否認・未知7値 × dry-run/書込の28例で失敗理由の原文と全ファイル bytes 不変を確認し、既存の肯定採用例も維持する。旧再現 `04-cr02-red-20261106.xml` は v3 `不採用` が returncode 0 だったことを示し、修正後 `04-cr02-green-20261106.xml` は107件、failure/error/skip 0。Ruff check/format（148件変更不要）は親の実行結果を再利用した。今回のレビューでは pytest・GUI を再実行していない。

現行 frontmatter は未解消 Critical 0 / Warning 1 / Info 0。下記 CR-02 の旧指摘と修正根拠は履歴として残す。旧 CR-01 fixed、WR-01 deferred（並行15609ms・単独15140ms）は不変。新しい単一全件 `04-reverify-20261106-cr02/` は実行中であり、この時点で成功とは判定しない。人手 W05c/script・実EXE、Phase04の親検証、出荷判定へ自動試験結果を転用しない。

## 2026-11-06 試験時序修正と W05c 採用境界の再監査（修正前の記録）

既存19ファイルのレビュー履歴と WR-01 を保持し、今回の変更対象 `tests/test_startup_windows.py:2170-2262`、W05c 計測・採用の追加8ファイルを standard 深度で再点検した。製品 bytes は前回 v3 全件から不変（`04-REVALIDATION-20261106.md`）。native 確認窓は可視・親無効化済みの検出後に `focus-ready` を出し、非manual試験だけが popup 出現から30秒後または peer の結果後に閉鎖を試みる。manual 経路に自動 No はない。極端な過負荷で送信済み IDNO が無視される既知の未解明モードは、このレビューで解消と判定しない。

新規 BLOCKER 1件（CR-02）を確認した。機械採取の成功は人手受入に算入しない。再利用した単一全件原本は `04-reverify-20261106-native-fix/result.json` と JUnit で、2333 passed、failure/error/skip 0、170入力の前後・現在 hash 一致。`04-QUALITY-RESUME-20261106.json` の Ruff check exit 0、format 146件変更不要、AST exit 0、stderr 空を確認した。Phase04 名称付き299件成功は `04-REVALIDATION-20261106.md` の Nyquist 記録を参照し、本レビューでは pytest・GUI を再実行していない。CR-01 は fixed、WR-01 は並行15609ms・単独15140msのまま Phase06 W07b へ deferred。正式台帳28pass/80必須not-run/対象外2、`ready_for_retry=false`、`release_allowed=false` は維持する。

## 2026-11-05 W05c計測差分のコード再監査

`tests/test_startup_windows.py`のmanual native-quit限定接続と`tests/w05c_evidence.py`のcallback委譲・Tk timer書出し・事前snapshot・stop回収、`tests/test_w05c_evidence.py`の正負対照をstandard深度で確認した。製品の終了判断とUI処理は変更なし。計測欠落・元マーカー不成立・回収後発生を成功扱いにしない。新規Critical/Warning 0、既知Warning 1（WR-01）を維持する。現行2293件/JUnit failure/error/skip 0、対象39件pass、167入力一致。`04-REVALIDATION-W05C-20261105.md`参照。

## 2026-11-05 現行差分のコード再監査

前回からのPhase04 stale要因3試験を確認した。`tests/test_startup_windows.py` はnative通知監査接続、合成PDF/OCR・focus継続の自動ケースと証拠採取を追加。`tests/test_startup_wake.py` と `tests/startup_wake_child.py` は前景観測値を診断として残し、許容するOS境界をAPI要求で独立判定する。製品の `UiThreadWake` / `PostThreadMessageW` 接続は既存の実装範囲。`git diff --check` 成功、全件2254 passed、Phase04名前付き299件・skip0、118入力の前後hash一致。新規Critical/Warningを検出せず、Critical 0 / Warning 1 / Info 0を維持する。既知WR-01の15609ms/15140msはPhase06 W07bへのdeferredであり、今回の全件成功で解消としない。生証拠・限界は `04-REVALIDATION-20261105.md`。

# Phase 4 コードレビュー

基準d274ef3からの変更14ファイルをstandard深度でインライン確認した。起動前遅延import、同一thread所有、IPC identity/期限/完了ACK、取消し寿命、UI状態維持、通知集約、試験隔離を確認。製品ソースを変更せず、再委任・コミットなし。

## Narrative Findings (AI reviewer)

#### CR-02: 否認した採用判断でも W05c を正式 pass にできる（修正済み履歴）

**Classification:** BLOCKER
**File:** `.planning/phases/06-release-validation/06-05-w05c-v3.cjs:54`、`.planning/phases/06-release-validation/06-05-record-w05c-python.cjs:25`、同`:252`
**Issue:** v3 の `adoption()` は `answer.adoption.decision` の真偽値だけを検査する。正式 helper も同じ条件で通過し、`row.status = 'pass'` に進む。テスト fixture は `"採用"` を使用する（`tests/test_w05c_evidence.py:352`）が、否認を表す `"不採用"` や任意の非空文字列でも両条件は真になる。回答と機械原本が整っていても、採用しないという判断を必須 UAT 行の pass に反転できる。`tests/test_w05c_runner.py:386-406` の拒否ケースには否認 decision がない。
**Fix:** v3 validator と正式 helper の両方で許可された採用値（現行 fixture 契約なら `decision === '採用'`）を厳密比較し、`"不採用"`・未知値を与えた dry-run が台帳に書かず失敗する回帰試験を追加する。人手の実回答・意味承認を自動試験で代用しない。

**修正後の独立判定:** fixed。現行ソース位置と負対照の根拠は冒頭の「CR-02修正後の独立再監査」に記録した。修正前の Issue は履歴として保持する。

### 2026-10-28 品質停止解除後のstandard再監査（当時の記録）

既存17ファイルに `tests/startup_foreground_audit.py` / `tests/test_startup_foreground_audit.py` を加えた19ファイルが対象。旧118入力のhash比較により製品と既存試験のうち変更されたのは `tests/test_startup_windows.py` だけと確認した。同ファイルの差分全体、監査helper/故障注入試験、実OS接続とowner＋8 peerへの配線を読解した。既存対象17ファイルのうち不変部分は前回standardレビューを再利用する。

監査はbackend構築前に開始し、子ごとの一時fixtureへ記録、context終了で `_bind` を復元する。wrapperは引数・戻り値・例外・last-errorを保持し、監査採取不能を独立して記録する。判定は9processのPID/生成時刻/role、必須APIの呼出/復帰対応、NOACTIVATE flags、禁止API要求（OS拒否時を含む）、一時的前景化、未知切替、hook解除/証拠不足を検査し、未知切替もpassにしない。故障注入は旧before/after同値でも途中の前景化を検出し、原証拠は変更しない。元設定/プロンプト隔離・所有Popen限定回収は維持する。

現行Python137/137と環境を照合し、最新単一全件2071 passed / 2 warnings / 480.86秒、failed/ERROR/skip 0、exit 0と実接続/9process各1件を再利用した。CRLF対応 `git diff --check` は対象差分でexit 0。新規Critical/Warningを検出せず、現行Critical 0 / Warning 1を維持する。CR-01 fixed、WR-01 deferred（15609ms/15140ms）を変更しない。旧全件/過去失敗は履歴であり、今回の成功や原因解決へ読み替えない。詳細は `04-GATES-CURRENT-20261028.md` / `.json` を参照。

### 前回の17ファイル再監査（履歴）

2026-10-28の再監査では、既存14ファイルに新規 `pagefolio/startup_wake.py`、`tests/test_startup_wake.py`、`tests/startup_wake_child.py` を加え、合計17ファイルをstandard深度で確認した。`__main__.py` のTk初期化後開始・root破棄前停止、Win32の `PostThreadMessageW` binding、自スレッド宛 `WM_NULL` のみの120ms周期、失敗時の再試行とログ抑制、試験の禁止API/別宛先/別種別の負対照を読解した。`git diff --check` と裸 `except:` / `# type: ignore` / TODO 等の検索に新規指摘はない。同一118入力のnative全件2047 passed / 1 warning / 427.01秒（`.planning/debug/startup-wake-foreground-evidence/full-native-after-state/{run.json,pytest.txt}`）を再利用し、再走していない。

初回原本で前景値が変化した発生原因は未確定。今回の試験は外部変化の模擬で旧判定の偽陽性を再現し、製品の禁止副作用を独立した境界で検査する。現行の新たなCritical/Warningは検出せず、既存WR-01の並行負荷15609msと単独15140msは未解消のまま `06-UAT-CARRYOVER.md` に従ってdeferredを維持する。過去のCR-01見出しは履歴であり、現行frontmatterの未解消件数には含めない。

2026-10-28時点の未解消指摘はWarning 1。旧Critical CR-01は04-06後の実コードと名前付き試験で独立再確認し、解消済みとした。後述の旧再現・旧観測は経緯と差分検証のため保持する。

## 解消済み Critical Issue の再確認

#### CR-01: 起動判定基盤の初期化失敗が利用者向け案内を通らず例外終了する

**File:** `pagefolio/__main__.py:20`、`pagefolio/startup_win32.py:422`

**Issue:** Win32Backend構築で_token/権限descriptor等の初期化がOSErrorになると、StartupCoordinatorに代入される前に例外が伝播する。claim内のcheck_failed変換にもmainのshow_noticeにも到達せず、GUI起動では確認できる理由/次の操作がないまま終了する。SC3、V110-START-03、D-09の実装欠落。追加画面なし/有限終了だけでは通知契約を満たさない。

**再現:** `.venv/Scripts/python.exe -c "from pagefolio.__main__ import main; main(backend_factory=lambda: (_ for _ in ()).throw(OSError(5, 'injected backend initialization failure')))"`

**実結果:** exit1、__main__.py:20からOSError traceback。通知経路なし。状態や実OS資源を変更しない決定的注入で確認した。

**Fix:** backend未完成でも判定不能を機密情報なしの固定文言で案内できる独立した失敗境界へ接続し、作成済み資源の有限cleanupを保証する。constructorのtoken/descriptor失敗を注入し、編集画面0・案内1・非活性/有界終了と例外本文非表示を検証する名前付き回帰試験を追加する。既存claim失敗テストではこの経路を通らない。

**04-06後の独立判定: resolved.** `pagefolio/__main__.py:19-42`は`_tick_ms`・`Win32Backend()`・`StartupCoordinator`の構築OSErrorをTk import前に捕捉し、`show_startup_initialization_failure()`を1回呼ぶ。`startup_notice.py:77-101`は通知専用backendを構築し、成功時だけ`check_failed`、通知生成/表示/解放の失敗時は`notification_unavailable`を返す。`startup_win32.py:428-568`の基底分離と取得直後のdescriptor登録、逆順解放を確認。今回、constructor/初期化/期限の25件を実走し25 passed/102 deselected/1 warning/9.75秒、対象skipなし。`test_constructor_failure_real_main_nonactivate_notice`は実mainからnative窓へ到達し、編集画面0、案内1、前面HWND不変をassert。`test_constructor_failure_entry_exit`は両Python入口の通知不能exit1を検査する。旧注入exit1は修正前の事実であり、現在の指摘数には含めない。

## Warnings

### WR-01: 並行負荷で二次終了の15.5秒予算超過を観測

**Classification:** WARNING
**File:** `pagefolio/startup_win32.py:287`、`pagefolio/startup_win32.py:307`、`pagefolio/startup_win32.py:819`

**Issue:** 絶対5秒期限と最大500ms取消し待ち、固定10秒通知は実装されているが、OSスケジューリングを含む実時間上限を一律に保証しない。04-05-EVIDENCE.jsonのW07b並行負荷は15609ms（109ms超過）、同じコードの単独測定15140ms。再測定だけで最初の超過を打ち消せない。有限終了は満たしており、既知の負荷条件での厳密予算適合性が残る。

**Fix:** Phase6で負荷条件と実時間計測範囲を明記して上限契約を再評価する。必要なら取消し/通知/終了の共通予算を実装し、同じ負荷条件で回帰を行う。元の超過値を保持する。2026-10-22承認済み06-UAT-CARRYOVERにこの再評価を明記済み。

## 検証と限界

本レビュー中の短い名前指定試験は47 passed（7件/0.15秒、21件/0.07秒、19件/0.13秒）、既存PyMuPDF警告のみ。加えてCR-01注入がexit1で欠落を再現した。親が直前に完了した全件1603 passed/209.19秒とvalidate-phaseの204 passed/190.22秒は再実行していない。Windows本番固定名/権限差の旧A証拠と新通知のW未実施を分離した。

04-06後は5変更ファイルの差分をstandard深度で再点検。新規25件を独立実走し、`git diff --check ff8b9355..cf5f354`成功、TBD/FIXME/XXX/TODO/空ハンドラ/裸except検索は該当0。全件1629 passed/1 warning/217.71秒は04-06-EVIDENCEの修正後記録を参照し、本レビューでは再実行しない。初期化時のOS資源解放自体が拒否された場合、当該processの有限終了で回収する範囲に限る。Phase6の実入力・実EXE受入は未実施のまま。

試験のskipifはWindows以外に限定され、対象Windowsでの無断skipなし。期待結果の自己生成・保存値比較による循環試験は見当たらない。実PDF回転/削除/4手Undo/RedoとOCR worker完了を値とidentityでassertしている。TBDはDoDの文法上のリテラル2件で、未解決の負債コメントではない。
