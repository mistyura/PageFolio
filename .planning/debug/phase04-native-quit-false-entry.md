---
status: resolved
trigger: "Phase04 native-quit-False-entry-module"
created: 2026-11-05
updated: 2026-11-05
---

# Debug: Phase04 native-quit-False-entry-module

## Symptoms

- expected: `tests/test_startup_windows.py::test_focus_restore_real_main_windows[native-quit-False-entry-module]` passes — the foreground target is the owned native confirmation window (askyesno from `app._quit()`), so `measured["target_correct"]` is True.
- actual: In the 2026-11-05 single-process full suite (`04-reverify-20261105-w05c2-full/`, 1 failed / 2332 passed), the test failed at `tests/test_startup_windows.py:1664` `assert measured["target_correct"]`. `focus-result.json`: `result: foreground_denied`, `activated: 5641316` == `expected_tk: 5641316`, `native: null`, `state_preserved: true`, `focus_correct: true`, 3 pages / [90,90,0]. Peer: `constructed 0` / `restored 0` / `foreground_denied` / 78ms. The native judgement is `actual not in {None, expected} and native == actual`, so it is False.
- errors: AssertionError only (not symptom ① TclError/ERROR). stderr empty.
- timeline: First observed in the full run after W05c v3 test-side input changes (uncommitted changes to `tests/test_startup_windows.py`, `tests/w05c_evidence.py`, new `tests/w05c_runner.py`, `tests/test_w05c_runner.py`). Product code (`pagefolio/`, `pagefolio.py`) unchanged across the 167 inputs. No earlier record of this failure in `.planning`.
- reproduction: Seen once in full-suite run. Isolated file run (`04-reverify-20261105-w05c2-isolate-file/`) = 88 passed (not reproduced). This is an automatic native-quit control (manual=False, no `w05c-observe`), so the W05c observer is NOT installed.

## Context / Evidence locations

- Summary: `.planning/phases/04-startup-control/04-REVALIDATION-W05C-20261105-2.md`
- Preserved owner fixture: `.planning/phases/04-startup-control/04-reverify-20261105-w05c2-full/failed-fixture-native-quit-False-entry-module/`
- Full-run raw: `.planning/phases/04-startup-control/04-reverify-20261105-w05c2-full/` (junit.xml, stdout.txt)
- Previous green full run: `.planning/phases/06-release-validation/06-05-evidence/w05c-instrumentation-native-20261105/`

## Constraints

- Release gate (CLAUDE.md): green only via single-process full suite; never skip/exclude/delete tests or treat a rerun as passing.
- Do not edit `pyproject.toml`. Do not decide product-vs-test defect without evidence. Ask user before applying any fix.
- Initial (unproven) hypothesis from the revalidation note: `focus-ready` is emitted before `pdf()` / `app._quit()` show the askyesno, so the peer's foreground request can be processed before the confirmation window exists (race).

## Current Focus

- hypothesis (CONFIRMED): 試験 owner が `focus-ready` を発行してから `app._quit()` の native 確認窓が「可視・親無効化済み」になるまでに時間差があり、peer の前面化要求がその間（`tk_messageBox` 内部の pump が窓生成より先に走る区間）に処理されると、`_owned_popup()` が None になり Tk 本体が前面化対象になる（試験側の時序競合）
- test: 計装 owner + 注入 + 自然発生 + 実テスト反復 + 負荷（Evidence 参照）
- expecting/result: 注入で署名を決定論的に再現、無注入でも自然再現、修正模擬（popup 可視後に focus-ready）で解消
- next_action: なし（利用者承認「今すぐ修正」により試験側の修正を適用・検証済み。未コミット。コミットは別途利用者判断）
- bug_class: 機構は決定的（Bohrbug 的）だが発現は時刻競合（確率的・負荷依存）。SBFL は不適用（単一失敗・per-test coverage 無し）
- candidate_causes (RCA branching): [code(test): 準備完了の合図 focus-ready が前提条件(native 窓の存在)の成立前に出る] / [environment: Tcl/Tk 9.0.4 Windows の tk_messageBox が窓生成前に Tcl タイマーを処理する] / [environment: 負荷による窓生成遅延と peer 到達(最早 +0.43s)の重なり]
- and_gate: yes。3 条件の同時成立が必要（どれか1つ欠ければ失敗しない）。ただし是正可能なのは試験側の合図位置のみ。

## Evidence

