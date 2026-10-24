---
status: resolved
trigger: "06-04 Task2前の検証ツール修正(tests/release_uat_support.py X03 lockバグ修正、未commit)のcommit前単一プロセス全件pytestで 1973 passed, 3 warnings / exit 0。うち2件が tests/test_ocr.py::TestRunParallelBackoff::test_always_retryable_errors_after_max_retries で RuntimeWarning: the Tcl interpreter is leaked because it was deallocated in a thread other than the one it was created in (gh-83274) と PytestUnraisableExceptionWarning(Variable.__del__ → RuntimeError: main thread is not in main loop)。06-VALIDATIONの停止条件『Tcl警告の同種再発』に該当し停止。"
created: 2026-10-24
updated: 2026-10-24
---

# Debug: tcl-leak-test-ocr

## Symptoms

- **期待:** 単一プロセス全件 pytest が失敗0・ERROR0・クラッシュなしで、警告は既存の PyMuPDF `ByteString` DeprecationWarning 1件のみ（直前 3e56452 時点の全件は `1970 passed, 1 warning`）。
- **実際:** `1973 passed, 3 warnings in 431.25s (0:07:11)` / exit 0。追加の2警告が `tests/test_ocr.py::TestRunParallelBackoff::test_always_retryable_errors_after_max_retries` に帰属:
  - `RuntimeWarning: the Tcl interpreter is leaked because it was deallocated in a thread other than the one it was created in (see gh-83274)`
  - `PytestUnraisableExceptionWarning`（`Variable.__del__` → `RuntimeError: main thread is not in main loop`）
- **エラー:** 上記警告のみ。テスト失敗・ERRORは無し。
- **時期:** 2026-10-24 17:45〜17:52 の全件で観測。直前の全件（3e56452、1970 passed / 1 warning）では出ていない。同系警告は 06-01 で `config-notice-tk-lifecycle`（resolved）として、設定通知テストの `TkinterDnD.Tk()` 間欠失敗で破棄されない Tk root が後続 `test_ocr_engine.py` のスレッド GC で回収された事例として解決済み。今回は帰属テストも事情も異なる可能性がある。
- **再現:** 単一プロセス全件 pytest。単体再現は未確認。差分は未commitの `tests/release_uat_support.py`（`walk_tree` に locked_ok/locked 引数、宣言済み overlay の lock 中は `locked_unverified` 記録）と `tests/test_release_uat_support.py`（`TestLockedOverlayVerification` 3件）。これらは Tk を使わないとされるが無関係とは断定していない。

## 証拠（原本保持・変更削除禁止）

- 全件ログ: `.planning/phases/06-release-validation/06-04-fixgate-full-tcl-warning.txt`（untracked、sha256 `9fd3c23c67918d3365945fb28e9071826f4b6d7b29c58035fd080b2bdeef0369`）
- basetemp: `C:\Users\shdwf\AppData\Local\Temp\pf06_04_fix_full_1792831546`
- 先行事例: `.planning/debug/resolved/config-notice-tk-lifecycle.md`、`06-01-STOP.md`、`06-01-task1-full.txt`

## 制約

