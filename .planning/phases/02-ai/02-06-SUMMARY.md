---
phase: 02-ai
plan: 06
subsystem: testing
tags: [tkinter, llm-config-dialog, prompt-templates, headless-testing, pytest]

# Dependency graph
requires:
  - phase: 02-ai (plan 05)
    provides: "テンプレート CRUD の Apply/Cancel 契約回復（CR-02 修正）・_SetGetVarStub・_on_template_delete への askyesno 削除確認"
provides:
  - "_make_template_dialog（LLMConfigDialog.__new__ + 属性注入によるheadlessダイアログヘルパー）"
  - "_FakeTemplateText/_FakeCombo（tk.Text/ttk.Combobox 相当の軽量スタブ）"
  - "TestTemplateChangeFlow（D-05/D-07: _on_template_change の切替中止・外部md上書きを実bound method呼び出しで実証）"
  - "TestTemplateNameValidationUI（D-04: _on_template_save/_on_template_rename の重複名/空名 showerror 拒否をUI経由で実証）"
  - "TestTemplateDeleteButtonState（D-03: _refresh_template_delete_state の disabled/!disabled 切替を実証）"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "既存の _ButtonStub（OCR-UI-02 節）・_SetGetVarStub（02-05 節）を新規UIハンドラテストでも再利用し、Text/Combobox のみ新規スタブを追加する（重複定義を避ける最小追加の方針）"
    - "LLMConfigDialog.__new__ + 属性注入によるheadlessダイアログテスト（tests/test_ocr_fallback.py の _make_dialog パターン）をテンプレートUIハンドラ層へ同型移植"

key-files:
  created: []
  modified:
    - tests/test_provider_ui.py

key-decisions:
  - "D-07 の検証を『フェイク捕捉（save_prompt_file 呼び出し引数の記録）』と『tmp_path 実ファイル読み取り』の二段構えにし、02-VERIFICATION.md behavior_unverified_items[1] の test 欄が要求する実I/O検証を満たした（settings._get_base_dir のみ monkeypatch し prompt_file_exists/save_prompt_file/load_prompt_file は実関数のまま通す）"
  - "新設スタブは Text（_FakeTemplateText）・Combobox（_FakeCombo）のみに限定し、set/get var スタブは 02-05 で新設済みの _SetGetVarStub を、Button スタブは既存の _ButtonStub（OCR-UI-02 節）をそのまま再利用した（plan の artifacts_produced は新規命名を例示していたが、既存スタブが同一インターフェースを満たすため重複定義を避けた）"

patterns-established:
  - "テンプレートUIハンドラのheadlessテストは _make_template_dialog 経由で LLMConfigDialog インスタンスを作り、current_settings/template_var/ocr_prompt_text 等の必要属性のみを注入する。以後のテンプレート関連UIハンドラ追加時もこのヘルパーを拡張して使う"

requirements-completed: [V180-TMPL-02, V180-TMPL-03, V180-TMPL-04]

coverage:
  - id: D1
    description: "_on_template_change は外部mdファイル連動モードで未保存差分がある場合 askyesno を呼び、No応答で切替を中止しtemplate_varをアクティブテンプレートへ戻し入力欄を変化させない（D-05）"
    requirement: "V180-TMPL-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateChangeFlow::test_cancel_discards_switch_and_keeps_edited_content"
        status: pass
    human_judgment: false
  - id: D2
    description: "_on_template_change は切替確定後、外部mdファイルを新アクティブテンプレートの内容で上書きする（D-07・フェイク捕捉+tmp_path実ファイル検証の両方）"
    requirement: "V180-TMPL-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateChangeFlow::test_confirmed_switch_overwrites_external_files_fake_capture"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateChangeFlow::test_change_overwrites_external_md_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "_on_template_save/_on_template_rename は既存名入力時に showerror を呼び save_template/rename_template を呼ばない（D-04・UI経由）"
    requirement: "V180-TMPL-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateNameValidationUI::test_save_rejects_duplicate_name"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateNameValidationUI::test_save_rejects_empty_name"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateNameValidationUI::test_rename_rejects_duplicate_name"
        status: pass
    human_judgment: false
  - id: D4
    description: "_refresh_template_delete_state はアクティブテンプレート選択時に template_delete_btn へ disabled を、非アクティブ選択時に !disabled を設定する（D-03・UI経由）"
    requirement: "V180-TMPL-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateDeleteButtonState::test_active_selection_disables_delete_button"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateDeleteButtonState::test_inactive_selection_enables_delete_button"
        status: pass
    human_judgment: false

duration: 約15分
completed: 2026-07-14
status: complete
---

# Phase 02 Plan 06: テンプレートUIハンドラ層の behavior_unverified_items 解消 Summary

