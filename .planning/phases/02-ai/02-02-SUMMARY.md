---
phase: 02-ai
plan: 02
subsystem: ui
tags: [tkinter, llm-config-dialog, prompt-templates, settings-json, pytest]

# Dependency graph
requires:
  - phase: 02-ai (plan 01)
    provides: "settings.py のテンプレート CRUD 純関数群（save/get/list/delete/rename/exists）・load_custom_prompt/load_summary_prompt の3段解決"
provides:
  - "LLM 設定ダイアログの📄テンプレートセクション（combobox選択＋保存/削除/リネームボタン）"
  - "_on_template_change による D-05（未保存差分確認）/ D-07（外部mdファイル書き戻し）フロー"
  - "_apply による active テンプレート名の収集（items 保持のまま永続化）"
affects: [02-03, 02-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "provider_combo と同型の readonly Combobox + <<ComboboxSelected>> バインドをテンプレート選択欄に複製"
    - "ShortcutsDialog._on_save の保存時重複拒否パターン（showerror→return）をテンプレート名検証に複製"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config/sections.py
    - pagefolio/dialogs/llm_config/dialog.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py

key-decisions:
  - "D-01: テンプレート選択欄1つでカスタム/サマリ両方が同時に切り替わる（ペア保存）"
  - "D-03: 削除ボタンは _refresh_template_delete_state でアクティブテンプレート選択時に disabled。settings.delete_template の ValueError による二重防御と合わせて機械的に強制"
  - "D-05: _has_unsaved_template_changes は外部mdファイル連動モード（prompt_file_exists）のときのみ比較を行い、非連動モードでは常に False（確認ダイアログを出さない）"
  - "D-07: テンプレート切替後は選択テンプレートの内容で外部mdファイルを常に上書きし『アクティブテンプレートのライブ編集内容』の不変条件を維持"
  - "_apply の prompt_templates 収集は getattr フォールバックで既存の _apply スタブ経路（current_settings/_active_template_name 未設定）との後方互換を保持"

patterns-established:
  - "_reload_template_combo(select_name) で combobox values 再読込 + 選択状態 + 削除ボタン活性の3点を1箇所に集約"

requirements-completed: [V180-TMPL-01, V180-TMPL-02, V180-TMPL-03, V180-TMPL-04, V180-TMPL-05]

coverage:
  - id: D1
    description: "sections.py に📄テンプレートセクション（combobox選択＋保存/削除/リネームボタン）を追加し、02-01のCRUD純関数をUIから呼ぶ"
    requirement: "V180-TMPL-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateSection::test_template_combo_referenced_in_sections_source"
        status: pass
    human_judgment: false
  - id: D2
    description: "combobox の <<ComboboxSelected>> でテンプレート切替（一覧選択）ができる"
    requirement: "V180-TMPL-02"
    verification:
      - kind: unit
        ref: "grep -c 'template_combo' pagefolio/dialogs/llm_config/sections.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "テンプレート名の重複/空名は保存・リネーム時に showerror で拒否（D-04）。アクティブテンプレートの削除ボタンは無効化（D-03）"
    requirement: "V180-TMPL-03"
    verification:
      - kind: unit
        ref: "tests/test_prompt_templates.py::TestDeleteRename（02-01 で settings.py 側は検証済み。本プランは UI 経路の source-scan で接続を確認）"
        status: pass
    human_judgment: false
  - id: D4
    description: "テンプレート切替時、外部mdファイル連動モードでは未保存差分確認（askyesno）を挟みキャンセルで中止（D-05）。切替後は選択テンプレートの内容で外部mdファイルを上書き（D-07）"
    requirement: "V180-TMPL-04"
    verification:
      - kind: unit
        ref: "コードレビュー（_on_template_change/_has_unsaved_template_changes の実装内容確認）。Tk 生成を伴う askyesno モックテストは未実装（Deferred Issues 参照）"
        status: unknown
    human_judgment: true
    rationale: "_on_template_change は _build() 実行後の Tk ウィジェット（ocr_prompt_text 等）に依存するため、既存の _apply スタブ方式のような非バインドメソッド単体呼び出しでは容易に検証できない。実機/統合テストでの確認が望ましい"
  - id: D5
    description: "_apply が prompt_templates の active を収集し items を保持したまま永続化。load_custom_prompt/load_summary_prompt 経由で全プロバイダ共有される"
    requirement: "V180-TMPL-05"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateSection::test_apply_collects_active_template_preserving_items"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateSection::test_save_template_then_load_custom_prompt_resolves"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateSection::test_save_template_then_load_summary_prompt_resolves"
        status: pass
    human_judgment: false

duration: 約20min
completed: 2026-07-14
status: complete
---

# Phase 02 Plan 02: LLM 設定ダイアログへのテンプレート管理 UI 追加 Summary

**sections.py に📄テンプレートセクション（combobox選択＋保存/削除/リネーム）を追加し、_on_template_change でD-05〜D-07の未保存差分確認/外部mdファイル書き戻しフローを実装、_apply でactiveテンプレート名をitems保持のまま収集**

## Performance

- **Duration:** 約20分
- **Started:** 2026-07-14（Task 1 コミット直前）
- **Completed:** 2026-07-14
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `sections.py` の `_build` にカスタムプロンプト入力欄の直前へテンプレートセクション（`template_combo` + 保存/削除/リネームの3ボタン）を挿入。02-01 の CRUD 純関数（`list_template_names`/`get_template`/`save_template`/`delete_template`/`rename_template`/`template_name_exists`）を UI から呼び出す経路を接続
- `_on_template_change` に D-05（外部mdファイル連動モードのみ未保存差分を `askyesno` で確認・キャンセルで切替中止）→ D-07（切替後に選択テンプレートの内容で外部mdファイルを上書き）の3手順フローを実装
- `_on_template_save`/`_on_template_delete`/`_on_template_rename` に ShortcutsDialog 型の重複/空名拒否（D-04）とアクティブテンプレート削除拒否（D-03・二重防御）を実装
- `dialog.py` の `_apply` に `prompt_templates`（active + items）の収集を追加。items は `self.current_settings` 由来のコピーを保持したまま active のみ現在の選択値で差し替える。既存の `_apply` スタブ経路（`current_settings`/`_active_template_name` 未設定）は `getattr` フォールバックで後方互換を保持
- `lang.py` に `tmpl_*` キー9個を ja/en 同一キーで追加（キー数左右一致を維持）
- `tests/test_provider_ui.py` に `TestTemplateSection`（5件: source-scan・純ロジック連携2件・`_apply` 収集検証2件）を追加。フルスイート956件グリーン・ruff クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: sections.py にテンプレートセクション（combobox + 保存/削除/リネーム + 切替フロー）を追加** - `c8dec50` (feat)
2. **Task 2: dialog.py _apply にアクティブテンプレート名収集を追加し、test_provider_ui.py にテンプレートテストを追加** - `7aaac64` (feat)

## Files Created/Modified

- `pagefolio/dialogs/llm_config/sections.py` - テンプレートセクション UI（combobox + 3ボタン）+ 7メソッド（`_on_template_change`/`_on_template_save`/`_on_template_delete`/`_on_template_rename`/`_has_unsaved_template_changes`/`_reload_template_combo`/`_refresh_template_delete_state`）
- `pagefolio/dialogs/llm_config/dialog.py` - `_apply` に `prompt_templates`（active + items）収集を追加
- `pagefolio/lang.py` - `tmpl_*` キー9個を ja/en 同一キーで追加
- `tests/test_provider_ui.py` - `TestTemplateSection`（5件）を追加

## Decisions Made

- `_has_unsaved_template_changes` は外部mdファイル連動モード（`prompt_file_exists`）のときのみ比較を行い、非連動モードでは常に `False` を返す設計にした（must_haves の「外部mdファイル連動モードでは」の限定文言に厳密に整合させるため）
- テンプレート「保存」は常に新規名として重複拒否する設計にした（既存名への上書き更新は「リネーム」の責務とし、UI操作の意味を明確に分離）
- `_reload_template_combo(select_name)` を新設し、combobox values 再読込・選択状態設定・削除ボタン活性再評価の3点を1箇所に集約（CRUD 各ハンドラからの重複呼び出しを避けるため）

## Deviations from Plan

None - plan executed as written（PLAN.md の action 記述通りに実装。RESEARCH.md Pattern 3 のコード例をベースに `_has_unsaved_template_changes`/`_reload_template_combo`/`_refresh_template_delete_state` の3ヘルパーを追加した点は PLAN.md 内で明示的に指示されていた内容）。

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

なし。テンプレートセクションは 02-01 の実 CRUD 純関数へ直接接続されており、プレースホルダ/モックデータのハードコードはない。

## Next Phase Readiness

- テンプレート管理 UI（V180-TMPL-01〜05）が LLM 設定ダイアログに接続され、外部mdファイル連動（v1.7.4）との共存不変条件（D-05〜D-08）を満たした状態で完成
- D4（V180-TMPL-04・切替時の未保存差分確認/書き戻しフロー）は実装レビューでの確認に留まり、Tk ウィジェット生成を伴う `askyesno` モック統合テストは未実装（human_judgment: true として記録）。理由: `_on_template_change` は `_build()` 実行後の実 Tk ウィジェット（`ocr_prompt_text` 等）に依存するため、既存の非バインドメソッド単体スタブ方式では検証しづらい
- 02-03（フォールバック順設定UI）・02-04（フォールバックオーケストレーション）はこのプランに依存しない別セクション追加のため、並行着手可能
- ブロッカーなし

---
*Phase: 02-ai*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/llm_config/sections.py
- FOUND: pagefolio/dialogs/llm_config/dialog.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_provider_ui.py
- FOUND: .planning/phases/02-ai/02-02-SUMMARY.md
- FOUND: c8dec50 (Task 1 commit)
- FOUND: 7aaac64 (Task 2 commit)
