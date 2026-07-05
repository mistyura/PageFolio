---
phase: 04-ui-ux
plan: 02
subsystem: ui
tags: [tkinter, keyboard-shortcuts, dialogs, i18n]

# Dependency graph
requires:
  - phase: 04-01
    provides: "build_keysym_from_event / find_duplicate_binding / keysym_to_display 純関数（app.py）と再実行可能な _bind_shortcuts() / self._cmd_map / self._default_shortcuts"
provides:
  - "ShortcutsDialog（pagefolio/dialogs/shortcuts.py）— cmd_map 全11コマンドの実キーキャプチャ編集・保存時重複拒否・無効化・全体リセット"
  - "SettingsDialog の外観/操作/AI・OCR 3セクション再編と app 参照配線（_open_shortcuts_dialog）"
  - "settings_lm_studio_section 等 🔍→⚙ アイコン改称（C8）"
affects: [04-ui-ux 後続プラン（V171-UIUX-02 文言監査等）]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ダイアログ共通骨格（parent/font_func/lang → grab_set → _build → 中央配置）を踏襲した新規 Toplevel ダイアログ"
    - "app 参照を持たない既存ダイアログ（SettingsDialog）へ後方互換の任意引数追加で app 参照を配線するパターン"

key-files:
  created:
    - pagefolio/dialogs/shortcuts.py
  modified:
    - pagefolio/dialogs/settings.py
    - pagefolio/dialogs/__init__.py
    - pagefolio/lang.py
    - pagefolio/app.py
    - CLAUDE.md

key-decisions:
  - "ShortcutsDialog は保存前は self._shortcuts という一時コピーのみを編集し、保存ボタンを押すまで app.settings / 実バインドへ反映しない（キャンセルで無効化）"
  - "保存時は (a) 全体重複再検査 → (b) 既定と異なる項目のみを settings['shortcuts'] へ完全置換 → (c) app._bind_shortcuts() → (d) _save_settings の順で1本道にする"
  - "SettingsDialog.__init__ に後方互換の app=None を追加し、_open_settings（app.py）から app=self を渡す（既存の位置引数の並びは変更なし）"

requirements-completed: [V171-UIUX-01, V171-UIUX-03]

coverage:
  - id: D1
    description: "ShortcutsDialog が新設され、cmd_map 全11コマンドを実キーキャプチャで編集・保存・即時反映できる"
    requirement: "V171-UIUX-01"
    verification:
      - kind: unit
        ref: "python -c import/AST 検証（class ShortcutsDialog 存在・re-export・find_duplicate_binding 参照確認）"
        status: pass
      - kind: manual_procedural
        ref: "実キー入力→保存→即時反映の目視確認（VERIFICATION.md Manual-Only 項目）"
        status: unknown
    human_judgment: true
    rationale: "実 Tk ウィジェット生成・event_generate を使うテストが既存スイートに存在しないため、実キー入力の目視確認は自動化できない（04-RESEARCH.md で確認済み）"
  - id: D2
    description: "SettingsDialog が外観/操作/AI・OCR の3セクション構成となり、旧「LM Studio (OCR)」見出しと🔍アイコンが⚙系へ改称される"
    requirement: "V171-UIUX-03"
    verification:
      - kind: unit
        ref: "pytest tests/test_provider_ui.py -x -q"
        status: pass
      - kind: unit
        ref: "pytest tests/test_lang_parity.py -x -q"
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-07-05
status: complete
---

# Phase 4 Plan 2: ショートカット GUI 編集完成 + SettingsDialog セクション再編 Summary

**新設 ShortcutsDialog で cmd_map 全11コマンドを実キーキャプチャ編集・保存時重複拒否可能にし、SettingsDialog を外観/操作/AI・OCR の3セクションへ再編・🔍→⚙アイコン改称**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-05T09:47:00Z
- **Completed:** 2026-07-05T09:59:00Z
- **Tasks:** 3
- **Files modified:** 6 (新規1・修正5)

## Accomplishments
- `pagefolio/dialogs/shortcuts.py` を新設し `ShortcutsDialog(tk.Toplevel)` を実装。cmd_map の全11コマンド（open_file/save_file/undo/redo/save_as/delete/toggle_mode/print_pdf/rotate_right/rotate_left/rotate_180）を一覧表示し、「変更」で実キーキャプチャ（修飾キー単体は確定せず継続待機・Escでキャンセル）、「解除」で無効化、「既定に戻す」で全体リセットできる
- 保存時は全体重複を `find_duplicate_binding` で再検査 → 拒否時は衝突コマンド名を含むエラー表示 → 問題なければ既定と異なる項目のみ `app.settings["shortcuts"]` へ差分格納 → `app._bind_shortcuts()` で即時反映 → `_save_settings` で永続化、の一本道を実装
- `SettingsDialog` を「外観（テーマ/フォント）」「操作（ショートカット）」「AI・OCR」の3セクション構成へ再編し、「操作」セクションに「⌨ ショートカット設定…」ボタン（`_open_shortcuts_dialog`・二重起動ガード付き）を追加
- `SettingsDialog.__init__` に後方互換の `app=None` 引数を追加し、`app.py._open_settings` から `app=self` を渡すことで ShortcutsDialog が `_cmd_map`/`_default_shortcuts`/`_bind_shortcuts` を参照できるようにした
- `settings_lm_studio_section`（旧「🔍 LM Studio (OCR)」→「⚙ AI・OCR 設定」）・`settings_open_llm_config`・`llm_config_heading` の🔍アイコンを⚙系へ改称（C8。既存 `settings_heading`="⚙ 設定" とのアイコン統一）
- ShortcutsDialog 用の全文言（タイトル・11コマンド表示名・列見出し・各操作ボタン・重複エラー・未割当プレースホルダ）と `settings_section_appearance`/`settings_section_operation`/`settings_open_shortcuts` を ja/en 両辞書へ同時追加
- `dialogs/__init__.py` へ `ShortcutsDialog` を re-export・CLAUDE.md のファイル構成表へ `dialogs/shortcuts.py` の1行を追加

