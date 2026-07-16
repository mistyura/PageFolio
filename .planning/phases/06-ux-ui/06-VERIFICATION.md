---
phase: 06-ux-ui
verified: 2026-07-16T00:00:00Z
status: human_needed
score: 20/20 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "アプリを起動し、上書き保存/別名保存/縮小保存/印刷のいずれかを一時的失敗が起きる状況（読み取り専用パス・ロック中ファイル・印刷ハンドラ未関連付け等）で実行し、メインウィンドウ右下にトーストが表示されることを目視確認する。テーマ切替（設定画面でテーマ変更）を行った直後に再度同じ失敗を起こし、トーストが引き続き正しく表示・操作できることも確認する。"
    expected: "右下に再試行ボタン付きの非モーダルトーストが表示され、自動消滅しない。✕ボタン・再試行成功・別経路成功のいずれかで消える。テーマ切替後も同様に機能する。"
    why_human: "Tkinter の実際の描画結果（位置・重なり・視認性・テーマ追従）は自動テストでは検証できない視覚的確認項目（VALIDATION.md Manual-Only Verifications・06-01-SUMMARY.md）。"
  - test: "プラグイン管理ダイアログを開き、プラグイン一覧上でマウスホイールスクロールを操作する。「🔄 再検出」ボタンを押した直後にも同じ一覧上でホイールスクロールが機能し続けることを確認する。また OCR ダイアログを低解像度（または大きめのフォントサイズ設定）の環境で開き、ダイアログ下端が画面外にはみ出さないことを確認する。"
    expected: "プラグイン一覧はマウスホイールでスクロールでき、再検出後も引き続きスクロールできる。OCR ダイアログは低解像度環境でも画面内に収まる。"
    why_human: "実際のマウスホイールイベント配送はTkイベントループ・実ウィジェット階層・実機ディスプレイ解像度に依存し、pytestのTk非依存/最小生成スタブでは体感相当の確認ができない（06-02-SUMMARY.md coverage D3/D4・06-SCROLL-FONT-AUDIT.md §1.4）。回帰テスト（test_plugin_dialog_wheel.py/test_ocr_dialog_center.py）は束縛状態・geometry計算のみを検証しており、実際のスクロール体感・実機表示は別途確認が必要。"
---

# Phase 6: 品質保証仕上げ（通知UX・UI一貫性監査・ドキュメント整合） Verification Report

