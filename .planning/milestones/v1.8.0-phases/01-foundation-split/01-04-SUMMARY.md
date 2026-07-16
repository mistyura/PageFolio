---
phase: 01-foundation-split
plan: 04
subsystem: ui
tags: [refactor, packaging, llm-config, mixin, tkinter, registry]

# Dependency graph
requires:
  - phase: 01-foundation-split (Plan 02)
    provides: "pagefolio/ocr_providers/registry.py（env_vars_for/primary_env_var/resolve_env_key/sensitive_keys）"
  - phase: 01-foundation-split (Plan 03)
    provides: "settings/ocr/ocr_dialog の registry 参照統合パターン（同型の統合手法）"
provides:
  - "pagefolio/dialogs/llm_config/ パッケージ（__init__.py/dialog.py/sections.py/model_fetch.py の4ファイル）"
  - "旧 pagefolio/dialogs/llm_config.py モジュールの削除（パッケージへ完全移行）"
  - "D-09 の残り2参照面（sections.py #4 + model_fetch.py #5）が registry を Single Source of Truth として参照する状態"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mixin 3層分割（PDFEditorApp の8 Mixin構成と同型パターンを LLMConfigDialog へ適用）"
    - "tk.Toplevel を継承リスト末尾に配置し __init__ を単一 Mixin へ集約する MRO 安全パターン"

key-files:
  created:
    - pagefolio/dialogs/llm_config/__init__.py
    - pagefolio/dialogs/llm_config/dialog.py
    - pagefolio/dialogs/llm_config/sections.py
    - pagefolio/dialogs/llm_config/model_fetch.py
  modified:
    - tests/test_provider_ui.py
  deleted:
    - pagefolio/dialogs/llm_config.py

key-decisions:
  - "分割で monkeypatch(pagefolio.dialogs.llm_config, 'prompt_file_exists'/'save_prompt_file') の対象名前空間がずれた（Plan 02 の _detect_tesseract と同型の Pitfall）ため、__init__.py で settings.prompt_file_exists/save_prompt_file を re-export し、DialogMixin._apply 内で pagefolio.dialogs.llm_config 経由の遅延 import へ変更した"
  - "sections.py/model_fetch.py の env var 設定済み判定・キー解決を registry.env_vars_for() の単一ループへ一般化し、Gemini の GEMINI_API_KEY 優先→GOOGLE_API_KEY フォールバックを含む3プロバイダの解決順を自動的に保存する形にした（provider 別ハードコード分岐を撤廃）"

patterns-established: []

requirements-completed: [V180-REFAC-02, V180-ROBUST-02]

coverage:
  - id: D1
    description: "pagefolio/dialogs/llm_config.py（1660行・単一クラス）を DialogMixin/SectionsMixin/ModelFetchMixin の3層 Mixin + __init__.py（多重継承統合）へ機械的分割し、両経路 import・MRO健全性を維持"
    requirement: "V180-REFAC-02"
    verification:
      - kind: unit
        ref: "python -c \"from pagefolio.dialogs.llm_config import LLMConfigDialog; from pagefolio.dialogs import LLMConfigDialog\""
        status: pass
      - kind: unit
        ref: "MRO構造検証: tk.Toplevel が3 Mixinより後ろ・__init__ が DialogMixin に集約（tests/test_provider_ui.py::TestLLMConfigDialogMRO）"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py（更新済み3ソーススキャンテスト含む・pytest tests/test_provider_ui.py -q）"
        status: pass
    human_judgment: false
  - id: D2
    description: "sections.py の環境変数「設定済み」注記判定（D-09 #4）と model_fetch.py のモデル取得キー解決（D-09 #5・REVIEWS.md Antigravity MEDIUM反映）を registry.env_vars_for() へ統合し、env var 名のハードコードを撤廃"
    requirement: "V180-ROBUST-02"
    verification:
      - kind: unit
        ref: "grep -c 'env_vars_for' pagefolio/dialogs/llm_config/model_fetch.py（5・import+使用あり）"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestCheckCloudApiKey（UI値優先→envフォールバック→未解決エラーの3系統回帰）"
        status: pass
      - kind: unit
        ref: "pytest -q（全906件）・ruff check . && ruff format --check .（69ファイル）"
        status: pass
    human_judgment: false

duration: 約16分
completed: 2026-07-14
status: complete
---

# Phase 01 Plan 04: llm_config 分割 + env var 参照統合（D-09残り2面） Summary

**`pagefolio/dialogs/llm_config.py`（1660行・単一クラス）を DialogMixin/SectionsMixin/ModelFetchMixin の3層 Mixin パッケージへ機械的分割し、D-09（env var 参照の registry 統合）の残り2参照面（sections.py の設定済み注記 + model_fetch.py のキー解決）を registry へ寄せて V180-ROBUST-02 の全参照面統合を完了した**

## Performance