## Task Commits

Each task was committed atomically:

1. **Task 1: ShortcutsDialog（実キーキャプチャ編集ダイアログ）を新設** - `9adcf3f` (feat)
2. **Task 2: SettingsDialog を3セクション再編しショートカットボタンを追加** - `2c0eff9` (feat)
3. **Task 3: lang.py に ShortcutsDialog 文言と改称見出しキーを ja/en 同時追加** - `2d74797` (docs)

## Files Created/Modified
- `pagefolio/dialogs/shortcuts.py` - 新規。`ShortcutsDialog(tk.Toplevel)`。実キーキャプチャ・重複検出・無効化・全体リセット・差分保存・即時再バインド
- `pagefolio/dialogs/settings.py` - `_build` を3セクション再編・`_open_shortcuts_dialog` 新設・`__init__` に `app` 引数追加
- `pagefolio/dialogs/__init__.py` - `ShortcutsDialog` の re-export 追加
- `pagefolio/lang.py` - ShortcutsDialog 文言・セクション見出しキー・🔍→⚙ 改称キーを ja/en 同時追加
- `pagefolio/app.py` - `_open_settings` の `SettingsDialog(...)` 呼び出しへ `app=self` を追加（Rule 2 deviation。下記参照）
- `CLAUDE.md` - ファイル構成表へ `dialogs/shortcuts.py` の1行を追加

## Decisions Made
- ShortcutsDialog は保存前状態を `self._shortcuts`（working copy）に閉じ込め、キャンセル時は app へ一切影響しないようにした（安全なプレビュー編集）
- 差分保存は「現在の全11コマンド状態」から「既定と異なるもののみ」を都度再計算して `settings["shortcuts"]` を完全置換する方式にした（マージではなく置換）。これにより全体リセット後の保存で不要な旧差分が settings に残留しない
- 個別「解除」は既定キーがあるコマンドでは `""` を明示的に差分として保存する（無効化を表現するために必要。マージ時 `if func and keysym` の keysym="" 判定で自然にバインドされない）
- SettingsDialog への `app` 引数は既存の位置引数順序を変えずキーワード専用の新規任意引数として追加し、既存呼び出し元（テストの SimpleNamespace スタブ含む）との後方互換を維持した

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] `app.py._open_settings` に `app=self` を追加**
- **Found during:** Task 2（SettingsDialog セクション再編）
- **Issue:** plan の frontmatter `files_modified` には `pagefolio/app.py` が含まれておらず、Task 2 の action 文言も「SettingsDialog.__init__ に任意引数を追加してよい」という記述に留まっていたが、実際に `SettingsDialog` を構築している唯一の本番呼び出し元（`app.py:560` `_open_settings`）を更新しない限り、`SettingsDialog._app` は常に `None` のままとなり、「⌨ ショートカット設定…」ボタンから ShortcutsDialog を開く機能が本番コードで一切動作しない（V171-UIUX-01 の成功基準そのものが達成できない）
- **Fix:** `app.py._open_settings` 内の `SettingsDialog(...)` 呼び出しへ `app=self` を追加（既存の位置引数は変更なし）
- **Files modified:** `pagefolio/app.py`
- **Verification:** `ruff check`/`ruff format --check` クリーン・`pytest tests/test_provider_ui.py -x -q`（`TestOpenSettingsDoubleLaunchGuard` 含む既存回帰）グリーン・`pytest` フルスイート845件グリーン
- **Committed in:** `2c0eff9`（Task 2 commit）

---

**Total deviations:** 1 auto-fixed（Rule 2 — missing critical functionality）
**Impact on plan:** ShortcutsDialog を本番導線から実際に開けるようにするために必須の配線。スコープ拡大ではなく、plan が意図した機能（V171-UIUX-01 成功基準1）を成立させるための不可欠な補完。

## Issues Encountered
None - ruff format の自動整形（Task 1 の `shortcuts.py` 内 1 行が Task 3 のフォーマットチェックで整形対象と判明・整形後も全テストグリーン再確認済み）以外は計画通り。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V171-UIUX-01（ショートカット GUI 編集）・V171-UIUX-03（SettingsDialog セクション再編・C8）は本プランで完成
- 実キー入力→保存→即時反映の目視確認は VERIFICATION.md の Manual-Only 項目として記録が必要（04-RESEARCH.md D-20・既存 human-verify 運用と同じ）
- 04-RESEARCH.md の棚卸し確定表（C2/C4/C5/C6/C7・V171-UIUX-02/V171-TEST-03 相当）は本プランの対象外（別プランの担当範囲）のため次プランへ継続
- ブロッカーなし。フルスイート845件グリーン・ruffクリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED
