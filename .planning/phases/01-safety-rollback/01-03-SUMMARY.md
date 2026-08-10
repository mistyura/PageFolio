---
phase: 01-safety-rollback
plan: 03
subsystem: ui
tags: [tkinter, settings-dialog, prompt-templates, apply-cancel-contract, regression-tests]

# Dependency graph
requires:
  - phase: 01-safety-rollback
    provides: "01-01（保存経路の暗号化維持）とはファイル面が独立。01-02（OCR OFF ガード全経路一貫化）とも独立"
provides:
  - "sections.py:_on_template_change から外部プロンプトファイルへの即時書き込みを撤去（D-15）。書き込みは dialog.py:_apply の1経路のみ"
  - "sections.py:_has_unsaved_template_changes は prompt_file_exists による早期 False 分岐を撤去し、アクティブテンプレート選択済みなら常に保存済み値と比較する単一経路（D-18）"
  - "TestApplyOnlyPromptFileWrite（6件）・TestUnsavedTemplateChangesSinglePath（3件）の新規回帰テストで V190-CFG-01/02 の契約を実ファイル検証込みで固定"
affects: [01-04, 01-05]

actuals:
  tokens: 5504
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "外部ファイルI/Oを伴うUI状態遷移は「書き込みトリガーを1箇所（Apply）へ集約し、他のイベントハンドラは副作用を持たない」設計にする（D-15/D-16/D-17）"
    - "未保存差分判定のような分岐を持つ判定関数は、外部リソースの有無で判定経路を分けない（D-18・同型バグの再発防止）"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config/sections.py
    - tests/test_provider_ui.py

key-decisions:
  - "D-15: sections.py:_on_template_change の save_prompt_file 即時呼び出し2箇所を削除し、外部プロンプトファイルへの書き込みを dialog.py:_apply の1経路へ一本化した。dialog.py 自体は無改造（既に正しい参照実装だったため）"
  - "D-18: _has_unsaved_template_changes から prompt_file_exists による早期 False 分岐（1ブロック）のみを削除し、未選択時ロジック（if not self._active_template_name）には触れない最小差分にした（Pitfall 5 回避）"
  - "テストの書き込み監視は sections.py 側のシンボル（撤去済み）ではなく pagefolio.settings.save_prompt_file を横断的にモニタするスタブへ統一した"

requirements-completed: [V190-CFG-01, V190-CFG-02]

coverage:
  - id: D1
    description: "テンプレート切替では外部プロンプトファイル（ocr_custom_prompt.md/ocr_summary_prompt.md）へ一切書き込まれない（複数回切替・Cancel・開く→Cancelの反復いずれも不変）"
    requirement: "V190-CFG-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite::test_template_change_does_not_write_prompt_files"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite::test_cancel_leaves_prompt_files_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite::test_open_cancel_twice_leaves_files_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateChangeFlow::test_change_leaves_external_md_file_untouched"
        status: pass
    human_judgment: false
  - id: D2
    description: "Apply が書き込む内容は入力欄の現在値であり、アクティブテンプレートの保存済み値でも外部エディタでの直近編集内容でもない（Apply が最後の書き手）"
    requirement: "V190-CFG-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite::test_apply_writes_input_field_content_not_active_template"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite::test_apply_overwrites_externally_edited_file_with_input_content"
        status: pass
    human_judgment: false
  - id: D3
    description: "外部プロンプトファイルが存在しない場合、Apply しても新規作成しない（オプトイン仕様の維持）"
    requirement: "V190-CFG-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApplyOnlyPromptFileWrite::test_apply_does_not_create_missing_prompt_files"
        status: pass
    human_judgment: false
  - id: D4
    description: "アクティブテンプレート選択済みの状態で入力欄を編集して別テンプレートへ切り替えると、外部ファイルの有無にかかわらず未保存確認ダイアログが表示される"
    requirement: "V190-CFG-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestUnsavedTemplateChangesSinglePath::test_selected_template_edit_warns_without_prompt_files"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestUnsavedTemplateChangesSinglePath::test_selected_template_unedited_does_not_warn"
        status: pass
    human_judgment: false
  - id: D5
    description: "未保存確認で「いいえ」を選ぶと、選択が元のアクティブテンプレートへ戻り入力欄の内容も保持される（未選択時の既存挙動も回帰なし）"
    requirement: "V190-CFG-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestUnsavedTemplateChangesSinglePath::test_switch_cancel_restores_active_template_selection"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateChangeFlow::test_no_active_template_warns_on_unsaved_freeform_text"
        status: pass
    human_judgment: false

duration: 約20min
completed: 2026-08-10
status: complete
---

