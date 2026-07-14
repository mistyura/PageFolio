---
phase: 02-ai
plan: 03
subsystem: ui
tags: [tkinter, llm-config-dialog, ocr-fallback, settings-json, pytest]

# Dependency graph
requires:
  - phase: 02-ai (plan 01)
    provides: "ocr_fallback.py の next_fallback_candidate/next_summary_candidate（純ロジック層）・settings.py の ocr_fallback_enabled/ocr_fallback_chain デフォルトキー"
provides:
  - "LLM 設定ダイアログの🔁フォールバックセクション（トグル + Listbox + 上へ/下へ + 候補追加/除外）"
  - "_apply による ocr_fallback_enabled/ocr_fallback_chain の収集（ホワイトリスト検証つき）"
affects: [02-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MergeOrderDialog の Listbox+上下ボタンウィジェット構成を Toplevel からLLM設定ダイアログ内の埋め込みセクションへ移植（D-13/D-15）"
    - "provider_row/url_section_frame と同型の pack/pack_forget によるトグル連動表示切替（D-16）"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config/sections.py
    - pagefolio/dialogs/llm_config/dialog.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py

key-decisions:
  - "D-13/D-15: MergeOrderDialog の Listbox+上下ボタンのウィジェット構成のみを移植。Toplevel化・callback経由の親子通信は不要（同一ダイアログ内のself属性で完結）"
  - "D-14: 候補一覧は _base_fallback_providers（6種）+ プラグイン登録の全実行可能プロバイダ。APIキー未設定でも表示し、既知プロバイダ一覧外の名前は読み込み時/_apply収集時の両方でホワイトリスト検証により除外（T-02-07）"
  - "D-16: 既定はトグルOFF・空チェーン。初期表示は self.fallback_enabled_var の初期値に従って直接pack、以降のトグル操作は _on_fallback_toggle が before=self.lm_status_label で位置を固定してpack/pack_forgetする"
  - "_apply のフォールバック収集は getattr フォールバックで既存の _apply スタブ経路（fallback_enabled_var/_fallback_chain/_fallback_known_providers 未設定）との後方互換を保持し、既定値（False・空リスト）を返す"

patterns-established: []

requirements-completed: [V180-FALL-01, V180-FALL-03]

coverage:
  - id: D1
    description: "sections.py に🔁フォールバックセクション（トグル+Listbox+上下ボタン+候補追加/除外）を追加し、D-13/D-14/D-15/D-16を満たす"
    requirement: "V180-FALL-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackSection::test_fallback_widgets_referenced_in_sections_source"
        status: pass
    human_judgment: false
  - id: D2
    description: "既定はトグルOFF・空チェーンでフォールバックが発火しない安全側既定（V180-FALL-01）。トグルONで順序リストが現れる"
    requirement: "V180-FALL-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackSection::test_apply_defaults_when_fallback_attrs_absent"
        status: pass
    human_judgment: false
  - id: D3
    description: "候補プロバイダ名は既知プロバイダ一覧のホワイトリストに限定される（読み込み時・_apply収集時の両方）"
    requirement: "V180-FALL-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackSection::test_apply_filters_unknown_provider_from_chain"
        status: pass
    human_judgment: false
  - id: D4
    description: "_apply が ocr_fallback_enabled(bool)/ocr_fallback_chain(list) を llm_settings へ収集し永続化経路（_save_settings）へ渡す"
    requirement: "V180-FALL-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestFallbackSection::test_apply_collects_fallback_enabled_and_chain"
        status: pass
    human_judgment: false

duration: 約15min
completed: 2026-07-14
status: complete
---

# Phase 02 Plan 03: LLM 設定ダイアログへのフォールバック順設定 UI 追加 Summary

**sections.py に🔁フォールバックセクション（トグル+Listbox+上下ボタン+候補追加/除外）を追加し、_apply でocr_fallback_enabled/ocr_fallback_chainをホワイトリスト検証つきで収集**

## Performance

- **Duration:** 約15分
- **Started:** 2026-07-14（Task 1 コミット直前）
- **Completed:** 2026-07-14
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `sections.py` の `_build` に🔁フォールバックセクション（トグル`fallback_enabled_var` + `fallback_listbox`（Listbox）+ `fallback_up_btn`/`fallback_down_btn` + 候補追加/除外コンボボックス）を追加。`MergeOrderDialog` の Listbox+上下ボタン構成をウィジェットレベルで移植（D-13/D-15）
- 候補一覧は `_base_fallback_providers`（lmstudio/ollama/runpod/claude/gemini/tesseract）+ プラグイン登録プロバイダの全実行可能プロバイダ（APIキー未設定でも表示・D-14）
- `self._fallback_chain` は読み込み時に `self._fallback_known_providers` でホワイトリスト検証し、既知プロバイダ一覧に無い名前を除外（T-02-07・Input Validation ASVS L1）
- `_on_fallback_toggle` により、既定OFF（V180-FALL-01・D-16）・トグルON時のみ順序リストを表示する `pack`/`pack_forget` 切替を実装（`_on_provider_change` と同型パターン）
- `_fallback_move_up`/`_fallback_move_down`/`_fallback_add`/`_fallback_remove`/`_reload_fallback_list` を実装（`merge.py` の `_move_up`/`_move_down`/`_reload_list` を対象データ `self._fallback_chain` へ置き換えて移植）
- `dialog.py` の `_apply` に `ocr_fallback_enabled`（bool）/`ocr_fallback_chain`（list）の収集を追加。収集時にも既知プロバイダ一覧でホワイトリスト再検証し、`getattr` フォールバックで既存の非バインド `_apply` スタブ経路との後方互換を保持（既定値 False・空リスト）
- `lang.py` に `fallback_*` キー7個を ja/en 同一キーで追加（キー数左右一致を維持）
- `tests/test_provider_ui.py` に `TestFallbackSection`（4件）を追加。フルスイート960件グリーン・ruff クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: sections.py に🔁フォールバックセクション（トグル + Listbox + 上下ボタン）を追加** - `5905a75` (feat)
2. **Task 2: dialog.py _apply にフォールバック設定収集を追加し、test_provider_ui.py にフォールバックテストを追加** - `878940b` (feat)

## Files Created/Modified

- `pagefolio/dialogs/llm_config/sections.py` - 🔁フォールバックセクション UI（トグル + Listbox + 上下ボタン + 候補追加/除外）+ 6メソッド（`_on_fallback_toggle`/`_reload_fallback_list`/`_fallback_move_up`/`_fallback_move_down`/`_fallback_add`/`_fallback_remove`）
- `pagefolio/dialogs/llm_config/dialog.py` - `_apply` に `ocr_fallback_enabled`/`ocr_fallback_chain` のホワイトリスト検証つき収集を追加
- `pagefolio/lang.py` - `fallback_*` キー7個を ja/en 同一キーで追加
- `tests/test_provider_ui.py` - `TestFallbackSection`（4件）を追加

## Decisions Made

- フォールバックセクションの配置は「並列度（concurrency）」セクションの直後・ステータスラベルの直前とした（プロバイダ選択セクション群・テンプレートセクションいずれとも独立したブロック・D-15の「独立セクション」要件を満たしつつ、既存レイアウトの自然な末尾位置）
- 候補追加/除外 UI は PLAN.md の「combobox または追加/除外ボタン」の記述に基づき、readonly combobox（`fallback_candidate_combo`）+「＋ 追加」/「－ 除外」ボタンの組み合わせを採用した（D-14 の「候補一覧には全プロバイダを含める」を Listbox 常時全件表示ではなく明示的な追加操作にすることで、D-16 の「未設定ユーザーにも分かりやすい」構成と両立）
- `_on_fallback_toggle` は `before=self.lm_status_label` で位置を固定する一方、`_build` 内の初回パックは `lm_status_label` 未生成のため単純な `pack()` とした（`_on_provider_change` の `before=self.scale_row` パターンと同型だが、アンカー先が未生成の時点と生成済み以降とで packing 呼び出し方を分けた）

## Deviations from Plan

None - plan executed as written（PLAN.md の action 記述通りに実装。フォールバックセクションのウィジェット構成・配置判断は Claude's Discretion 領域として明示されていた内容の範囲内）。

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

なし。フォールバックセクションは 02-01 で確立済みの `settings.py` デフォルトキー（`ocr_fallback_enabled`/`ocr_fallback_chain`）へ直接接続されており、プレースホルダ/モックデータのハードコードはない。実際のフォールバック発火・確認ダイアログ再提示・プロバイダ再構築（オーケストレーション層）は02-04の責務として未実装のまま（計画どおり）。

## Next Phase Readiness

- フォールバック順設定UI（V180-FALL-01設定面・V180-FALL-03の設定面）がLLM設定ダイアログに接続され、既定OFF・ホワイトリスト検証済みの安全側既定で完成
- 02-04（フォールバックオーケストレーション: `_propose_fallback`/`_switch_to_fallback_provider`・確認ダイアログ再提示・`build_provider`再構築）はこのプランで確立した `ocr_fallback_enabled`/`ocr_fallback_chain` 設定値の上に構築できる
- ブロッカーなし

---
*Phase: 02-ai*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/llm_config/sections.py
- FOUND: pagefolio/dialogs/llm_config/dialog.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_provider_ui.py
- FOUND: 5905a75 (Task 1 commit)
- FOUND: 878940b (Task 2 commit)