**Phase Goal:** エラー時のリカバリー導線・UI の一貫性が磨き込まれ、開発履歴.md の版番表記が整合してマイルストーンを締められる。
**Verified:** 2026-07-16
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged from ROADMAP.md Success Criteria (3) and PLAN frontmatter `must_haves.truths` (06-01/06-02/06-03).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | 軽微なエラー発生時、再試行アクション付きの非モーダルトースト通知が表示され自動消滅しない（重大エラーダイアログは維持） | ✓ VERIFIED | `pagefolio/toast.py` ToastManager + `pagefolio/file_ops.py`/`print_ops.py` wired via `_show_error_or_toast`; `messagebox.showerror` still used for open/auth/password paths (file_ops.py:544,567,578,607,820,847) |
| SC2 | スクロールパターンとフォントスケーリングがダイアログ間で監査され、不一致箇所が是正される | ✓ VERIFIED | `06-SCROLL-FONT-AUDIT.md` (8-file audit table); `about.py` font fix; `plugin.py`/`ocr_dialog.py` scroll fixes |
| SC3 | 開発履歴.md の v1.7.0 表記が実際のバージョン履歴と整合する（V16-D-04 解消） | ✓ VERIFIED | `06-CHANGELOG-AUDIT.md`; 開発履歴.md v1.6.1 date corrected to 2026-06-23 (matches `git log -1 --format=%ai v1.6.1` = 2026-06-23 18:03:06); `.planning/PROJECT.md` V16-D-04 row now reads "✅ 解消済み" with no leftover "Revisit/⚠️" |
| D-01 | 入力バリデーション・ファイルオープン・パスワード系エラーは従来どおり messagebox モーダル維持 | ✓ VERIFIED | grep confirms 6 remaining `messagebox.showerror` calls in `_open_file`/`_authenticate_doc`/`_do_open_merged`/`_open_pdf_path`/`_set_password`/`_remove_password` ranges, unchanged |
| D-02 | トースト対象は保存3操作+印刷の4操作に限定 | ✓ VERIFIED | `file_ops.py` `_save_file`/`_save_as`/`_save_compressed`, `print_ops.py` `_print_pdf`/`_send_to_printer` call `_show_error_or_toast`; no other messagebox converted |
| D-03 | 再試行ボタンで同一操作が再実行される | ✓ VERIFIED | `tests/test_toast.py::test_retry_button_invokes_retry_cb`; integration tests assert `retry_cb == app._save_file` etc. |
| D-04 | 再試行再失敗時は同じトーストが文言更新され残る（回数制限なし） | ✓ VERIFIED | `tests/test_toast.py::test_same_category_reshow_updates_message_and_stays` (real Tk Frame identity check) |
| D-05 | テーマ切替（`_rebuild_ui`）後もトーストが有効 | ✓ VERIFIED | `pagefolio/ui_builder.py:187` `self._toast = ToastManager(self)` inside `_build_ui()`; `app.py` `_rebuild_ui()` (line 655) calls `_build_ui()` (line 673) — code path traced directly; `tests/test_toast.py::TestToastRegeneratedAfterRebuild` exercises the regenerate-after-destroy pattern with a minimal stub (documented simplification per CONTEXT.md Claude's Discretion) |
| D-06/D-07 | 右下配置・同時1件のみ表示（新規は既存を置換） | ✓ VERIFIED | `toast.py._build_frame` `place(relx=1.0, rely=1.0, anchor="se", ...)`; `tests/test_toast.py::test_second_show_replaces_single_toast` |
| D-08 | ✕/再試行成功/別経路成功で消える。異なるカテゴリの dismiss は no-op | ✓ VERIFIED | `tests/test_toast.py::test_dismiss_matching_removes_and_mismatch_is_noop`, `test_close_button_dismisses_toast`; `file_ops.py`/`print_ops.py` success paths call `self._toast.dismiss(category)` |
| D-09 | LANG/C/_font 経由、ja/en キー数一致 | ✓ VERIFIED | `pagefolio/lang.py` `toast_retry_btn` present in both ja(625)/en(1332) blocks; `tests/test_lang_parity.py` passes; no hex/numeric-font literals in `toast.py` |
| R1 | 印刷の一時ファイル失敗とOS印刷失敗が同一カテゴリでも異なる文言で区別できる | ✓ VERIFIED | `print_ops.py` uses `err_print_msg.format(e=e)` vs `err_print_no_handler`; `tests/test_toast.py::test_tempfile_failure_and_os_failure_have_distinct_messages` |
| WR-03 | 同一カテゴリ再show時も最新 retry_cb へ差し替わる（コードレビュー修正） | ✓ VERIFIED | `toast.py.show()` reconfigures `self._retry_btn`; `tests/test_toast.py::test_same_category_reshow_rebinds_retry_cb` |
| D-12/D-13 | フォントサイズ数値ハードコード是正（about.py）+ 回帰テストで検出ゼロ担保 | ✓ VERIFIED | `pagefolio/dialogs/about.py:45` `self._font(4, "bold")`; `tests/test_font_hardcode_guard.py` (2 tests: zero-offenders + literal-vs-variable regex assertion) pass |
| D-10 (plugin.py) | Canvas に llm_config 基準の動的 Enter/Leave ホイール束縛が追加される | ✓ VERIFIED (behaviorally tested + WR-02 fixed) | `pagefolio/dialogs/plugin.py:97-114`; `tests/test_plugin_dialog_wheel.py` simulates `<Enter>`, calls real `_rescan()`, asserts global binding survives (WR-02 regression); destroy still unbinds |
| D-10 (ocr_dialog.py) | `_center()` が画面高でクランプされ低解像度で画面外に出ない | ✓ VERIFIED (behaviorally tested + WR-01 fixed) | `pagefolio/ocr_dialog.py:210` `max_h = max(620, self.winfo_screenheight() - 100)` (floor raised to match `minsize(960,620)`); `tests/test_ocr_dialog_center.py` calls real `_center()` with spied `geometry()`, asserts h>=620 on short screens and h==680 (uncompressed) on large screens |
| D-11 | 8ファイルのスクロール監査、是正/受容差分の根拠が記録される | ✓ VERIFIED | `.planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md` §1.2/§1.3 (judgment table + rationale for 2 fixes + 4 accepted deviations); no common helper introduced (grep confirms no `make_scrollable_frame`) |
| D-17 | insert→undo→redo→undo(2回目) でページ数・内容が正しく往復（重複しない） | ✓ VERIFIED | `pagefolio/file_ops.py:401-408` `insert_redo` block now mirrors `delete_redo` (descending `delete_page`); `tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_undo_roundtrip` passes (re-ran independently, 1 passed) |
| D-17 | 修正は insert_redo ブロックのみに限定、他 op の対称性を壊さない | ✓ VERIFIED | Diff limited to lines 401-408 of `_restore_state`; `_apply_inverse` (line 295-304) unchanged; full `test_pdf_ops.py`/`test_undo_stress.py` remain green (1101 total suite passed) |
| D-14 | 開発履歴.md が git タグ・APP_VERSION・MILESTONES.md と突合され不一致が修正/記録される | ✓ VERIFIED | `06-CHANGELOG-AUDIT.md` full per-version table; v1.6.1 mismatch (2026-06-22→2026-06-23) independently confirmed against `git log -1 --format=%ai v1.6.1` = 2026-06-23 |
| D-15 | 旧 PDF Editor 時代の同名見出しは現状維持、監査記録に意図的共存と明記 | ✓ VERIFIED | `06-CHANGELOG-AUDIT.md` §旧PDF Editor時代エントリの意図的共存; git diff shows no changes to that region of 開発履歴.md |
| D-16 | PROJECT.md の V16-D-04 が解消済みへ更新、V16-D-05 は不変 | ✓ VERIFIED | `.planning/PROJECT.md:234` "✅ 解消済み"; line 235 V16-D-05 still "⚠️ Revisit" (unchanged) |

**Score:** 20/20 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/toast.py` | ToastManager class | ✓ VERIFIED | Exists, substantive (107 lines), wired into ui_builder/file_ops/print_ops |
| `tests/test_toast.py` | Unit + integration tests | ✓ VERIFIED | 15 test methods, all real Tk widgets, all pass |
| `pagefolio/lang.py` toast_retry_btn key | ja/en parity | ✓ VERIFIED | Present both blocks, `test_lang_parity.py` passes |
| `tests/test_font_hardcode_guard.py` | Source-scan regression test | ✓ VERIFIED | 2 tests, pass |
| `.planning/phases/06-ux-ui/06-SCROLL-FONT-AUDIT.md` | Audit record | ✓ VERIFIED | Exists, covers 8 files with judgment table |
| `.planning/phases/06-ux-ui/06-CHANGELOG-AUDIT.md` | Audit record | ✓ VERIFIED | Exists, covers full version range with judgment |
| `tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_undo_roundtrip` | 4-move regression test | ✓ VERIFIED | Exists, passes independently |
| `tests/test_ocr_dialog_center.py` | WR-01 regression | ✓ VERIFIED | New file, 2 tests, pass |
| `tests/test_plugin_dialog_wheel.py` | WR-02 regression | ✓ VERIFIED | New file, 2 tests, pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `ui_builder._build_ui()` | `pagefolio.toast.ToastManager` | `self._toast = ToastManager(self)` (line 187), re-run every `_build_ui()` call including from `_rebuild_ui()` (app.py:655→673) | ✓ WIRED | Confirmed via direct code trace |
| `file_ops.py`/`print_ops.py` failure paths | `ui_builder._show_error_or_toast` | `self._show_error_or_toast(category, title, msg, retry_cb)` | ✓ WIRED | 5 failure paths (3 save + 2 print) confirmed via grep + integration tests |
| `file_ops.py`/`print_ops.py` success paths | `ToastManager.dismiss` | `getattr(self, "_toast", None)` guard + `self._toast.dismiss(category)` | ✓ WIRED | Confirmed at file_ops.py:678-679,704-705,762-763 and print_ops.py:71-72,80-81 |
| `plugin.py` Canvas | dynamic wheel bind/unbind | `<Enter>`/`<Leave>`/`<Destroy>` bindings | ✓ WIRED | Confirmed + behaviorally tested (survives `_rescan()`, unbinds only on dialog destroy) |
| `ocr_dialog.py._center()` | `winfo_screenheight()` | height clamp before `geometry()` | ✓ WIRED | Confirmed + behaviorally tested (floor matches `minsize(960,620)`) |
| `file_ops.py._restore_state` insert_redo | `doc.delete_page` (descending) | mirrors `delete_redo` symmetric pattern | ✓ WIRED | Confirmed via code read + regression test |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| insert 4-move undo/redo roundtrip | `pytest tests/test_pdf_ops.py::TestInsertUndoRedo::test_insert_undo_redo_undo_roundtrip -x -q` | 1 passed | ✓ PASS |
| Toast/font/scroll/print regression files | `pytest tests/test_toast.py tests/test_font_hardcode_guard.py tests/test_ocr_dialog_center.py tests/test_plugin_dialog_wheel.py tests/test_lang_parity.py tests/test_print.py -q` | 31 passed | ✓ PASS |
| Full suite regression | `pytest -q` | 1101 passed, 1 unrelated warning (Tk `__del__` GC noise in `test_ocr.py`, pre-existing, unrelated to Phase 6 changes) | ✓ PASS |
| Lint | `ruff check .` / `ruff format --check .` | All checks passed / 87 files already formatted | ✓ PASS |
| v1.6.1 tag date cross-check | `git log -1 --format="%ai" v1.6.1` | 2026-06-23 18:03:06 +0900 (matches corrected 開発履歴.md date) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| V180-QA-02 | 06-01-PLAN.md | エラー時リカバリー通知が改善される（再試行アクション付き非モーダルトースト） | ✓ SATISFIED | ToastManager + wiring, all D-01〜D-09/R1/WR-03 truths verified |
| V180-QA-03 | 06-02-PLAN.md | UI 一貫性が監査・修正される（スクロールパターン統一・フォントスケーリング） | ✓ SATISFIED | Audit + about.py fix + plugin.py/ocr_dialog.py fixes (WR-01/WR-02) |
| V180-QA-04 | 06-03-PLAN.md | 開発履歴.md の v1.7.0 表記整合が完了する（V16-D-04 残課題） | ✓ SATISFIED | Audit + v1.6.1 date fix + PROJECT.md status update |

No orphaned requirements: REQUIREMENTS.md Traceability table maps only V180-QA-02/03/04 to Phase 6, and all three are claimed by exactly one plan each.

### Anti-Patterns Found

None. Scanned all phase-modified files (`toast.py`, `ui_builder.py`, `file_ops.py`, `print_ops.py`, `lang.py`, `about.py`, `plugin.py`, `ocr_dialog.py`, and new test files) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` — zero matches.

### Code Review Findings (06-REVIEW.md / 06-REVIEW-FIX.md)

3 warnings (WR-01, WR-02, WR-03) were found by the phase's own code-review agent and independently confirmed fixed with dedicated regression tests that exercise the actual defect mechanism (not just presence checks):
- WR-01 (ocr_dialog.py height clamp neutralized by minsize): fixed, `tests/test_ocr_dialog_center.py` verified.
- WR-02 (plugin.py wheel-unbind fires on every child destroy): fixed, `tests/test_plugin_dialog_wheel.py` verified.
- WR-03 (ToastManager drops updated retry_cb on re-show): fixed, `tests/test_toast.py::test_same_category_reshow_rebinds_retry_cb` verified.
IN-01 (retry re-triggers overwrite confirmation dialog) was explicitly scoped out as future polish, not a blocker — consistent with D-03's narrow re-try scope.

### Human Verification Required

1. **Toast visual/positional confirmation** — Trigger a transient save/print failure and confirm the toast appears bottom-right, non-modal, does not auto-dismiss, and continues to work after a theme switch. Why human: Tkinter rendering position/visual/theme-following cannot be verified by grep/unit tests (flagged in VALIDATION.md and 06-01-SUMMARY.md as manual-only).
2. **Mousewheel feel + low-resolution dialog display** — Confirm mousewheel scrolling works on the plugin list (including after "🔄 再検出"), and that the OCR dialog does not overflow the screen on a short/low-resolution display. Why human: automated tests verify the binding state and geometry math but not actual wheel-event delivery through the real Tk event loop/widget hierarchy or real display constraints (flagged as human_judgment: true in 06-02-SUMMARY.md coverage D3/D4, and in 06-SCROLL-FONT-AUDIT.md §1.4 as structurally untestable).

### Gaps Summary

No gaps found. All must-have truths (roadmap Success Criteria + plan-level D-01〜D-17/R1/WR-01〜03) are verified via direct code reads, independent test re-runs (not trusting SUMMARY claims), and cross-checks against git history (e.g., v1.6.1 tag date independently confirmed to match the corrected 開発履歴.md date). The only open items are the two human-verification checks above, which are inherent visual/real-time behaviors that no automated check in this codebase can settle — this is expected and does not indicate incomplete work.

---

_Verified: 2026-07-16_
_Verifier: Claude (gsd-verifier)_
