---
phase: 04-ui-ux
plan: 03
subsystem: ui
tags: [tkinter, dialogs, llm-config, ollama, i18n]

# Dependency graph
requires:
  - phase: 04-02
    provides: "SettingsDialog の外観/操作/AI・OCR 3セクション再編・app 参照配線（_open_settings に app=self）"
provides:
  - "LLMConfigDialog の共通/固有グルーピング見出し（llm_config_common_section/llm_config_provider_section）"
  - "app._apply_llm_settings_live（_rebuild_ui を伴わない軽量 app.settings 即時反映）"
  - "SettingsDialog(on_llm_apply=...) 経由のネスト適用独立トランザクション化（D-14・C4/C5 解消）"
  - "LLMConfigDialog._probe_ollama_provider（Ollama モデル取得/接続テストの共通ヘルパー・C2 解消）"
affects: [04-04 (棚卸し・文言監査の残タスク), 04-ui-ux]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "既存 _probe_lm_provider（update_combo パラメータ化）と同型のヘルパー統合パターンを Ollama にも横展開"
    - "ネストダイアログの適用を外側 Apply/Cancel から独立させる際は、後方互換の任意引数 + getattr 防御アクセスで既存 SimpleNamespace スタブとの互換性を保つ"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config.py
    - pagefolio/dialogs/settings.py
    - pagefolio/app.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py

key-decisions:
  - "共通/固有見出しは _on_provider_change 内で each 分岐（claude/gemini/tesseract/else）ごとに before=self.scale_row で再配置する設計にした。既存の specific-frame と effort/temperature frame の挿入ロジック（before=self.scale_row）自体は一切変更していない"
  - "app._apply_llm_settings_live は self.settings.update(llm_settings) + _save_settings のみを行い、_rebuild_ui() は呼ばない（nested on_apply から呼ぶと開いている SettingsDialog Toplevel まで destroy されるため）"
  - "SettingsDialog.__init__ の on_llm_apply は末尾の後方互換任意引数とし、_open_llm_config 内の nested on_apply では getattr(self, '_on_llm_apply', None) で防御的に参照する（既存の _on_llm_apply 未設定スタブとの互換維持）"
  - "_probe_ollama_provider は _probe_lm_provider と同型の update_combo パラメータ化ヘルパーとし、既存のステータス文言（settings_lm_testing/settings_lm_test_ok/settings_lm_test_fail）をそのまま使い回した（lang.py は本プランで変更しない・04-04 へ委譲）"

requirements-completed: [V171-UIUX-03, V171-TEST-03]

coverage:
  - id: D1
    description: "LLMConfigDialog に共通/固有グルーピング見出し（llm_config_common_section/llm_config_provider_section）が表示され、既存の1枚・プロバイダ選択でセクション切替という構造は維持される"
    requirement: "V171-UIUX-03"
    verification:
      - kind: unit
        ref: "python -c AST/lang.py キー存在確認（見出しキー2種・ja/en 同時追加）"
        status: pass
      - kind: unit
        ref: "pytest tests/test_provider_ui.py -x -q（プロバイダ切替の既存回帰）"
        status: pass
      - kind: manual_procedural
        ref: "実際の見出し表示・レイアウト目視確認"
        status: unknown
    human_judgment: true
    rationale: "Tkinter ウィジェットの実描画・見出し配置の視覚的妥当性は既存テストスイート（実 Tk ウィジェット生成なし）では検証できず、VERIFICATION.md の Manual-Only 項目として記録される（既存 human-verify 運用と同じ・RESEARCH.md D-20）"
  - id: D2
    description: "LLMConfigDialog のネスト適用が独立トランザクション化され、外側 SettingsDialog をキャンセルしても app.settings（メモリ）へ反映済みの LLM 設定が失われない（C4/C5 解消）"
    requirement: "V171-UIUX-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py#TestApplyLlmSettingsLive"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py#TestSettingsDialogNestedApplyCascade"
        status: pass
    human_judgment: false
  - id: D3
    description: "Ollama のモデル取得/接続テストが LM Studio と同型の単一共通ヘルパー（_probe_ollama_provider）へ統合され、二重実装が解消される"
    requirement: "V171-TEST-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py#TestProbeOllamaProvider"
        status: pass
    human_judgment: false
  - id: D4
    description: "API キーが LLMConfigDialog の適用値（llm_settings）・ネスト適用経由の app.settings いずれにも流入しない（prohibition の回帰固定）"
    requirement: "V171-UIUX-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py#TestApiKeyNotInSettings"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py#TestSettingsDialogNestedApplyCascade::test_api_key_not_propagated_through_cascade"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-05
status: complete
---

# Phase 4 Plan 3: LLMConfigDialog 整理 + Ollama 重複解消 Summary

**LLMConfigDialog に共通/固有見出しを追加しネスト適用を独立トランザクション化（D-14）、Ollamaモデル取得/接続テストをLM Studio型の共通ヘルパーへ統合（C2）**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-05T09:59:00Z
- **Completed:** 2026-07-05T10:15:46Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `LLMConfigDialog._build` に「選択中プロバイダ固有の設定」「全プロバイダ共通の設定」の2見出しラベルを追加し、`_on_provider_change` の各分岐（lmstudio/ollama/runpod/claude/gemini/tesseract/off）で `before=self.scale_row` を使って正しい位置（固有設定の直後・共通パラメータ群の先頭）へ再配置する設計にした。既存の `before=self.scale_row` 挿入ロジック自体は変更していない
- `app.py` に `_apply_llm_settings_live(llm_settings)` を新設し、`self.settings.update()` + `_save_settings()` のみを行う軽量反映（`_rebuild_ui()` は呼ばない）を実装
- `SettingsDialog.__init__` に後方互換の `on_llm_apply=None` 引数を追加し、`_open_llm_config` のネスト `on_apply` から `getattr(self, "_on_llm_apply", None)` 経由で呼び出すことで、外側 SettingsDialog の Apply/Cancel と独立して app.settings（メモリ）へ即時反映するようにした（C4/C5 解消）
- `app._open_settings` の `SettingsDialog(...)` 呼び出しに `on_llm_apply=self._apply_llm_settings_live` を配線
- `LLMConfigDialog._probe_ollama_provider(update_combo)` を新設し、`_fetch_ollama_models`/`_test_ollama_connection` を 1 行ラッパーへ置換。旧重複本体（LM Studio 用 `_probe_lm_provider` とほぼ完全重複していた実装）を除去（C2 解消）
- 新規テストクラス4種を `tests/test_provider_ui.py` へ追加: `TestApplyLlmSettingsLive`（軽量反映の単体検証）・`TestSettingsDialogNestedApplyCascade`（外側キャンセルでも反映が失われないことの回帰）・`TestProbeOllamaProvider`（Combobox反映有無・URL空欄・接続エラー・薄いラッパー化の検証）

## Task Commits

Each task was committed atomically:

1. **Task 1: LLMConfigDialog に共通/固有グルーピング見出しを追加（D-15）** - `d70dc19` (feat)
2. **Task 2: ネスト適用を独立トランザクション化（D-14・C4/C5）+ cascade 回帰テスト** - `bdcc97a` (feat)
3. **Task 3: Ollama モデル取得/接続テストを共通ヘルパーへ統合（C2）** - `f979d37` (refactor)

## Files Created/Modified
- `pagefolio/dialogs/llm_config.py` - 共通/固有見出しラベル2種を追加し `_on_provider_change` の各分岐へ配置ロジック追加・`_probe_ollama_provider` 新設で Ollama 重複解消
- `pagefolio/dialogs/settings.py` - `SettingsDialog.__init__` に `on_llm_apply=None` 後方互換引数を追加・`_open_llm_config` のネスト `on_apply` から呼び出す配線を追加
- `pagefolio/app.py` - `_apply_llm_settings_live` メソッド新設・`_open_settings` の `SettingsDialog(...)` 呼び出しに `on_llm_apply=self._apply_llm_settings_live` を追加
- `pagefolio/lang.py` - `llm_config_provider_section`/`llm_config_common_section` を ja/en 両辞書へ同時追加
- `tests/test_provider_ui.py` - `TestApplyLlmSettingsLive`/`TestSettingsDialogNestedApplyCascade`/`TestProbeOllamaProvider` の3クラス追加・既存 `TestOpenSettingsDoubleLaunchGuard` の2スタブへ `_apply_llm_settings_live` 属性を追加（新規必須引数への追従）

## Decisions Made
- 共通/固有見出しの配置は、既存の「specific-frame と effort/temperature frame がともに `before=self.scale_row` で挿入される」という構造上の制約から、`_common_section_heading` も `_on_provider_change` の各分岐内で `before=self.scale_row` により都度再配置する設計にした。これにより visual 順序（固有見出し → 固有フレーム → 共通見出し → 共通パラメータフレーム → scale_row）を、既存の specific-frame 挿入ロジックを一切変更せずに実現した
- `_apply_llm_settings_live` は `_rebuild_ui()` を意図的に呼ばない。nested on_apply の実行コンテキストは「SettingsDialog（Toplevel）がまだ開いている最中」であり、`_rebuild_ui()` は `self.root.winfo_children()` を全 destroy するため、そのまま呼ぶと開いている SettingsDialog 自身が破棄されてしまう
- `on_llm_apply` の参照は `getattr(self, "_on_llm_apply", None)` の防御的パターンにした。これは既存の `TestSettingsDialogOpenLlmConfigPersists`（`_on_llm_apply` 属性を持たない SimpleNamespace スタブ）との後方互換を壊さないための選択で、Phase 1-2 で確立済みの `getattr(self, "_plugin_manager", None)` 等と同じ慣習に従う

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 既存 `TestOpenSettingsDoubleLaunchGuard` の2スタブに `_apply_llm_settings_live` 属性を追加**
- **Found during:** Task 2（ネスト適用の独立トランザクション化）
- **Issue:** `app._open_settings` が新たに `on_llm_apply=self._apply_llm_settings_live` を参照するようになったため、この属性を持たない既存の `SimpleNamespace` スタブ（`test_second_call_reuses_existing_dialog`/`test_new_dialog_created_after_previous_closed`）が `AttributeError` で落ちるようになった
- **Fix:** 両テストのスタブへ `_apply_llm_settings_live=lambda s: None` を追加
- **Files modified:** `tests/test_provider_ui.py`
- **Verification:** `pytest tests/test_provider_ui.py -x -q` 全件グリーン
- **Committed in:** `bdcc97a`（Task 2 commit）

---

**Total deviations:** 1 auto-fixed（Rule 3 — blocking issue）
**Impact on plan:** 既存テストスタブの後方互換維持に必要な最小限の追従。スコープ拡大なし。

## Issues Encountered

None - `_probe_ollama_provider` のテストスタブに `_L`（LANG 辞書）属性が漏れていた点のみ実装中に気づき、即座に追加して解決（Task 3 完了前・コミット前に修正済み）。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- V171-UIUX-03（SettingsDialog/LLMConfigDialog 整理）・V171-TEST-03（棚卸しの一部・Ollama 重複解消）は本プランで完了
- 04-RESEARCH.md の棚卸し確定表のうち、本プランで解消したのは C2（Ollama 重複）と C4/C5（ネスト同期）のみ。残る C6（viewer.py ハードコード文言）・C7（page_ops.py messagebox 種別不一致）・C8（見出しアイコン改称・D-16 は 04-02 で既に着手済みだが lang.py 未使用9キー削除は未着手）は次プラン（04-04）の担当範囲として継続
- LLMConfigDialog の共通/固有見出し表示・ネスト適用の実挙動目視は VERIFICATION.md の Manual-Only 項目として記録が必要
- ブロッカーなし。フルスイート857件グリーン・ruffクリーン確認済み

---
*Phase: 04-ui-ux*
*Completed: 2026-07-05*

## Self-Check: PASSED
