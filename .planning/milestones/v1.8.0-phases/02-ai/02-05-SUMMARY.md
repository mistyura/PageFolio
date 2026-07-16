---
phase: 02-ai
plan: 05
subsystem: ui
tags: [tkinter, llm-config-dialog, prompt-templates, apply-cancel-contract, pytest]

# Dependency graph
requires:
  - phase: 02-ai (plan 01)
    provides: "settings.py のテンプレート CRUD 純関数（save/get/list/delete/rename/exists）"
  - phase: 02-ai (plan 02)
    provides: "LLMConfigDialog の 📄テンプレートセクション（sections.py・dialog.py の _apply 収集）"
provides:
  - "LLMConfigDialog.__init__ が prompt_templates（active/items・各テンプレート dict まで）を copy.deepcopy で分離し、ダイアログ内 CRUD が app.settings を汚染しない不変条件"
  - "テンプレート保存/削除/リネームの永続化を Apply（_apply）経由の一括確定へ一本化（即時 _save_settings 除去）"
  - "_on_template_delete の削除前 askyesno 確認（誤削除防止）"
  - "lang.py の tmpl_delete_confirm（ja/en）"
  - "tests/test_provider_ui.py::TestTemplateCancelContract（CR-02 回帰4件）"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ネスト辞書（prompt_templates）を持つ設定オブジェクトをダイアログへ渡す際は、トップレベル浅コピー（dict()）に加えて対象ネストキーのみ copy.deepcopy で明示的に分離し、CRUD 操作の in-place 変更が呼び出し元オブジェクトへ伝播しないようにする（Apply/Cancel 契約を機械的に保証するパターン）"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config/dialog.py
    - pagefolio/dialogs/llm_config/sections.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py

key-decisions:
  - "CR-02 の修正方針は 02-REVIEW.md 対処案1（推奨: __init__ でのディープコピー分離）+ 対処案2（askyesno 削除確認）の両方を採用し、Apply 一括確定へ一本化することで安全性と使い勝手を両立させた"
  - "sections.py のコメントで _save_settings という具体的な識別子トークンを使うと source assertion（'sections.py 全体に _save_settings の残存参照が無い'）に抵触するため、コメント文言を「即時ディスク永続化を除去」という言い換えに統一した"
  - "テスト1（deepcopy 分離）は LLMConfigDialog.__init__ が実 Tk 親ウィジェットを要求し headless で直接呼べないため、dialog.py 実コードと同一の分離手順をテスト内で再現し不変条件をアサートする方式を採用。dialog.py 実ソースの copy.deepcopy 出現数を source assertion で補強した"

patterns-established:
  - "設定ダイアログのネスト辞書分離は __init__ 直後の1行（copy.deepcopy）で完結させ、CRUD ハンドラ側は変更対象辞書がどこから来たかを意識せずそのまま in-place 変更してよい設計にする（責務分離: 分離は入口で1回、CRUD は分離済みオブジェクトを信頼して操作）"

requirements-completed: [V180-TMPL-01, V180-TMPL-02, V180-TMPL-03]

coverage:
  - id: D1
    description: "LLMConfigDialog.__init__ で prompt_templates（active/items・各テンプレート dict）を app.settings からディープコピー分離する"
    requirement: "V180-TMPL-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateCancelContract::test_init_deepcopy_separates_prompt_templates_from_app_settings"
        status: pass
    human_judgment: false
  - id: D2
    description: "テンプレート保存/削除/リネームは Cancel（destroy のみ・on_apply 非呼出）で app.settings/ディスクへ一切反映されず、Apply で一括確定される"
    requirement: "V180-TMPL-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateCancelContract::test_cancel_does_not_mutate_app_settings_then_apply_commits_once"
        status: pass
    human_judgment: false
  - id: D3
    description: "sections.py の CRUD ハンドラ（保存/削除/リネーム）から即時 _save_settings 呼び出しが完全に除去されている（回帰防止）"
    requirement: "V180-TMPL-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateCancelContract::test_sections_source_has_no_save_settings_reference"
        status: pass
    human_judgment: false
  - id: D4
    description: "_on_template_delete は削除前に messagebox.askyesno の確認を出し、No 応答で delete_template を呼ばずに中止する（誤削除防止）"
    requirement: "V180-TMPL-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestTemplateCancelContract::test_on_template_delete_askyesno_no_aborts_yes_deletes"
        status: pass
    human_judgment: false