- timestamp: 2026-11-05
  checked: 失敗時 owner fixture の原本タイムスタンプ（コピー前の basetemp `%LOCALAPPDATA%\Temp\pf04-04-reverify-20261105-w05c2-full\test_focus_restore_real_main_w11`）
  found: 18:57:25.407 owner 起動 / 26.129 initializing.json / 32.205 ready / 32.639 focus-ready / 32.651 peer fixture 作成(+12ms) / 33.324 peer traceback.log / 33.494 owner focus-result.json / 33.497 peer resource-audit.json。focus-ready→focus-result = 0.855s。`quit-cancelled` と `stop` は無い。
  implication: restore は focus-ready の約0.85s後、`app._quit()` が未復帰の状態（`quit-cancelled` が無い）で走った。5秒の close_native 期限による自動閉鎖（popup は既に閉じていた）説は、時間差（0.85s≪5s）と quit-cancelled 不在の両面から否定。

- timestamp: 2026-11-05
  checked: 同一全件ランの兄弟 fixture 30個の同種タイムライン（focus-ready→peer起動→focus-result）
  found: focus-ready→focus-result は 0.39〜0.95s。失敗 param の 0.855s は兄弟の範囲内（native-quit-entry-script は 0.685s で成功、popup 検出→0.048s 後に quit-cancelled）。
  implication: 失敗 run 全体が異常に遅かったわけではない。peer の到達時刻は通常範囲で、owner 側の「窓が出るまで」が相対的に遅かったか、余裕が元々小さい。

- timestamp: 2026-11-05
  checked: `tests/test_startup_windows.py` の native-quit 経路（ready() 2170-2238 行, after() 1962-, Backend._foreground_window 3037-3047）と startup_focus.py の restore()/_owned_popup
  found: ready() は `focus-ready` を touch（2185行）→ `root.after(30, close_native)` → `pdf()` → `app._quit()`（2213-2214行、ここで tk_messageBox が同期ブロック）の順。harness は `focus-ready` だけを待って peer を起動する（1655行）。`native` は `_foreground_window` 呼出し時点の `_owned_popup()` 結果で、判定は `actual not in {None, expected} and native == actual`（1968行）。窓が無ければ `selected = popup or target_hwnd` = Tk 本体になり必ず False。
  implication: 試験は「popup が存在する」ことを待たずに peer を起動する。popup の存在は restore 時点の偶然に依存する。

- timestamp: 2026-11-05
  checked: 試験側の未コミット差分が native-quit 経路に及ぶか（`git show HEAD:tests/test_startup_windows.py` と現行の ready()/after()/_foreground_window/_prepare_focus_case の比較）
  found: native-quit の順序（focus-ready touch → pdf() → _quit()）、close_native、after()、_foreground_window は HEAD と同一。差分は manual 分岐・W05c observer の条件付き install（w05c-observe ファイルがあるときのみ。本件では未設置）・manual_ocr 分岐のみで、native-quit 非 manual には影響しない。製品コードは変更なし。
  implication: 時序の競合は未コミット差分で導入されたものではなく、HEAD から存在する潜在的な競合。「W05c v3 の入力変更が原因」という仮説は支持されない（ただし負荷等で顕在化する確率は別問題）。

- timestamp: 2026-11-05
  checked: 計装 owner（probe_owner.py: askyesno / FocusRestorer.restore / _owned_popup / UI スレッドの top-level 窓集合を1ms周期で記録）で、無注入の1回
  found: focus-ready +0ms → pdf() 約290ms で終了 → askyesno_enter +308ms → TclNotifier 窓が +312ms に生成 → 親(TkTopLevel)が無効化 +448ms → `#32770`(MessageBox) 窓生成 +455ms(不可視) → 可視 +475ms → restore_enter +586ms（popup 検出 5/5、foreground_denied）→ 窓閉鎖 → quit-cancelled。
  implication: 正常時でも「askyesno 入口から可視窓まで約165ms」の窓生成前区間があり、focus-ready からは約0.47s後にようやく検出可能になる。

- timestamp: 2026-11-05
  checked: 同計装で pdf() 末尾に UI スレッド多忙(time.sleep、非pump)1000ms を注入して peer 要求を pending のまま askyesno に入らせる
  found: askyesno_enter +1120ms → restore_enter +1143ms（23ms後）。その時点の UI スレッド窓集合に `#32770` は無く TkTopLevel は有効。`_owned_popup` は5回とも None、`foreground_denied`。MessageBox 窓は +1400ms 頃に生成された。生成された focus-result.json は失敗 fixture と同一の形（`native: null`, `activated == expected_tk`, `result: foreground_denied`, `page_rotations [90,90,0]`, `current_page 1`, `selected_pages []`, `focus_correct true`, `settled_focus "."`, `target_correct false`）。restore の呼出し stack は `ready → _quit → askyesno → commondialog.show → Tk.call → callit → StartupCoordinator._poll → _dispatch_pending → restore_window → FocusRestorer.restore`。
  implication: 失敗の署名を決定論的に再現。restore は `tk_messageBox` 内部の pump（Tcl_ServiceAll 経路）から窓生成前に実行される。「窓は在るが検出できなかった」のではなく「窓がまだ存在しなかった」。