- **Duration:** 約16分
- **Started:** 2026-07-14T09:11:32Z（前セッションから継続・Wave 3実行開始直後）
- **Completed:** 2026-07-14T09:27:16Z
- **Tasks:** 2
- **Files modified:** 6（新規4 + 変更1 + 削除1、Task 2 で2ファイル追加変更）

## Accomplishments
- `pagefolio/dialogs/llm_config.py`（単一クラス `LLMConfigDialog`・1660行）を責務別3層 Mixin へ機械的分割（D-04/D-05: 行の移動のみ・共通化/最適化/リネームなし）:
  - `dialog.py`: `DialogMixin`（`__init__`/`_apply`/`_on_provider_change`/`_on_model_change`/`_model_supports_effort`/`_resize_to_fit`/`_add_prompt_file_notice`/`_set_lm_status`・スクロール域構築）
  - `sections.py`: `SectionsMixin`（`_build` の UI セクション構築・約920行）
  - `model_fetch.py`: `ModelFetchMixin`（`_fetch_models_async` + プロバイダ別 probe/refresh 群）
  - `__init__.py`: `class LLMConfigDialog(DialogMixin, SectionsMixin, ModelFetchMixin, tk.Toplevel)` で多重継承統合。`tk.Toplevel` を継承リスト末尾に配置し `__init__` を `DialogMixin` に集約（Pitfall 3・MRO 破壊防止）
- `tests/test_provider_ui.py` の3ソーススキャンテスト（`test_provider_combo_includes_gemini`/`test_gemini_section_frame_exists_in_source`/`test_fetch_and_test_are_thin_wrappers`）を、旧単一ファイル `read_text` からパッケージ全体を sorted glob で連結する共有ヘルパー `_read_llm_config_package_source()` 経由の走査へ更新
- Pitfall 3 の headless ガードとして `TestLLMConfigDialogMRO` を新設: (a) `tk.Toplevel` が3 Mixin より後ろ、(b) `__init__` が `DialogMixin` に集約、(c) `_build`/`_apply`/`_on_provider_change`/`_fetch_models_async` の存在、をヘッドレスで自動検証
- D-09 #4: `sections.py` の環境変数「設定済み」注記判定（旧 `os.environ.get("RUNPOD_API_KEY")` 等の3箇所ハードコード分岐）を `registry.env_vars_for()` 経由の共有ヘルパー `_configured_env_var()` へ統合。Gemini の GEMINI_API_KEY 優先→GOOGLE_API_KEY フォールバック表示は不変
- D-09 #5（REVIEWS.md Antigravity MEDIUM 反映）: `model_fetch.py` の `_refresh_runpod_models`/`_refresh_claude_models`/`_refresh_gemini_models` のキー解決（旧 `os.environ.get(<HARDCODED_NAME>, "")` の3箇所）を `registry.env_vars_for()` 経由の共有ヘルパー `_env_fallback()` へ統合。UI 入力値優先 → env var フォールバック（タプル順）→ 未解決時空文字の順序は完全不変
- `pytest tests/test_provider_ui.py tests/test_imports.py -q`（154件）・`pytest -q`（全906件）・`ruff check . && ruff format --check .`（69ファイル）全緑を確認

## Task Commits

Each task was committed atomically:

1. **Task 1: llm_config を Mixin 3層パッケージへ機械的分割し、source-scan テストと MRO 構造テストを更新** - `4a17921` (refactor)
2. **Task 2: llm_config の env var 参照（sections.py D-09 #4 + model_fetch.py D-09 #5）を registry へ統合** - `a6688be` (refactor)

**Plan metadata:** (このコミット・docs: complete plan)

## Files Created/Modified
- `pagefolio/dialogs/llm_config/__init__.py` - **新設**。`DialogMixin`/`SectionsMixin`/`ModelFetchMixin` + `tk.Toplevel` の多重継承統合クラス定義。`prompt_file_exists`/`save_prompt_file` の re-export も担う
- `pagefolio/dialogs/llm_config/dialog.py` - **新設**。`DialogMixin`（`__init__`/`_apply`/`_on_*`/スクロール域構築等の共通部）
- `pagefolio/dialogs/llm_config/sections.py` - **新設**。`SectionsMixin`（`_build` の UI セクション構築 + D-09 #4 の `_configured_env_var()` ヘルパー）
- `pagefolio/dialogs/llm_config/model_fetch.py` - **新設**。`ModelFetchMixin`（`_fetch_models_async` + probe/refresh 群 + D-09 #5 の `_env_fallback()` ヘルパー）
- `pagefolio/dialogs/llm_config.py` - **削除**（パッケージへ移行）
- `tests/test_provider_ui.py` - 3ソーススキャンテストをパッケージ走査へ更新 + `TestLLMConfigDialogMRO` 新設