duration: 約20分
completed: 2026-07-14
status: complete
---

# Phase 02 Plan 05: テンプレート CRUD の Apply/Cancel 契約回復（CR-02 修正）Summary

**LLMConfigDialog.__init__ で prompt_templates をディープコピー分離し、sections.py の3 CRUD ハンドラから即時 _save_settings を除去して Apply 経由の一括確定へ一本化。_on_template_delete に askyesno 削除確認を追加し CR-02（Apply/Cancel 契約違反・データ消失リスク）を解消**

## Performance

- **Duration:** 約20分
- **Tasks:** 3
- **Files modified:** 4（pagefolio/dialogs/llm_config/dialog.py・pagefolio/dialogs/llm_config/sections.py・pagefolio/lang.py・tests/test_provider_ui.py）

## Accomplishments

- `LLMConfigDialog.__init__`（dialog.py）で `self.current_settings["prompt_templates"]` を `copy.deepcopy` して分離し、`app.settings["prompt_templates"]` との参照共有（items・各テンプレート dict まで）を完全に断った（02-REVIEW.md CR-02 の根本原因を解消）
- `_apply` の prompt_templates items 収集を `dict(...)`（エイリアスの可能性あり）から `copy.deepcopy(...)` へ変更し、on_apply 経由で `app.settings` へ渡る構造も内側まで独立させた（T-02-03 対応）
- `sections.py` の `_on_template_save`/`_on_template_delete`/`_on_template_rename` から即時ディスク永続化呼び出しを3箇所とも除去し、テンプレート CRUD の確定を Apply（`_apply`）経由の一括確定へ一本化した（未使用となった import も削除）
- `_on_template_delete` に削除前の `messagebox.askyesno` 確認を追加（02-REVIEW Fix 案2）。No 応答時は `delete_template` を呼ばず早期 return する
- `lang.py` に `tmpl_delete_confirm` を ja/en 同一キーで追加（`test_lang_parity.py` のキー数一致を維持）
- `tests/test_provider_ui.py` に `TestTemplateCancelContract`（4件）を新設: __init__ の deepcopy 分離不変条件・Cancel 非永続化 + Apply 一括確定・sections.py の即時永続化残存なし・delete askyesno No/Yes 分岐を、実際の bound method 呼び出しと source assertion で検証
- フルスイート978件グリーン（4件純増）・ruff クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: dialog.py で prompt_templates をディープコピー分離し _apply を一括確定へ整合させる** - `23a354f` (fix)
2. **Task 2: sections.py の3 CRUD ハンドラから即時 _save_settings を除去し、_on_template_delete に askyesno 削除確認を追加する** - `a841a17` (fix)
3. **Task 3: CR-02 回帰テスト（Cancel 非永続化・deepcopy 分離・delete 確認 No 中止）を test_provider_ui.py に追加する** - `aa7cf88` (test)

## Files Created/Modified

- `pagefolio/dialogs/llm_config/dialog.py` - `import copy` 追加。`__init__` で `prompt_templates` を `copy.deepcopy` して分離（Task 1）。`_apply` の items 収集を `copy.deepcopy` 化しコメントを新設計へ整合（Task 1）
- `pagefolio/dialogs/llm_config/sections.py` - `_on_template_save`/`_on_template_delete`/`_on_template_rename` から即時ディスク永続化呼び出しを除去（未使用 import も削除）。`_on_template_delete` に `askyesno` 削除確認を追加（Task 2）
- `pagefolio/lang.py` - `tmpl_delete_confirm` を ja/en 同一キーで追加（Task 2）
- `tests/test_provider_ui.py` - `TestTemplateCancelContract`（4件）・`_SetGetVarStub` を新設（Task 3）