- timestamp: 2026-11-05
  checked: pdf() 先頭に1200ms 注入（要求が pending のまま pdf() チェーン全体を実行）
  found: 要求の最初の到達は focus-ready +431ms。pdf() チェーン(_rotate/_duplicate/_delete/_refresh_all x3 = 1210〜1347ms)の間に restore_enter は発生せず、askyesno_enter(+1350ms)の10ms後に初めて restore が走り、窓は未生成で `native: null` になった。
  implication: pdf()/_refresh_all 内に Tk イベント pump は無い（仮説「pdf() 中に処理される」は否定）。pump が起きるのは askyesno（tk_messageBox）に入ってから。ゆえに窓生成前区間 = `[askyesno 入口, MessageBox 窓が可視化]` が競合の脆弱区間。peer 要求の最早到達は focus-ready +0.43s で、無負荷の窓可視化(+0.47s)と重なりうる。

- timestamp: 2026-11-05
  checked: 無注入・計装 owner で自然発生（watcher 付き 23 回: base25 11回 + probe2 12回）
  found: 2/23 回が失敗（base25/run010, probe2/run009）。いずれも restore_enter 時点の UI スレッド窓集合に `#32770` が無く（TkTopLevel は有効のまま）、`_owned_popup` は None。popup はその 60〜120ms 後に出現して検出された。restore の stack は `askyesno → commondialog.show → Tk.call → callit → _poll → _dispatch_pending → restore_window → restore`。成功 21 回の ms（focus-ready 起点）: pdf() 終了 中央値122（97〜202）/ askyesno 入口 中央値125 / MessageBox 窓生成 中央値331（254〜**1214**）/ 可視 中央値345 / peer 最初の要求到達 中央値501（最小430）。窓可視〜要求到達の余裕は 3ms〜250ms（3ms, 18ms, 55ms の薄氷が複数）。
  implication: 余裕が数十msの薄氷運用で、窓生成が遅い尾（本件では tk_messageBox の窓生成前に 0.5〜1.1s かかる回）が要求到達に追い越されると失敗する。窓生成遅延は pdf() とは無関係（pdf() は 100〜200ms で安定）。

- timestamp: 2026-11-05
  checked: 実テスト（試験コード無改変）`test_focus_restore_real_main_windows[native-quit-False-entry-module]` の反復（一意 basetemp `%LOCALAPPDATA%\Temp\pf_pytest_tmp_dbg1_<tag>_<n>`）
  found: (a) 20:03〜20:05 の外因的に高負荷だった時間帯: 17 回中 **9 回が同一署名で失敗**（foreground_denied / activated==expected_tk / native null / quit-cancelled 無し / focus-ready→result 0.59〜1.36s）、**8 回が別モードの `connection_failed`**（peer が `accepted` 後に終端応答を得られず終了、owner は focus-result.json 無し）、PASS 1 回。(b) 負荷が落ち着いた後の無負荷 8 回: 8/8 PASS。(c) 意図的に CPU 負荷（python 空回し24本/16論理CPU）を掛けた 8 回: 6 PASS、1 回が同一署名で失敗、1 回が `connection_failed`。(d) 同条件の native-ocr-False-entry-module 8 回: 8/8 PASS。
  implication: 実テストでも負荷依存で同一署名が再現する（確率は環境負荷で 0〜50%超まで変動）。2332 件フルスイート中の 1 失敗はこの確率的競合と整合する。`connection_failed` は同じ前提（owner の UI スレッドが tk_messageBox 内で窓生成前に長時間停止）が peer の 5 秒期限を超えた別の発現形と推定（owner 側 focus-result.json が無いことのみ確認。個別の根本調査はしていない）。native-ocr は同構造だが pdf() が無く露出が小さい（観測上は未発現）。

- timestamp: 2026-11-05
  checked: 修正案の模擬（owner 計装内で `focus-ready` の touch を差し替え、`_owned_popup([root])` が非 None になってから touch。製品・試験ファイルは未変更）
  found: 注入（pdf() 後に UI スレッド 1000ms 停止）で 対照（模擬なし）3/3 失敗 → 模擬あり 3/3 成功。CPU 負荷 24 本下で 模擬なし 10 回中 1 失敗 → 模擬あり 14 回中 0 失敗。
  implication: 「popup が可視・親無効化されてから focus-ready を出す」で競合は消える。peer は popup 存在後にしか起動しないため、`connection_failed` 型（窓生成停止が peer の期限を食う型）も同時に回避できる見込み。