## Decisions Made
- **`_apply` の `prompt_file_exists`/`save_prompt_file` 参照を遅延 import 化**: 分割前は `llm_config.py` 単一モジュール内で `monkeypatch.setattr(pagefolio.dialogs.llm_config, "prompt_file_exists", ...)`（既存テスト `TestApplyPromptFileWriteback`）がモジュールレベル属性を直接差し替えて `_apply` 内の呼び出しに反映されていた。分割後 `_apply` は `dialog.py` に移動し、そのモジュールが `pagefolio.settings` から直接 import していたため、テストが `pagefolio.dialogs.llm_config`（`__init__.py`）側の属性を差し替えても `dialog.py` 側の束縛には反映されず2件のテストが赤くなった（Plan 02 の `_detect_tesseract` monkeypatch 断絶と同型の Pitfall）。`__init__.py` で `prompt_file_exists`/`save_prompt_file` を re-export した上で、`_apply` 内で `from pagefolio.dialogs.llm_config import prompt_file_exists as _prompt_file_exists, save_prompt_file as _save_prompt_file` という遅延 import へ変更し、パッケージ側の（monkeypatch 後の）最新属性を毎回参照するようにした
- D-09 #4/#5 の env var 参照統合は、3プロバイダ（claude/gemini/runpod）それぞれ個別のハードコード分岐だったコードを `registry.env_vars_for()` のタプル順ループへ一般化する形で実施。Gemini のみ2要素タプル（`GEMINI_API_KEY`, `GOOGLE_API_KEY`）を持つため、ループが自然に「優先→フォールバック」を実現し、claude/runpod（各1要素タプル）でも同じコードパスで動作する

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `_apply` の `prompt_file_exists`/`save_prompt_file` monkeypatch 断絶を修正**
- **Found during:** Task 1（分割直後の `pytest tests/test_provider_ui.py -q` 実行）
- **Issue:** 分割により `DialogMixin._apply` 内の `prompt_file_exists`/`save_prompt_file` 呼び出しが `dialog.py` 自身のモジュール名前空間で解決されるようになり、既存テスト `TestApplyPromptFileWriteback`（`monkeypatch.setattr(pagefolio.dialogs.llm_config, "prompt_file_exists"/"save_prompt_file", ...)`）の差し替えが効かなくなった（`AttributeError: module 'pagefolio.dialogs.llm_config' has no attribute 'prompt_file_exists'`）
- **Fix:** `__init__.py` に `from pagefolio.settings import prompt_file_exists, save_prompt_file` を追加して re-export し、`dialog.py` の `_apply` 内で `pagefolio.dialogs.llm_config` 経由の遅延 import に変更（Plan 02 の `TesseractProvider._detect_tesseract` 修正と同型のパターン）
- **Files modified:** `pagefolio/dialogs/llm_config/__init__.py`, `pagefolio/dialogs/llm_config/dialog.py`
- **Verification:** `pytest tests/test_provider_ui.py -q` で99件全通過（修正前は該当2件が失敗）
- **Committed in:** `4a17921`（Task 1 コミットに含む）

**2. [Rule 3 - Blocking] `dialog.py` の未使用 import（`save_prompt_file`）を ruff で検出・削除**
- **Found during:** Task 1（`ruff check` 実行時）
- **Issue:** 上記修正で `_apply` 内が遅延 import に変わった結果、`dialog.py` モジュール冒頭の `from pagefolio.settings import ... save_prompt_file` が未使用（F401）になった
- **Fix:** `ruff check --fix` で未使用 import を除去し `ruff format` を適用
- **Files modified:** `pagefolio/dialogs/llm_config/dialog.py`
- **Verification:** `ruff check . && ruff format --check .` がクリーン
- **Committed in:** `4a17921`（Task 1 コミットに含む）

---

**Total deviations:** 2 auto-fixed（いずれも Rule 3 - blocking issue: 機械的分割によって既存テストの monkeypatch 前提が壊れた箇所の修正、および付随する lint 指摘の解消）
**Impact on plan:** 修正は D-11（後方互換 import・既存テスト無修正での通過）の精神を保つための必須対応。プロバイダの実挙動・UI レイアウト・env var 解決順は一切変更していない。スコープ拡大なし。

## Issues Encountered
None（上記2件は Deviations セクションで対応済み）

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `pagefolio/dialogs/llm_config/` パッケージが確立され、D-09（全参照面統合）が4箇所すべて（Plan 03: settings/ocr/ocr_dialog、Plan 04: sections.py + model_fetch.py）完了した
- V180-REFAC-01/02・V180-ROBUST-02 の3要件すべてが Phase 1 で完了
- ブロッカーなし。Phase 1（foundation-split）の全4プラン完了

---
*Phase: 01-foundation-split*
*Completed: 2026-07-14*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/llm_config/__init__.py
- FOUND: pagefolio/dialogs/llm_config/dialog.py
- FOUND: pagefolio/dialogs/llm_config/sections.py
- FOUND: pagefolio/dialogs/llm_config/model_fetch.py
- CONFIRMED DELETED: pagefolio/dialogs/llm_config.py
- FOUND commit: 4a17921
- FOUND commit: a6688be