## Decisions Made

- CR-02 の修正方針は 02-REVIEW.md の対処案1（ディープコピー分離・推奨）と対処案2（削除確認 askyesno）を両方採用し、「Apply 一括確定」という一般的なダイアログ契約へ完全準拠させた（片方のみの部分修正は選ばなかった）
- sections.py のコメント文言から `_save_settings` という具体的な識別子トークンを取り除き「即時ディスク永続化を除去」という言い換えへ統一した（plan の source assertion が `grep -q "_save_settings"` でコメント込みの完全不在を要求するため）
- Task 3 のテスト1（deepcopy 分離）は、`LLMConfigDialog.__init__` が実 Tk 親ウィジェットを要求し headless で直接呼べないため、dialog.py 実コードと同一の分離手順（`dict(current_settings)` 後に `prompt_templates` を `copy.deepcopy`）をテスト内で再現して不変条件そのものをアサートし、加えて dialog.py 実ソースの `copy.deepcopy` 出現数を source assertion で補強する二段構えとした

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] sections.py のコメント文言に `_save_settings` トークンが残存し source assertion に抵触**
- **Found during:** Task 3（`test_sections_source_has_no_save_settings_reference` 実行時）
- **Issue:** Task 2 で追加した3箇所のコメント（「CR-02 修正: 即時 `_save_settings` を除去」）が、除去を説明する目的で識別子トークンそのものを引用していたため、plan の受入基準（`sections.py` にコメント文字列含め `_save_settings` トークンが一切現れないこと）を満たさなくなっていた
- **Fix:** 3箇所のコメントを「即時ディスク永続化を除去」という言い換えへ統一し、識別子トークンを含まない表現に変更した
- **Files modified:** pagefolio/dialogs/llm_config/sections.py
- **Verification:** `! grep -q "_save_settings" pagefolio/dialogs/llm_config/sections.py` が真（終了コード0）になることを確認。`pytest tests/test_provider_ui.py::TestTemplateCancelContract -q` 4件グリーン再確認
- **Committed in:** aa7cf88（Task 3 コミット）

---

**Total deviations:** 1 auto-fixed（Rule 1 × 1）
**Impact on plan:** コメント文言の言い換えのみで実装ロジックへの影響はない。Task 3 の自己検証テストが即座に不整合を検出し、同一コミット内で修正済み。

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-02（02-VERIFICATION.md gaps・BLOCKER）が解消された。テンプレート保存/削除/リネームは「キャンセル」で確実に取り消せるようになり、Apply でのみ一括確定される
- 02-VERIFICATION.md の truth 1（SC1: テンプレート保存/選択/削除/リネーム）の failed 原因（浅いコピー + 即時 `_save_settings`）が両方除去された
- CR-01（Tesseract 未インストール時の `_last_valid_provider` 初期化バグ）は本プランのスコープ外（02-VERIFICATION.md gaps に非計上・別件推奨）として引き続き未対応
- behavior_unverified の3件（テンプレート切替の D-05/D-07 フロー・重複名拒否 UI・削除ボタン無効化 UI）は本プランの対象（CR-02）外のため未着手のまま
- ブロッカーなし。フルスイート978件グリーン・ruff クリーン

---
*Phase: 02-ai*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/llm_config/dialog.py
- FOUND: pagefolio/dialogs/llm_config/sections.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_provider_ui.py
- FOUND: 23a354f (Task 1 commit)
- FOUND: a841a17 (Task 2 commit)
- FOUND: aa7cf88 (Task 3 commit)
- FOUND: 3b60235 (SUMMARY commit)