- timestamp: 2026-11-05
  checked: 修正適用後（popup 検出後に focus-ready、自動閉鎖期限は 5 秒を popup 出現起点に付け替え）の CPU 負荷 24 本下の反復（20:31〜20:44 の外因的に重い時間帯）
  found: native-quit-False-entry-module 10 回中 7 回失敗、うち 6 回を精査すると全て `focus-ready→quit-cancelled = 5.02〜5.03s`（自動閉鎖が 5 秒で popup を閉じた後に peer の復帰要求が `focus-ready +5.08〜7.07s` で到達し `native: null`）。peer の起動〜要求が負荷で 5〜7 秒かかり、5 秒の自動閉鎖期限を超えた。原因は元の競合（窓生成前）ではなく、HEAD から存在する 5 秒期限が高負荷の peer 遅延より短いこと。
  implication: 修正案どおり「5 秒を popup 出現起点に付け替え」だけでは高負荷で不十分。自動閉鎖期限は peer の到達待ち（試験側の待機 `_BOOTSTRAP_TIMEOUT`=30 秒）以上にする必要がある。適用: `deadline = popup 出現時刻 + _BOOTSTRAP_TIMEOUT`（承認範囲の試験側時序修正の延長。製品コード不変）。

- timestamp: 2026-11-05
  checked: 期限を 30 秒にした後の同負荷反復（24 本・12 回）と計装追加の再現調査
  found: 12 回中 9 PASS / 3 FAIL。3 件とも別モードで `quit-cancelled` が 30 秒以内に出ない（restore 自体は成功し `target_correct=true`・`native==activated`）。いずれも `focus-ready→focus-result = 8.3〜10.9s`（極端な遅延 peer）。計装（一時・撤去済み）で `close_native` は `focus-result.json` 検知直後に popup（restore で記録した native と同一 HWND）へ `PostMessageW(WM_COMMAND, IDNO)` を送り戻り値 1（成功）だが、MessageBox が閉じない（主スレッドは askyesno 内に留まる）ことを確認。無負荷で peer を 8 秒・11 秒遅らせた人為再現では閉じる（再現せず）。その後 24〜32 本の再実測（計 70 回弱）は、外部負荷が下がり再現せず（失敗は全て owner 起動が 30 秒枠に収まらない `focus-ready` 待機切れのみ）。
  implication: 「peer が 8 秒超遅れる極端な過負荷」下でのみ現れる未解明の残存モード（送信済み WM_COMMAND が MessageBox に無視される）。元の競合・今回の修正とは独立で、通常負荷（peer が 5 秒未満）では発現しない。原因は未特定（Windows 側挙動の可能性）。再発した場合は `close_native` の再送（bounded retry）や当該 HWND の状態採取を検討。

## Eliminated

- hypothesis: 失敗は close_native の5秒期限で popup が先に閉じられた後に restore が走ったため
  evidence: focus-ready→focus-result が 0.855s（≪5s）、quit-cancelled が無い（popup が閉じれば `_quit` は復帰し即 touch される）。
  timestamp: 2026-11-05

- hypothesis: popup は在ったが `_owned_popup` が検出し損ねた（検出ロジックの欠陥）
  evidence: 再現 run の restore_enter 時点の窓集合に `#32770` が存在しない（窓が未生成）。窓が存在する通常 run では 5/5 回検出。製品の `_owned_popup` 条件（可視・有効・親無効）自体は正しく働いている。ただし「窓生成の途中（不可視〜親無効化の約27ms）」に restore が重なる亜種は同根の競合として含まれる。
  timestamp: 2026-11-05

- hypothesis: pdf()/_refresh_all 内で Tk イベントが pump され restore が先に走った
  evidence: pdf() 先頭注入の run で、要求が pending のままチェーン全体(約140ms)を実行しても restore_enter は askyesno_enter 以前に発生しない。
  timestamp: 2026-11-05

- hypothesis: 未コミットの試験側変更（W05c v3 入力）が競合を導入した
  evidence: native-quit 非 manual の ready()/after()/_foreground_window は HEAD と同一。W05c observer は `w05c-observe` ファイルが無いため install されない。
  timestamp: 2026-11-05

## Resolution