# Phase 1 Plan 3: LLM 設定ダイアログの Apply/Cancel 契約整合 Summary

**外部プロンプトファイルへの書き込みを Apply 押下時の1経路へ一本化し、テンプレート切替の未保存確認をファイル連動有無に依存しない単一判定経路へ統一した**

## Performance

- **Duration:** 約20分
- **Tasks:** 3/3
- **Files modified:** 2

## Accomplishments
- `sections.py:_on_template_change` から `save_prompt_file()` の即時書き込み2箇所（CUSTOM_PROMPT_FILE/SUMMARY_PROMPT_FILE）を撤去し、外部プロンプトファイルへの書き込みを `dialog.py:_apply` の1経路へ一本化した（D-15）。`dialog.py` 自体は既に正しい実装だったため無改造
- `_has_unsaved_template_changes` から `prompt_file_exists()` による早期 False 分岐を削除し、アクティブテンプレート選択済みの場合は常に入力欄と `get_template()` の保存済み値を比較する単一経路にした（D-18）。未選択時ロジック（自由入力の有無だけを見る分岐）には一切触れていない
- 未使用となった `prompt_file_exists`/`save_prompt_file` の import を `sections.py` から除去（`CUSTOM_PROMPT_FILE`/`SUMMARY_PROMPT_FILE` は他箇所で使用中のため維持）
- `TestTemplateChangeFlow` の既存4テストを更新: 旧ライブ連動挙動（切替の都度ファイル上書き）を検証していた2テストを「書き込みが発生しないことの検証」へ反転し改名。書き込み監視は撤去済みシンボルではなく `pagefolio.settings.save_prompt_file` を横断モニタするスタブへ統一
- `TestApplyOnlyPromptFileWrite`（6件）・`TestUnsavedTemplateChangesSinglePath`（3件）を新設し、「Cancel は外部ファイルを変えない」「Apply は入力欄の現在値を書く」「存在しないファイルは作らない」「外部編集を Apply が上書きする」「開く→Cancel の反復で不変」「選択済みテンプレート編集は常に未保存確認が出る」の各契約を実ファイル検証込みで固定
- フルテストスイート（1139件）・ruff（`ruff check .` / `ruff format --check .`）ともにグリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: テンプレート切替の即時書き込み撤去と未保存判定の単一経路化（D-15・D-16・D-17・D-18）** - `725f665` (refactor)
2. **Task 2: 旧ライブ連動挙動を検証していた既存テスト4件の更新（D-15・D-16）** - `dc9b1c0` (test)
3. **Task 3: Apply一本化契約と未保存確認の新規回帰テスト整備（V190-CFG-01・V190-CFG-02）** - `56a4520` (test)

**Plan metadata:** このコミット（本 SUMMARY + STATE.md + ROADMAP.md）

## Files Created/Modified
- `pagefolio/dialogs/llm_config/sections.py` - `_on_template_change`/`_has_unsaved_template_changes` の副作用除去と判定経路の単一化、docstring 更新、未使用 import 除去
- `tests/test_provider_ui.py` - `TestTemplateChangeFlow` 4テストの更新（うち2件改名・反転）、`TestApplyOnlyPromptFileWrite`（6件）・`TestUnsavedTemplateChangesSinglePath`（3件）の新設

## Decisions Made
- D-15: 外部プロンプトファイルへの書き込みは `dialog.py:_apply` の唯一の経路へ一本化。ライブ連動＋Cancel復元案は不採用（REQUIREMENTS.md Out of Scope）
- D-18: `_has_unsaved_template_changes` の判定経路を1本化。外部ファイル内容を基準に加える案は判定経路が2本に戻るため不採用
- D-19: i18n（`pagefolio/lang.py`）と外部ファイルに関する注記文言は無改造（`git diff --stat pagefolio/lang.py` が空であることを確認済み）
- テストの書き込み監視先を `pagefolio.dialogs.llm_config.sections.save_prompt_file`（撤去済み・存在しない）から `pagefolio.settings.save_prompt_file`（実体）へ切り替え、テストが「実際に呼ばれるべき唯一の経路」を監視する形にした

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- V190-CFG-01・V190-CFG-02 の受け入れ条件（Cancel は外部ファイルを変えない・Apply は入力欄の現在値を書く・存在しないファイルは作らない・選択済みテンプレート編集は常に未保存確認が出る）を満たした
- `dialog.py` の Apply ハンドラと `pagefolio/lang.py` は無改造のため、後続プラン（01-04・01-05）が本プランの変更と衝突する余地はない（`page_ops.py`/`file_ops.py` 側のロールバック方式を扱うため対象ファイルも独立）

---
*Phase: 01-safety-rollback*
*Completed: 2026-08-10*