- 再実行で警告が消えても合格扱いにしない。原因（leak した Tk/Variable がどのテストで生成され、なぜ非メインスレッドで GC されたか）を特定する。
- 期限延長・skip・除外・警告フィルタ追加で通さない。製品コードの変更が必要なら適用前に利用者確認。
- 06-04 の build 出力 `C:\Users\shdwf\AppData\Local\Temp\pf06_final_2f67e363e4ca4304b1ea6a9a11431358\` は削除・変更しない。
- 未commitの検証ツール修正（tests/release_uat_support.py、tests/test_release_uat_support.py）は保持する（撤回しない）。commit は本調査の結論と全件ゲート合格後。
- 既存 dirty（.planning/STATE.md、config.json、state.json、debug/dep-05-regression.md、debug/simultaneous-owner-missing.md、05-CONTEXT.md、requirements.txt、開発履歴.md）は stage/commit しない。
- `ruff format` は Python ファイルに限定する（ruff 0.17.1 は Markdown 内コードブロックも整形するため）。テキスト書込みは quoted heredoc か Write ツールを使う。
- pyproject.toml を編集しない。

## Current Focus

bug_class: Mandelbug（GC発火スレッド依存・アロケーション列依存。Bohrbugではない。SBFLは適用しない＝flakyスペクトルは順位を汚染するため）
hypothesis: CONFIRMED（機構まで実証）。先行テスト（tests/test_config_notification.py の実Tkテスト群、tests/test_batch_ocr_dialog.py の Variable）がテスト終了時に循環ガベージ（Tk root + Variable）を残し、後で循環GCが回収する。その回収がたまたま run_parallel の ThreadPoolExecutor ワーカースレッド内で起きると Tk がメイン生成と別スレッドで解放され、Tcl leak 警告と Variable.__del__ の RuntimeError になる。
test: (済) 寿命プローブ・決定的機構再現・修正模擬(各テストteardown後のメインスレッド gc.collect())の部分実行/全件2本 -> 案A適用後の実リポジトリ conftest による単一プロセス全件
expecting: 修正模擬で全Tk/Variableがメインスレッドで解放され警告0件 -> 達成（模擬: 1973 passed, 1 warning / 実適用: 1975 passed, 1 warning）
next_action: なし（解決済み。修正は 89582df、本記録のアーカイブ commit は別）。利用者の案A選択（2026-10-24）に基づき適用・検証・コミット完了。

reasoning_checkpoint:
  hypothesis: "テスト終了後に Tk root/Variable の循環ガベージが残り（test_config_notification.py の実Tk約12件・test_batch_ocr_dialog.py 10件）、後続テストの循環GCがワーカースレッド内で発火して回収するため、Tcl interpreter が生成スレッド以外で解放される"
  confirming_evidence:
    - "寿命プローブ（weakref.finalize、GC不変更）で同一シグネチャの警告2件が447件部分実行で自然再現。Tk 2 + Variable 12 が final_thread=ThreadPoolExecutor-10_0 / during=test_always_retryable_errors_after_max_retries、生成は全て MainThread の test_config_notification.py 由来"
    - "全件でも寿命プローブのみ（修正なし）で再現（1973 passed, 2 warnings）。犠牲テストは test_retryable_once_then_success に入れ替わり、加害側は同じ test_corrupt_two_failures_rebuild_edit_recovery_and_exit の Tk 1 + Variable 6"
    - "決定的実証: 自動GC無効でガベージ蓄積→別スレッドで gc.collect() すると Tcl leak RuntimeWarning と Variable.__del__ RuntimeError が必ず再現"
    - "修正模擬（各テスト teardown 後のメインスレッド gc.collect()）で、警告が再現していた同条件でも 447件 1 warning・Tk 29/Var 204 全てメインスレッド解放。全件 1973 passed, 1 warning（ByteString のみ）"
  falsification_test: "修正模擬(バリア)有りで、寿命プローブ上に final_in_main=False の Tk/Variable、または Tcl leak / Variable.__del__ 警告が1件でも出れば仮説（または修正の十分性）は誤り -> 全件・部分実行とも0件で反証されず"
  fix_rationale: "原因は『Tk/Variable の循環ガベージの回収スレッドが非決定』であり、個別テストの Tk 破棄漏れではない（tkinter の Tk は破棄後も循環で残るのが通常）。GC発火位置はアロケーション列依存で、個別テスト修正は 1970->1973 件のような摂動で別テストが露出する（config-notice-tk-lifecycle で TkinterDnD.Tk() を段階的に直して再発した経緯と同型）。テスト境界で必ずメインスレッドの gc.collect() を実行すれば、回収が生成スレッドで決定的に行われる。警告を隠さず根本の『非メインスレッド回収』を除去する"
  blind_spots: "(1) モジュール内の別スレッド実行中に同一テスト内で生じたガベージは本バリアでは防げない（全件模擬では未観測）。(2) test_config_notification.py の undestroyed な live root（gc.collect() 後も残る約14個）は C 側 Tcl コマンド参照で GC から見えず、プロセス終了時にメインスレッドで解放される前提（観測上 sessionfinish 時 main）。(3) 実 conftest での実測は未実施（模擬はプラグイン）。(4) Python 3.15.1 の GC 実装依存で、将来の版で閾値挙動が変わりうる"
  candidate_causes:
    - "code(test): テストが Tk/Variable の循環ガベージを残し、回収スレッドを制御していない（確定）"
    - "environment: Python 3.15.1 / Tcl-Tk 9.0 で非メインスレッド回収時に leak 警告・Variable.__del__ RuntimeError が出る仕様（gh-83274）。循環GCは閾値を越えたスレッドで走る（確定・変更不可）"
    - "data/config(タイミング): 収集テスト数・pytest のアロケーション列で GC 発火位置が決まる（プローブ有無・1970->1973 件で出入り。確定・変更不可の誘因）"
    - "code(product): BatchOCRDialog/PDFEditorApp が Variable を属性保持する通常パターン（棄却: 製品は修正不要）"
    - "code(verification tool diff): 未commit の release_uat_support 差分（棄却: 直接原因ではなく件数増による露出のみ）"
  and_gate: "yes。『(a) テストが Tk/Variable 循環ガベージを残す』と『(b) その回収がワーカースレッド内で起きる（GC発火位置のずれ）』の同時成立が必要。(a) が無ければ回収対象が無く、(b) が無ければ警告にならない。(b) は制御不能なため、制御可能な (a)＋回収スレッド固定で断つ"

## Evidence

- timestamp: 2026-10-24 18:03 JST; 原本ログ末尾（sha256 9fd3c23c…ef0369 確認済み・無改変）。警告2件は `tests/test_ocr.py::TestRunParallelBackoff::test_always_retryable_errors_after_max_retries` に帰属。RuntimeWarning の発生元は `unittest/mock.py:2263 def __init__(self, name, parent)`（= `_Call.__init__`、MagicMock の `time.sleep` 呼び出し記録）、unraisable の traceback は `ocr.py:359 _call` → `test_ocr.py:699 side_effect` の例外処理コンテキスト。= **ThreadPoolExecutor ワーカースレッド内で GC が走り、そこで Tk/Variable が解放された**ことを示す。`tkinter/__init__.py:420 Variable.__del__` が `self._tk.call("info","exists",...)` で `RuntimeError: main thread is not in main loop`。
- timestamp: 2026-10-24 18:04 JST; Python 3.15.1 / Tcl-Tk 9.0 / GIL有効 / `gc.get_threshold()=(2000,10,10)`。test_ocr.py 自体は Tk を一切使わない（grep: 言及はコメントのみ）。`tests/test_release_uat_support.py` は test_ocr.py より後に実行され、差分（locked_ok/locked, 3件）は Tk 非使用。未commit差分は警告の直接原因ではない。
- timestamp: 2026-10-24 18:06 JST; **ガベージ生成元の特定**（診断プラグイン `scratchpad/probe/tk_leak_probe.py`: 自動GC無効化＋各テストteardown後に gc.collect() 前後の Tk/Variable 数を記録、先頭10ファイル447件、ログ `probe1.log`）。teardown直後に回収待ちの循環ガベージを残すテスト: `test_batch_ocr_dialog.py` の E2E/Summary 10件（各 Variable 3個: `dialogs/batch_ocr.py` の overall_progress_var/status_var/file_select_var がモジュール共有 `tk_root` を master に持つ）、`test_config_notification.py` の実Tkテスト約12件（各 Tk root 1 + Variable 6）。例: `TestNotificationLifecycle::test_real_root_visibility_suspends_same_event[withdraw]`, `TestConfigAcceptance::test_corrupt_two_failures_rebuild_edit_recovery_and_exit`, `TestLoadProtection::test_exit_preserves_corrupt_original_and_cancel_keeps_work[None/True]` ほか。
- timestamp: 2026-10-24 18:08 JST; **自然GCでの再現**（寿命プローブ `scratchpad/probe/tk_life_probe.py`: Tk/Variable 生成テストと解放時スレッド・実行中テストを weakref.finalize で記録。GC挙動は不変更。先頭10ファイル447件、`life1.log`/`run_life1.txt`）。結果 `447 passed, 3 warnings`。**同一テスト・同一 mock.py:2263・同一 Variable.__del__ traceback の警告2件が再現**。finalize ログ: `test_config_notification.py::TestConfigAcceptance::test_corrupt_two_failures_rebuild_edit_recovery_and_exit` 由来の Tk 1 + Variable 6、`TestLoadProtection::test_exit_preserves_corrupt_original_and_cancel_keeps_work[None]` 由来の Tk 1 + Variable 6 が `final_thread=ThreadPoolExecutor-10_0 / during=test_ocr.py::...test_always_retryable_errors_after_max_retries` で解放。生成は全て MainThread。他の Tk 27個/Variable 192個はメインスレッドで解放（ただし「生成したテストの数〜数百テスト後」に遅延解放されており、生成テスト終了時点では解放されていない）。
- timestamp: 2026-10-24 18:09 JST; **対照（プローブ無し）**: 同じ先頭10ファイル447件をプラグイン無しの自然実行で2回 → `447 passed, 1 warning`（Tcl警告0件）。= 再現は GC 発火位置（アロケーション列）依存。プローブの weakref/ラッパーが列をずらすだけで出る・消える。原本全件での出現も、収集テスト数 1970→1973 による GC 発火位置のずれで説明できる（潜在バグ）。
- timestamp: 2026-10-24 18:11 JST; **決定的な機構実証**（`scratchpad/probe/force_thread_gc.py`: 自動GC無効でガベージ蓄積し、対象テスト直前に別スレッドで gc.collect()、447件、`runD.txt`）→ `447 passed, 3 warnings`、`test_always_retryable_errors_after_max_retries` に `RuntimeWarning: the Tcl interpreter is leaked ... (gh-83274)` と `RuntimeError: main thread is not in main loop`（PytestUnraisableExceptionWarning）が再現。「先行テストが残した Tk/Variable ガベージ ＋ 非メインスレッドでの回収」で2警告が必ず出ることを確認。
- timestamp: 2026-10-24 18:12 JST; **修正模擬（リポジトリ未変更）**: `scratchpad/probe/gc_barrier.py`（各テストの teardown 完了後にメインスレッドで gc.collect()）＋寿命プローブ（上記で警告が再現した摂動と同条件）→ `447 passed, 1 warning`（Tcl警告0件）、Tk 29個/Variable 204個すべて `final_in_main=True`。gc.collect() 追加コストは約 5ms/テスト（447件で約2秒）。
- timestamp: 2026-10-24 18:23 JST; **全件・修正模擬（リポジトリ未変更）**: `-p gc_barrier` のみで単一プロセス全件（fresh basetemp `pf_tclleak_F1_*`、ログ `scratchpad/probe/full_F1.txt`）→ `1973 passed, 1 warning in 443.84s`（警告は PyMuPDF ByteString のみ）。原本 431.25s に対し +3%（実行ばらつきの範囲）。
- timestamp: 2026-10-24 18:31 JST; **全件・寿命プローブのみ（修正なし）**: `-p tk_life_probe` で単一プロセス全件（`full_F0.txt`/`life_F0.log`）→ `1973 passed, 2 warnings`。unraisable 警告が今度は `test_ocr.py::TestRunParallelBackoff::test_retryable_once_then_success` に帰属（犠牲テストが入れ替わる）。非メインスレッド解放は Tk 1 + Variable 6、生成は同じ `test_config_notification.py::TestConfigAcceptance::test_corrupt_two_failures_rebuild_edit_recovery_and_exit`（`final_thread=ThreadPoolExecutor-9_0`）。= 加害側は安定して config 通知テストの Tk、犠牲側は GC 発火位置次第。
- timestamp: 2026-10-24 18:14 JST; 回帰ガード案の動作確認（Tk 非依存・`scratchpad/probe/guard/test_gc_barrier_guard.py`）: バリア有り `2 passed`、バリア無し `1 failed, 1 passed`（test_b が失敗）。= バリアの存在を決定的に検知できる。
- 備考: 提案 conftest は `scratchpad/probe/proposed/conftest.py`（ruff check/format 通過済み。ただし書出しが CRLF のため、実適用は Edit ツールで LF のまま `import gc` と `pytest_runtest_teardown` ラッパーを追加すること。tests/conftest.py は LF）。-> 下記 18:3x〜18:5x の実適用で、提案と同一内容（CRLF 差のみ）を LF のまま適用済み。
- timestamp: 2026-10-24 18:3x JST; **案A適用（利用者選択済み）**。`tests/conftest.py` に `import gc` と `@pytest.hookimpl(wrapper=True) def pytest_runtest_teardown(item, nextitem)`（`try: return (yield) finally: gc.collect()`）を Edit ツールで追加（+20 行、`git ls-files --eol` i/lf w/lf 維持、CR バイト 0、提案と CRLF 差のみで同一）。`tests/test_gc_barrier_guard.py` を新設（Tk 非依存・決定的の 2 件、LF）。当初の docstring が `ruff check` で E501（全角 2 桁幅換算）6 件になったため docstring を折り返して解消（コード部は提案どおり）。`ruff check .` All checks passed、`ruff format` は py 2 本のみ明示指定で unchanged（`ruff format .` は未使用）。実行前後の既存 dirty ファイル 10 本＋pyproject.toml の sha256 は完全一致。
- timestamp: 2026-10-24 18:4x JST; **revert-and-reconfirm（実リポジトリ）**。修正済み conftest をバックアップ（sha256 `90a2d0d36b8f8fd74133d71062cf88eb2e72289959d04ee8022d581f0e73b176`）-> `git show HEAD:tests/conftest.py` で一時的に元へ戻す（blob `a19cd0c4…` に一致）-> 回帰ガード `1 failed, 1 passed`（`test_b_barrier_collected_it` が `AssertionError: teardown 後のメインスレッド gc.collect() が働いていない`）-> バックアップから復元（sha256 一致）-> 回帰ガード `2 passed`。バリアの存在を決定的に検知できることを実リポジトリで確認。
- timestamp: 2026-10-24 18:44〜18:52 JST; **単一プロセス全件（実リポジトリ conftest のみ・診断プラグイン／-k／--ignore／skip／警告フィルタなし）**: `1975 passed, 1 warning in 482.71s (0:08:02)`、exit 0。収集 1975 = 1973 + 回帰ガード 2。警告は PyMuPDF `ByteString` DeprecationWarning 1 件のみ。ログ内の `Tcl interpreter is leaked` / `PytestUnraisableExceptionWarning` / `RuntimeWarning` / `main thread is not in main loop` / `Traceback` / `STATUS_` / failed / error はすべて 0 件。ログ `logs/full_fix_real_conftest.txt`（sha256 `027e2ddcd518e695cbdcfec85ff82b7818a7efd7aea8ed8f713d6085a8186bb4`、basetemp `pf_tclleak_fix_1792835044`）。所要は原本 431.25s／模擬 443.84s に対し +9〜12%。gc.collect() の追加コストは計測上約 5ms/テスト（1975 件で約 10 秒）で、差の全てはそれでは説明できない。実行ばらつき（実行中に行った読み取り専用の確認作業を含む）が混在しており、性能への影響の有無は未切り分け（合否条件ではない）。
- timestamp: 2026-10-24 18:5x JST; **未commit検証ツール修正のテスト**: 上記全件に `tests/test_release_uat_support.py`（`TestLockedOverlayVerification` 3 件を含む）が含まれ全て通過。該当ファイル単体の補助実行（全件の合否判定には不使用）でも `87 passed, 1 warning`、`TestLockedOverlayVerification` のみで `3 passed`。この 2 ファイルは今回コミットせず作業ツリーに保持。
- timestamp: 2026-10-24 18:54 JST; **コミット**: 修正 `89582df`（tests/conftest.py, tests/test_gc_barrier_guard.py, 開発履歴.md の自分の 1 行のみ。他作業の 20 行 hunk は index に載せず作業ツリーに保持）。原本ログ `06-04-fixgate-full-tcl-warning.txt` の sha256 `9fd3c23c…ef0369` は無変更を再確認。


## Eliminated

- hypothesis: 未commitの検証ツール修正（tests/release_uat_support.py、tests/test_release_uat_support.py）が Tk を生成して警告を起こした
  evidence: 当該テストは test_ocr.py より後に実行される。差分は Tk 非使用。両ファイルを含まない先頭10ファイル447件の部分実行で同一シグネチャの警告が再現した。影響は「収集テスト数 1970→1973 によるGC発火位置のずれ」に限られる（直接原因ではなく露出の引き金）。
  timestamp: 2026-10-24 18:08 JST
- hypothesis: test_ocr.py 自体、または run_parallel（ocr.py）が Tk/Variable を生成・保持している
  evidence: test_ocr.py に Tk 生成は無い（言及はコメントのみ）。寿命プローブで解放された全 Tk/Variable の生成元は test_config_notification.py / test_batch_ocr_dialog.py で、test_ocr.py 由来は 0。warning の発生元 mock.py:2263 はワーカー内の MagicMock 呼び出し記録で、単に「そのスレッドで GC が走った地点」。
  timestamp: 2026-10-24 18:08 JST
- hypothesis: 単一の特定テストだけがリーク元で、それを直せばよい
  evidence: teardown 後にガベージを残すテストは test_batch_ocr_dialog.py 10件・test_config_notification.py 約12件。どれが「ワーカースレッド内で回収される側」になるかは GC 発火位置（アロケーション列）次第で、プローブ有無・テスト数で入れ替わる。個別テストの修正では再発する（先行 config-notice-tk-lifecycle で TkinterDnD.Tk() 3箇所を段階的に直しても再発した経緯と同型）。
  timestamp: 2026-10-24 18:11 JST
- hypothesis: 製品コード（BatchOCRDialog / PDFEditorApp の Variable 保持）の修正が必要
  evidence: tk.StringVar を dialog 属性に持つのは通常の tkinter パターン。製品でダイアログを閉じるのはメインスレッドで、テストのような「別スレッド内でのGC回収」を意図的に誘発する構造はない。製品側に変更しなくてもテスト側のメインスレッド回収バリアで警告は解消できることを実証（Evidence 18:25）。製品変更は不要。
  timestamp: 2026-10-24 18:12 JST

## Resolution

root_cause: [AND-gate] (a) テスト側: tests/test_config_notification.py の実Tkテスト（約12件、各 Tk root 1 + Variable 6）と tests/test_batch_ocr_dialog.py（10件、各 Variable 3）が、終了時に Tk/Variable の循環ガベージを残し、テスト境界で回収されない; (b) 実行時: その回収が run_parallel の ThreadPoolExecutor ワーカースレッド内の循環GCで起きると、Tk が生成スレッド以外で解放され Tcl leak RuntimeWarning（gh-83274）と Variable.__del__ の RuntimeError（main thread is not in main loop）になる。GC発火位置はアロケーション列依存で、収集テスト数 1970→1973（未commit検証ツール修正の追加3件）や計測有無で出入りする潜在バグ。
fix: 案A（利用者選択・テスト基盤のみ、製品コード変更なし）。tests/conftest.py に `@pytest.hookimpl(wrapper=True) def pytest_runtest_teardown(item, nextitem)` を追加し、各テストの後始末（モジュール/セッション fixture 分を含む）の直後に `try: return (yield) finally: gc.collect()` でメインスレッドの循環GCを実行する。Tk/Variable ガベージを生成元のメインスレッドで決定的に回収し、ワーカースレッド内GCでの回収（＝Tcl leak 警告・Variable.__del__ RuntimeError）を構造的に断つ。回帰ガード tests/test_gc_barrier_guard.py を新設（Tk 非依存・決定的）。コミット 89582df。
verification: (1) 実リポジトリ revert-and-reconfirm: conftest を HEAD に戻すと回帰ガード `1 failed, 1 passed`（test_b 失敗）、修正済みを復元（sha256 一致）すると `2 passed`。(2) 実リポジトリの conftest のみ（診断プラグイン・除外・skip・警告フィルタなし）による単一プロセス全件 `1975 passed, 1 warning in 482.71s`、exit 0。警告は PyMuPDF ByteString のみ、Tcl leak / PytestUnraisableExceptionWarning / RuntimeWarning / Traceback は 0 件（logs/full_fix_real_conftest.txt、sha256 027e2ddc…bb4）。(3) `ruff check .` 通過、`ruff format` は py 2 本のみ unchanged。(4) 事前の修正模擬でも 447 件部分で警告 0・Tk 29/Var 204 全てメインスレッド解放、全件 1973 passed, 1 warning。残る限界: GC 発火位置依存の Mandelbug のため『1 回の全件グリーン』は原因除去の証明ではなく、根拠は機構実証（決定的再現）と模擬/実適用の複数回グリーン。
files_changed: ["tests/conftest.py", "tests/test_gc_barrier_guard.py", "開発履歴.md", ".planning/debug/resolved/tcl-leak-test-ocr.md", ".planning/debug/tcl-leak-test-ocr-evidence/"]
oracle_type: derived（警告ゼロ＋解放スレッド＝メインスレッドの機構契約）
tdd: false
specialist_review: none
why_not_caught: 既存ゲートに該当なし。単一プロセス全件 pytest は警告を失敗扱いにしていない（Tcl leak は警告として出るのみ）ため、件数増で露出した時点で人手の警告確認でしか見つからなかった。Tk を使うテストが循環ガベージを残すこと自体は tkinter の通常動作でテストの不備ではない。
prevention: tests/conftest.py のメインスレッド gc.collect() バリア ＋ 回帰ガード tests/test_gc_barrier_guard.py::TestTeardownBarrier（バリア削除で test_b が決定的に失敗）。併せて『Tk/Variable の循環ガベージは回収スレッドが非決定で、ワーカースレッドのGCで回収されると Tcl leak 警告が無関係なテストに帰属する。個別テストの Tk 破棄修正ではなくテスト境界でのメインスレッド回収で防ぐ』という知見を本記録に残す。残リスク: (a) 同一テスト内でワーカースレッドが走る間に生じたガベージはバリアでは防げない（未観測）。(b) test_config_notification.py の未 destroy の live root（gc.collect() 後も残る約14個）はプロセス終了時にメインスレッドで解放される前提（観測上 sessionfinish 時 main）。(c) Python 3.15.1 の GC 実装依存で、版が変わると閾値挙動が変わりうる。再発時は logs/ のプローブ手順（plugins/*.py.txt を .py に戻して `-p`）で解放スレッドと帰属元を特定する。

## 診断成果物（原本保持）

`.planning/debug/tcl-leak-test-ocr-evidence/`（plugins/ = 診断プラグイン4本＋回帰ガード案（ruff対象外にするため拡張子 .py.txt。使用時は .py に戻す）、logs/ = 各実行ログ、SHA256SUMS.txt）。logs/full_fix_real_conftest.txt は修正適用後の実リポジトリ全件（案A適用の最終検証）。製品コード（pagefolio/）は未変更。修正で変更した tests/ 配下は tests/conftest.py（バリア追加）と tests/test_gc_barrier_guard.py（新設）のみ。plugins/test_gc_barrier_guard.py.txt は適用前の提案原本で、実リポジトリ版は ruff E501 対応で docstring のみ折り返している（コード部は同一）。