- root_cause: 試験 owner（tests/test_startup_windows.py の `_prepare_focus_case.ready()`）が「native 確認窓が可視・親無効化済みになった」ことを待たずに `focus-ready` を発行する（2185行）。harness は `focus-ready` だけを待って peer を起動する（1655-1656行）。native-quit では `focus-ready` の直後に `pdf()` → `app._quit()`（2213-2214行、tk_messageBox は同期ブロック）が走り、窓が可視になるのは中央値 +345ms（尾は +0.5〜1.2s）。一方 peer の最初の要求は最早 +430ms（中央値 +501ms）で到達する。要求が窓可視より先に到達すると、Tcl/Tk 9.0.4 の tk_messageBox が MessageBox 窓の生成前に Tcl タイマー（Notifier 窓の WM_TIMER → Tcl_ServiceAll）を処理するため、`StartupCoordinator._poll → restore_window` が窓の無い状態で走る。`_owned_popup()` は None となり `selected = popup or target_hwnd` が Tk 本体になるため、`Backend._foreground_window` が `activated=expected_tk, native=None` を記録し、判定 `actual not in {None, expected} and native == actual` が False になる。`foreground_denied` は無関係（通常 run でも同じ結果）。AND ゲート: [試験の合図位置] ∧ [tk_messageBox の窓生成前 pump] ∧ [負荷等による窓生成遅延と peer 到達の重なり]。分類: **試験側の時序欠陥**（製品欠陥は証拠上なし）。潜在的には HEAD から存在し、未コミットの W05c v3 入力変更が導入したものではない。確度: 高（決定論的注入で署名一致を再現、無注入の自然再現 2/23、実テスト無改変でも負荷下再現、修正模擬で解消）。
- fix: 適用済み（試験側のみ・製品コード不変）。`tests/test_startup_windows.py` の `_prepare_focus_case.ready()`: (1) 非 native は従来どおり即 `focus-ready`。native-*（quit / ocr、manual 有無とも）は blocking 呼出し（`pdf()`+`app._quit()` / `showinfo` / `_on_close()`）の前に `root.after(5, announce_native)` のポーリングを仕掛け、`backend._owned_popup([backend._top_level_hwnd(state["target"])])`（restore と同じ述語＝可視・親無効化済み）が非 None になった時点で初めて `focus-ready` を touch する。ポーリングは 20 秒の有界期限を持ち、超過時は AssertionError（harness は 30 秒で『focus-ready を確認できない』と明示失敗）。 (2) `close_native` を `close_native(deadline)` 引数化し、自動閉鎖の期限を popup 出現時刻 + `_BOOTSTRAP_TIMEOUT`(30 秒) に付け替え（元は ready() 起点 5 秒）。5 秒のままだと高負荷で peer の要求到達前に popup が閉じて失敗するため、orchestrator 指示の『5 秒の起点付け替え』より長くした（Evidence 参照・要レビュー）。manual は従来どおり自動閉鎖なし。
- verification: ruff check / format --check 全通過（他ファイル変更なし）。 負荷 24 本の反復（最終構成・外部負荷が下がった時間帯）: native-quit-False-entry-module 12/12、native-quit-False-entry-script 10/10、native-ocr-False-entry-module 8/8、native-ocr-False-entry-script 8/8 PASS（計 38/38、`connection_failed` 0 件）。 無負荷スモーク: `-k native`（native-ocr/quit x entry x manual 含む 6 件）6 passed を 2 回。 `tests/test_startup_windows.py` 単体 88 passed (334s)。 単一プロセス全件 `pytest -q --basetemp=%LOCALAPPDATA%\Temp\pf_pytest_tmp_fix_full`: 2333 passed、failed 0 / ERROR 0 / クラッシュなし（655.91s）。症状①TclError は不観測。 注意: 20:31〜20:44 の外因的に重い時間帯では 5 秒期限版が 7/10 失敗、30 秒期限版が 12 回中 3 失敗（peer が 8 秒超遅れる極端な過負荷で、送信済み IDNO を MessageBox が無視する未解明モード）。この極端領域は未解決の残存リスクとして記録。 負荷 28〜32 本ではowner 起動が harness の 30 秒枠を超えて `focus-ready` 待機切れになる別の負荷由来失敗もあった（本件と無関係・元から存在）。
- files_changed: [tests/test_startup_windows.py]（`ready()` の native-* 部分のみ。未コミット）。調査用の計装は scratchpad のみ（probe_*.py / stress_*.sh / test_late_peer.py / run_loaded_bg.sh 等）で、一時計装（TEMPDBG）は本番ファイルから撤去済み（`grep TEMPDBG` = 0）。失敗 run の basetemp は `%LOCALAPPDATA%\Temp\pf_pytest_tmp_dbg1_*` に残置。