**LLMConfigDialog.__new__ + 実bound method呼び出しによるheadlessテストで、02-VERIFICATION.mdのbehavior_unverified_items 4件（D-03削除ボタン無効化・D-04重複名拒否・D-05切替中止・D-07外部md上書き）を全て自動テストへ移行**

## Performance

- **Duration:** 約15分
- **Tasks:** 2
- **Files modified:** 1（tests/test_provider_ui.py）

## Accomplishments

- `_make_template_dialog` ヘルパー（`LLMConfigDialog.__new__` + 属性注入・`tests/test_ocr_fallback.py::_make_dialog` と同型）を新設し、Tk 生成なしでテンプレートUIハンドラを実bound method呼び出しで駆動できるようにした
- `_FakeTemplateText`（tk.Text の get/delete/insert 相当）・`_FakeCombo`（ttk.Combobox の configure(values=...) 相当）を新設。既存の `_SetGetVarStub`（02-05）・`_ButtonStub`（OCR-UI-02）はそのまま再利用した
- `TestTemplateChangeFlow` を新設し、`_on_template_change` の D-05（未保存差分ありで askyesno=False → 切替中止・template_var 復元・入力欄不変・save_prompt_file 非呼出）と D-07（切替確定後の外部md上書き）を実証。D-07 はフェイク捕捉版に加え、`settings._get_base_dir` のみ monkeypatch して `prompt_file_exists`/`save_prompt_file`/`load_prompt_file` を実関数のまま通す `tmp_path` 実ファイル読み取り検証版も追加し、02-VERIFICATION.md の test 欄が要求する実I/O検証を満たした
- `TestTemplateNameValidationUI` を新設し、`_on_template_save`（重複名・空名）/`_on_template_rename`（重複名）の `messagebox.showerror` 拒否経路をUI経由で実証（D-04）
- `TestTemplateDeleteButtonState` を新設し、`_refresh_template_delete_state` のアクティブ/非アクティブ選択時の `disabled`/`!disabled` 切替を実証（D-03）
- フルスイート986件グリーン（8件純増）・ruff クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: headlessテンプレートダイアログスタブとD-05/D-07切替フローテストを追加** - `4b3a368` (test)
2. **Task 2: D-04重複名showerror拒否とD-03削除ボタン無効化のUIハンドラテストを追加** - `7d03d41` (test)

## Files Created/Modified

- `tests/test_provider_ui.py` - `_FakeTemplateText`・`_FakeCombo`・`_make_template_dialog`・`TestTemplateChangeFlow`（Task 1）・`TestTemplateNameValidationUI`・`TestTemplateDeleteButtonState`（Task 2）を追加

## Decisions Made

- D-07 の検証を「フェイク捕捉」と「`tmp_path` 実ファイル読み取り」の二段構えにした。02-VERIFICATION.md の behavior_unverified_items[1] の `test` 欄が「ファイル内容が新アクティブテンプレート内容で上書きされていることをファイル読み取りで確認する」ことを明示的に要求していたため、モック検証だけでは不十分と判断し実I/O検証を追加した
- 新設スタブは Text・Combobox のみに限定し、var/Button スタブは既存の `_SetGetVarStub`（02-05 で新設済み）・`_ButtonStub`（OCR-UI-02 節で新設済み）をそのまま再利用した。plan の `artifacts_produced` は新規命名（`_FakeButton` 等）を例示していたが、既存スタブが完全に同一インターフェースを満たしていたため重複定義を避けた（受入基準の「新設スタブ（set/get var・Text・Button・Combobox 相当）が追加されている」は、Text/Combobox の新設 + var/Button の既存流用という形で意図を満たしている）

## Deviations from Plan

None - plan executed as written（スタブ再利用の判断は上記 Decisions Made に記載の実装上の選択であり、must_haves の behavior assertion にはすべて実 bound method 呼び出しテストで応えている）。

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 02-VERIFICATION.md の `behavior_unverified_items`（4件・D-03/D-04/D-05/D-07）が全て実bound-methodテストでカバーされ、human_verification の該当3項目（テンプレート切替・重複名拒否・削除ボタン無効化）は自動テストへ移行した
- テンプレート UI ハンドラ層のカバレッジ非対称（フォールバック側 02-04 との差）が解消された
- CR-02（02-05 で解消済み）と本プランの behavior_unverified_items 解消により、02-VERIFICATION.md の gaps（BLOCKER 1件・behavior_unverified 3件）は両方とも解消済み。Phase 2 の再検証（`/gsd-verify-work` 等）で `gaps_found` から `passed` への遷移が期待される
- CR-01（Tesseract 未インストール時の `_last_valid_provider` 初期化バグ）は本プランのスコープ外のまま未対応（02-VERIFICATION.md の gaps に非計上・別件推奨として引き続き記録）
- ブロッカーなし。フルスイート986件グリーン・ruff クリーン

---
*Phase: 02-ai*
*Completed: 2026-07-14*
