---
phase: 03-qa-release-gate
plan: 01
subsystem: file-ops
tags: [toast, retry, save, file-ops, functools-partial, requirements-doc, pytest]

requires: []
provides:
  - "pagefolio/file_ops.py: _do_save_file(path) / _do_save_as(path) / _do_save_compressed(path, save_kwargs) — 保存3経路の path 引数を取る実保存層（確認ダイアログ・保存先ピッカーを含まない）"
  - "保存トーストの retry_cb が確定パス（と save_kwargs）を functools.partial で束縛し、確認・保存先選択を再表示しない挙動（V190-QA-02）"
  - "REQUIREMENTS.md の V190-QA-02 文言訂正（D-12）"
affects: [03-02-test-env-investigation, 03-03-uat-release]

actuals:
  tokens: 6455
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "確認・パス選択層 と path 引数を取る実保存層（Tk非依存）への分離。既存の _overwrite_current_file(path, **save_kwargs) と同型のパターンを _save_file/_save_as/_save_compressed へ横展開"
    - "functools.partial(self._do_save_*, path[, save_kwargs]) で retry_cb を確定時点の値へ束縛し、以降のアプリ状態変化（self.filepath の差し替え等）から独立させる"
    - "テストの検証方式をオブジェクト等価性（retry_cb == app._save_file）から振る舞い検証（askyesno/asksaveasfilename の呼び出し回数スパイ）へ置き換え"

key-files:
  created: []
  modified:
    - pagefolio/file_ops.py
    - tests/test_toast.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Task 1（type=tracer）の <verify> 完全自動通過後、対話モードのtracerゲート（checkpoint:human-verify）を人手待ちにせず Task 2 へ自動続行した。理由: 全検証が pytest/ruff の完全自動判定であり、<verify> にGUI操作・視覚判断を要する要素が無く、セッションが config.json の mode: yolo（02-01 SUMMARY と同一の前例）で構成されているため。GSD config の workflow.auto_advance は false のままだが、判断の透明性のためここに明記する"
  - "_RaisingThenOkDoc スタブに fail_times パラメータ（既定1・既存呼び出しは無変更）を追加し、save_paths/save_kwargs_history の記録機能を付与。新規スタブを追加せず既存スタブを最小拡張する方針（03-CONTEXT.md/03-PATTERNS.md の指示に従う）"
  - "Task 3: ROADMAP.md の Goal 文・Success Criteria #2 は計画時点で既に D-12 訂正後の文言だったため変更なし（内容確認のみ・二重書き換えを回避）。REQUIREMENTS.md の V190-QA-02 のみが記述ミスのまま残っていたため、その1行のみを Edit で訂正した"

requirements-completed: [V190-QA-02]

coverage:
  - id: D1
    description: "保存トーストの retry_cb を呼ぶと askyesno/asksaveasfilename を経由せず、前回確定した対象へ黙って再保存される（保存3経路すべて）"
    requirement: "V190-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py#TestSaveFilePathsUseSharedHelper（retry_skips を含む10テスト）"
        status: pass
      - kind: unit
        ref: "tests/test_password.py（暗号化維持の既存回帰テスト全件）"
        status: pass
    human_judgment: false
  - id: D2
    description: "初回の保存操作では従来どおり確認ダイアログ・保存先ピッカーが表示される（確認スキップは再試行経路にのみ適用）"
    requirement: "V190-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestSaveFilePathsUseSharedHelper::test_save_file_initial_save_still_shows_confirm_dialog"
        status: pass
      - kind: unit
        ref: "tests/test_toast.py::TestSaveFilePathsUseSharedHelper::test_save_as_initial_save_shows_picker_cancel_skips_save"
        status: pass
      - kind: unit
        ref: "tests/test_toast.py::TestSaveFilePathsUseSharedHelper::test_save_compressed_initial_save_shows_picker_cancel_skips_save"
        status: pass
    human_judgment: false
  - id: D3
    description: "トースト表示中にアプリ状態（filepath/doc）が変化しても、retry_cb は束縛時のパスにのみ書き込み、ファイルクローズ後は書き込まない"
    requirement: "V190-QA-02"
    verification:
      - kind: unit
        ref: "tests/test_toast.py::TestSaveFilePathsUseSharedHelper::test_save_file_retry_writes_to_bound_path_not_current_filepath"
        status: pass
      - kind: unit
        ref: "tests/test_toast.py::TestSaveFilePathsUseSharedHelper::test_save_file_retry_noop_after_doc_closed"
        status: pass
    human_judgment: false
  - id: D4
    description: "REQUIREMENTS.md / ROADMAP.md の V190-QA-02 関連文言が実装（再試行時は確認を再表示しない）と一致している"
    requirement: "V190-QA-02"
    verification:
      - kind: other
        ref: "grep -n V190-QA-02 .planning/REQUIREMENTS.md / grep -n 前回確定した対象へ黙って再保存 .planning/ROADMAP.md"
        status: pass
    human_judgment: false

duration: 約20分
completed: 2026-08-11
status: complete
---

# Phase 3 Plan 1: 保存トースト再試行の確認スキップ Summary

**保存トーストの「再試行」が上書き確認・保存先選択を再表示せず前回確定した対象へ黙って再保存するよう、保存3経路（_save_file/_save_as/_save_compressed）を確認・パス選択層と path 引数を取る実保存層へ分離した（V190-QA-02・D-09〜D-12）**

## Performance

- **Duration:** 約20分（git commit ログ基準・1845e6d → 34ea35d）
- **Started:** 2026-08-11T19:14:10+09:00（Task 1 コミット）
- **Completed:** 2026-08-11T19:20:14+09:00（Task 3 コミット）
- **Tasks:** 3 / 3
- **Files modified:** 3（`pagefolio/file_ops.py`・`tests/test_toast.py`・`.planning/REQUIREMENTS.md`）

## Accomplishments

- `_save_file` を「確認・パス選択層」（`askyesno`）と `_do_save_file(path)`（実保存層。`self.doc` が falsy なら書き込まずステータス通知のみで return するガード付き）に分離した縦スライスを、`file_ops.py` → `ui_builder.py:_show_error_or_toast` → `toast.py:ToastManager` → 振る舞い検証テストまで端から端まで通した（Task 1・tracer）
- `_save_as`/`_save_compressed` を同型で `_do_save_as(path)`/`_do_save_compressed(path, save_kwargs)` へ水平展開（Task 2）。`_do_save_compressed` は `save_kwargs` を明示引数（`**kwargs` にしない）で受け取り、束縛時の dict がそのまま再利用されることを型として明示
- 保存3経路すべての `retry_cb` を `functools.partial(self._do_save_*, path[, save_kwargs])` で確定パス束縛に統一（`grep -c "functools.partial(self._do_save_"` = 3）
- `tests/test_toast.py` に `retry_skips` を含む振る舞いテスト10件を追加し、既存3件のオブジェクト等価性アサーション（`retry_cb == app._save_file` 等）を「askyesno/asksaveasfilename の呼び出し回数」ベースの検証へ置き換え。並行性エッジ（トースト表示中の `filepath` 差し替え・`doc` クローズ後の古い再試行）も個別テストで固定
- `pagefolio/ui_builder.py`・`pagefolio/toast.py` は無改造のまま維持（D-11）。`tests/test_password.py` の暗号化維持テスト全件 green（`encryption=fitz.PDF_ENCRYPT_KEEP` の受け渡しに退行なし）
- `REQUIREMENTS.md` の V190-QA-02 文言を D-12 の訂正後表現へ更新。`ROADMAP.md` は計画時点で既に訂正済みだったため確認のみ（Task 3）
- フルテストスイート 1398 passed（0 failed）。1回だけ `tests/test_ocr_dialog_center.py` 2件で既知の TclError フレーキー（STATE.md「Blockers/Concerns」に記録済み・本プランの変更とは無関係）が発生したが、直後の再実行では 1398/1398 grün を確認済み

## Task Commits

1. **Task 1: tracer — 「保存失敗 → トースト再試行 → 確認なしで再保存」を `_save_file` 1経路で端から端まで通す** - `1845e6d` (feat)
2. **Task 2: `_save_as` / `_save_compressed` への水平展開（D-10 の3経路一貫化）** - `5040ef4` (feat)
3. **Task 3: D-12 の文言訂正（REQUIREMENTS.md / ROADMAP.md）** - `34ea35d` (docs)

## Files Created/Modified

- `pagefolio/file_ops.py` - `_do_save_file`/`_do_save_as`/`_do_save_compressed` 新設。`_save_file`/`_save_as`/`_save_compressed` を確認・パス選択層のみへ縮小。`import functools` 追加
- `tests/test_toast.py` - `_RaisingThenOkDoc` に `fail_times`/`save_paths`/`save_kwargs_history` を追加、`_FakeFileOpsApp` に `overwrite_paths`/`status_calls` を追加。`retry_skips` を含む10テストを新規追加、既存3テストのアサーションを振る舞いベースへ置き換え
- `.planning/REQUIREMENTS.md` - V190-QA-02 の1行を D-12 の訂正後文言へ置換

## Decisions Made

- **Task 1（tracer）ゲートの自動続行:** `<verify>` が pytest（`test_toast.py`/`test_password.py`/`test_save_overwrite.py`）の完全自動判定で全通過し、GUI操作や視覚判断を要する要素が無かったこと、およびセッションが `config.json` の `mode: yolo` で構成されていたこと（02-01 SUMMARY と同一の前例）から、対話モードの `checkpoint:human-verify` による人手待ちを行わず Task 2 へ続行した
- **`_RaisingThenOkDoc` の最小拡張:** 新規スタブを追加せず、`fail_times` パラメータ（既定値1で既存呼び出しと完全互換）・`save_paths`/`save_kwargs_history` の記録機能のみを既存スタブへ追加する形で Behavior Test 3/4/6（連続 retry・並行性エッジ）を実装した
- **Task 3 の ROADMAP.md 非改変:** `ROADMAP.md` の Goal 文（197行目）と Success Criteria #2（203行目）は計画時点で既に D-12 訂正後の文言だったため、二重書き換えを避けて内容確認のみで完了とした（`REQUIREMENTS.md` の1行のみ Edit）

## Deviations from Plan

None - 計画どおりに実行完了。3経路の分離・テスト置き換え・文言訂正はすべて `<action>`/`<acceptance_criteria>` の記述どおりに実装した。

## Issues Encountered

- フルスイート実行1回目で `tests/test_ocr_dialog_center.py` の2テストが `_tkinter.TclError` でERRORになったが、これは STATE.md「Blockers/Concerns」に既に記録済みの既知フレーキー症状（本プランのファイル変更範囲外・V190-QA-01 の調査対象）。直後の再実行（同一環境）では1398/1398 grün を確認し、`pagefolio/file_ops.py`/`tests/test_toast.py`/`REQUIREMENTS.md` への変更に起因する問題ではないことを確認した

## User Setup Required

None - 本プランは既存コードの内部関数分離とテスト振る舞い検証のみで完結し、新規依存・環境変数・外部設定を必要としない。

## Next Phase Readiness

- V190-QA-02 は完了。保存3経路すべてが同一の分離形（確認・パス選択層 + path 引数を取る実保存層）を持ち、`REQUIREMENTS.md`/`ROADMAP.md` の文言が実装と一致した状態で V190-QA-01（環境切り分け・分割実行ゲート）・V190-QA-03（human-verify/UAT）の後続プランに進める
- 保存トーストの `retry_skips` パターンは今後同様の「再試行時は確認をスキップする」UX を実装する際の参照実装として `pagefolio/file_ops.py` に残る

## Self-Check: PASSED

- `grep -c "def _do_save_file" pagefolio/file_ops.py` → 1（FOUND）
- `grep -c "def _do_save_as" pagefolio/file_ops.py` → 1（FOUND）
- `grep -c "def _do_save_compressed" pagefolio/file_ops.py` → 1（FOUND）
- `grep -c "functools.partial(self._do_save_" pagefolio/file_ops.py` → 3（FOUND）
- `grep -c "retry_skips" tests/test_toast.py` → 10（FOUND）
- コミットハッシュ `1845e6d`/`5040ef4`/`34ea35d` は `git log --oneline --all` に存在（FOUND）
- `git diff --stat -- pagefolio/ui_builder.py pagefolio/toast.py` → 出力空（FOUND・無改造を維持）

---
*Phase: 03-qa-release-gate*
*Completed: 2026-08-11*
