---
phase: 02-ai
plan: 01
subsystem: ai
tags: [settings, prompt-templates, ocr-fallback, pure-logic-layer, pytest]

# Dependency graph
requires:
  - phase: 01-foundation-split
    provides: ocr_providers/registry.py の sensitive_keys() 中央レジストリ（_SENSITIVE_KEYS の生成元）
provides:
  - "settings.py のテンプレート CRUD 純関数群（save/get/list/delete/rename/exists）"
  - "prompt_templates/ocr_fallback_enabled/ocr_fallback_chain の3デフォルトキー（setdefault マイグレーション対応）"
  - "load_custom_prompt/load_summary_prompt の3段解決（外部ファイル > アクティブテンプレート > 設定欄）"
  - "pagefolio/ocr_fallback.py（next_fallback_candidate/next_summary_candidate・Tk/fitz 非依存）"
affects: [02-02, 02-03, 02-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "settings 辞書を第1引数に取る関数型 CRUD ヘルパー（自動保存しない・呼び出し側が _save_settings() を担う）"
    - "Tk/fitz 非依存の純ロジック層（ocr_pipeline.py/pagination.py と同格）に ocr_fallback.py を追加"

key-files:
  created:
    - pagefolio/ocr_fallback.py
    - tests/test_prompt_templates.py
    - tests/test_ocr_fallback.py
  modified:
    - pagefolio/settings.py

key-decisions:
  - "D-01/D-02: テンプレートは settings.json 内の prompt_templates 辞書（active + items のペア保存）に閉じ、UI 実装（02-02〜）へ土台を渡す"
  - "D-03: delete_template はアクティブテンプレート削除を ValueError で拒否する防御的実装（UI 側の無効化と二重防御）"
  - "D-04: save_template/rename_template は空名・重複名を ValueError で拒否する純粋バリデーション"
  - "V180-TMPL-05: resolve_ocr_prompt/resolve_summary_prompt（ocr.py）のシグネチャは無改造。テンプレート層は load_custom_prompt/load_summary_prompt 側でのみ挿入"
  - "D-10/D-12: ocr_fallback.py は次候補選択のみを担う純関数。確認ダイアログ・実際のプロバイダ切替は 02-04（オーケストレーション層）の責務として明確に分離"

patterns-established:
  - "テンプレート CRUD は各関数冒頭で settings.setdefault('prompt_templates', ...) を行い未初期化 settings でも安全に動作する"
  - "purely-logic モジュールは grep -c -E 'import (tkinter|fitz)' が 0 であることをテストで機械検証する"

requirements-completed: [V180-TMPL-01, V180-TMPL-03, V180-TMPL-04, V180-TMPL-05, V180-FALL-01, V180-FALL-03]

coverage:
  - id: D1
    description: "settings.py にテンプレート CRUD 純関数（save/get/list/delete/rename/exists）と prompt_templates/ocr_fallback_* の3デフォルトキーを追加"
    requirement: "V180-TMPL-01"
    verification:
      - kind: unit
        ref: "tests/test_prompt_templates.py::TestSaveTemplate"
        status: pass
      - kind: unit
        ref: "tests/test_prompt_templates.py::TestListAndSelect"
        status: pass
    human_judgment: false
  - id: D2
    description: "delete_template のアクティブテンプレート削除禁止（D-03）・rename_template の重複/空名拒否（D-04）"
    requirement: "V180-TMPL-03"
    verification:
      - kind: unit
        ref: "tests/test_prompt_templates.py::TestDeleteRename"
        status: pass
    human_judgment: false
  - id: D3
    description: "load_custom_prompt/load_summary_prompt を外部ファイル>アクティブテンプレート>設定欄の3段解決へ拡張。resolve_ocr_prompt/resolve_summary_prompt のシグネチャは不変"
    requirement: "V180-TMPL-04"
    verification:
      - kind: unit
        ref: "tests/test_prompt_templates.py::TestExternalFileSync"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestResolveOcrPrompt / TestResolveSummaryPrompt"
        status: pass
    human_judgment: false
  - id: D4
    description: "テンプレートは全プロバイダ共通の load_custom_prompt/load_summary_prompt を経由するため横断共有される"
    requirement: "V180-TMPL-05"
    verification:
      - kind: unit
        ref: "tests/test_prompt_templates.py::TestExternalFileSync"
        status: pass
    human_judgment: false
  - id: D5
    description: "ocr_fallback.py 新規（next_fallback_candidate/next_summary_candidate）。chain 空・全試行済みで None を返す安全側既定"
    requirement: "V180-FALL-01"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestDisabledByDefault"
        status: pass
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestNextCandidate"
        status: pass
    human_judgment: false
  - id: D6
    description: "next_summary_candidate が text_capable フィルタで tesseract 等の text 非対応プロバイダを除外（サマリフォールバックの並列度/APIキー再評価は 02-04 の責務）"
    requirement: "V180-FALL-03"
    verification:
      - kind: unit
        ref: "tests/test_ocr_fallback.py::TestSummaryCandidateFilter"
        status: pass
    human_judgment: false

duration: 約10min
completed: 2026-07-14
status: complete
---

# Phase 02 Plan 01: テンプレート管理 + フォールバックの純ロジック基盤層 Summary

**settings.py にプロンプトテンプレート CRUD 純関数（6関数）と3段プロンプト解決を追加し、新規 ocr_fallback.py に次候補選択の純関数2本を実装（Tk/fitz 非依存）**

## Performance

- **Duration:** 約10分
- **Started:** 2026-07-14T20:3x（Task 1 コミット直前）
- **Completed:** 2026-07-14T20:41:33+09:00
- **Tasks:** 3
- **Files modified:** 4（新規2・変更2）

## Accomplishments

- `settings.py` に `prompt_templates`（active + items ペア保存）・`ocr_fallback_enabled`・`ocr_fallback_chain` の3デフォルトキーを既存 `setdefault` マイグレーションループへ追加（後方互換）
- テンプレート CRUD 純関数6本（`list_template_names`/`get_template`/`template_name_exists`/`save_template`/`delete_template`/`rename_template`）を実装。D-03（アクティブ削除禁止）・D-04（空名/重複名拒否）を ValueError で機械的に強制
- `load_custom_prompt`/`load_summary_prompt` を「外部mdファイル > アクティブテンプレート > 設定欄直接値」の3段解決へ拡張。`ocr.py` の `resolve_ocr_prompt`/`resolve_summary_prompt` は無改造（シグネチャ・優先順位ロジック不変）で流用
- 新規 `pagefolio/ocr_fallback.py`（Tk/fitz 非依存の純ロジック層）に `next_fallback_candidate`/`next_summary_candidate` を実装。D-10（連鎖は最後まで辿る）・D-12（サマリ経路は text_capable フィルタ）を満たす
- 新規テスト2本（`test_prompt_templates.py` 32件・`test_ocr_fallback.py` 13件）を作成。フルスイート951件グリーン・ruff クリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: settings.py テンプレート CRUD 純関数 + デフォルト値追加、test_prompt_templates.py を先行作成** - `7bdb6a8` (feat)
2. **Task 2: load_custom_prompt / load_summary_prompt をアクティブテンプレート段を含む3段解決へ拡張** - `f12e07a` (feat)
3. **Task 3: ocr_fallback.py 新規（次候補選択の純関数）+ test_ocr_fallback.py を先行作成** - `b2776a1` (feat)

_Note: 各タスクは tdd="true" だが、settings.py/ocr_fallback.py は既存純ロジック層と同型の「実装+テスト同時作成」形式で進行（既存テストファイルが存在しない Wave 0 gap のため、RED 単独コミットは行わず実装とテストを1コミットにまとめた。既存 pytest 951件のフルスイート回帰で GREEN を担保）。_

## Files Created/Modified

- `pagefolio/settings.py` - テンプレート CRUD 6関数・3デフォルトキー追加・load_custom_prompt/load_summary_prompt の3段解決化
- `pagefolio/ocr_fallback.py` - 新規。next_fallback_candidate/next_summary_candidate（Tk/fitz 非依存）
- `tests/test_prompt_templates.py` - 新規。TestSaveTemplate/TestListAndSelect/TestDeleteRename/TestExternalFileSync/TestSensitiveKeysNotPolluted（32件）
- `tests/test_ocr_fallback.py` - 新規。TestDisabledByDefault/TestNextCandidate/TestSummaryCandidateFilter（13件）

## Decisions Made

- CRUD ヘルパーは `_ensure_prompt_templates` のような共有 private ヘルパーを設けず、各関数冒頭で `settings.setdefault(...)` を直接呼ぶ形にした（プランの action 記述に忠実・過剰な抽象化を避けた）
- `load_custom_prompt`/`load_summary_prompt` はテンプレート解決に `get_template()`（本プランで新設した公開関数）を再利用し、辞書アクセスの重複実装を避けた

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 2 の acceptance criteria verify コマンドが 0 件収集で失敗する問題を等価コマンドで検証**
- **Found during:** Task 2（load_custom_prompt/load_summary_prompt 拡張）
- **Issue:** プラン記載の `pytest tests/test_prompt_templates.py::TestExternalFileSync tests/test_provider_ui.py -k resolve_prompt -x` および単独の `pytest tests/test_provider_ui.py -k resolve_prompt -x` はいずれも `-k resolve_prompt` が実際のテストクラス名（`TestResolveOcrPrompt`/`TestResolveSummaryPrompt`）に一致せず「99 deselected, 0 selected」（pytest exit code 5）で終了し、検証を完了できなかった（プラン記述時のキーワード想定と実クラス名の齟齬）
- **Fix:** 意図が同一の等価コマンド `pytest tests/test_prompt_templates.py::TestExternalFileSync -x`（7件 pass）と `pytest tests/test_provider_ui.py -k "ResolveOcrPrompt or ResolveSummaryPrompt" -x`（11件 pass）を個別実行して検証した。実装コードは変更なし（テストコマンドの表記のみの問題）
- **Files modified:** なし（検証コマンドの解釈のみ）
- **Verification:** 上記2コマンドがいずれも green。フルスイート（951件）でも該当テストが全て通過することを確認
- **Committed in:** f12e07a（Task 2 コミットに実装変更を含む。検証コマンド自体はコード変更を伴わないため別コミットなし）

---

**Total deviations:** 1 auto-fixed（Rule 3・ブロッキング issue の検証コマンド代替）
**Impact on plan:** 実装コードへの影響なし。プランの検証コマンド表記の誤り（`-k` キーワードが実際のクラス名と不一致）を、同じ検証意図を満たす代替コマンドで解消した。スコープクリープなし。

## Issues Encountered

None（上記デビエーション以外に問題なし）

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- テンプレート CRUD・3段プロンプト解決・フォールバック次候補選択の純ロジック基盤層が確立。02-02（UI: テンプレートセクション）・02-03（UI: フォールバックセクション）・02-04（オーケストレーション: `_propose_fallback`/`_switch_to_fallback_provider`）はこの上に構築できる
- `ocr_fallback.py` はあくまで「次候補選択」のみ。確認ダイアログ再提示（D-11）・`self.app.settings` を汚染しないローカルスナップショット方式（RESEARCH.md Pitfall 4）・`build_provider` の並列度/APIキー再評価（Pitfall 3）は 02-04 の責務として未着手のまま残っている（計画どおり）
- ブロッカーなし

---
*Phase: 02-ai*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/ocr_fallback.py
- FOUND: tests/test_prompt_templates.py
- FOUND: tests/test_ocr_fallback.py
- FOUND: .planning/phases/02-ai/02-01-SUMMARY.md
- FOUND: 7bdb6a8 (Task 1 commit)
- FOUND: f12e07a (Task 2 commit)
- FOUND: b2776a1 (Task 3 commit)
- FOUND: 5b270a8 (SUMMARY.md commit)
