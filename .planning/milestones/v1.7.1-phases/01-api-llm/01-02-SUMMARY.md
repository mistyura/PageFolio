---
phase: 01-api-llm
plan: 02
subsystem: ui
tags: [llm-config-dialog, api-key-input, session-keys, tkinter, settings-dialog]

# Dependency graph
requires:
  - "01-api-llm/01-01-PLAN（_resolve_api_key の優先順反転・LANG キー先行整備）"
provides:
  - "LLMConfigDialog の claude/gemini/runpod 各セクションへのマスク付き APIキー入力欄（トグル + セッション限定注記）"
  - "LLMConfigDialog._apply による app._session_api_keys への同期（llm_settings 非流入を維持）"
  - "SettingsDialog 経由の session_api_keys 配線（app.py → settings.py → LLMConfigDialog）"
  - "_refresh_claude_models / _refresh_gemini_models / _refresh_runpod_models のライブ値優先キー解決"
affects: [01-api-llm/01-03-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "session_api_keys は __init__ で dict(...) 複製せず参照のまま self._session_api_keys として保持（app 実体を書き換えるため）"
    - "APIキー入力行はモデル選択行の直後・モデル更新ボタン行の直前に挿入（キー入力→即モデル取得の操作順を UI 順序でも表現）"
    - "_apply() は llm_settings dict 構築ロジックとは独立したループで3プロバイダ分の session_api_keys 同期のみを行う（api_key 系キーを llm_settings へ混入させない構造的分離）"

key-files:
  created: []
  modified:
    - pagefolio/dialogs/llm_config.py
    - pagefolio/app.py
    - pagefolio/dialogs/settings.py
    - tests/test_provider_ui.py

key-decisions:
  - "app.py._open_settings は self._session_api_keys を getattr(self, '_session_api_keys', None) 経由で渡す（既存の完全 SimpleNamespace テストスタブとの後方互換のための防御的コーディング・実運用では app.py:81 で必ず初期化済み）"
  - "SettingsDialog.__init__ は current_settings（dict(...) で複製）とは異なり session_api_keys を複製せず参照のまま保持（RESEARCH.md Pitfall 5 対応）"
  - "gemini の注記（D-07）は GEMINI_API_KEY 設定済みならその名を、無ければ GOOGLE_API_KEY を表示（既存 dual env var 優先順と整合）"
  - "Task 3 のテストは実 Tk ウィジェットを生成せず、_apply が参照する全属性を SimpleNamespace + 軽量 Get系スタブで埋めて LLMConfigDialog._apply を直接呼ぶ既存パターン（_call_update_ocr_buttons_state 等）を踏襲"

patterns-established:
  - "LLMConfigDialog の3セクション共通パターン（キー入力行 + トグル + 注記）は claude/gemini/runpod で完全に並行実装（analog は同ファイル内モデル選択行）"

requirements-completed: [V171-KEY-01, V171-KEY-04, V171-TEST-02]

coverage:
  - id: T1
    description: "LLMConfigDialog の claude/gemini/runpod 各セクションにマスク付き APIキー入力欄・トグル・セッション限定注記が表示される"
    requirement: "V171-KEY-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestLLMConfigProviderValues（既存回帰・全67件グリーン）"
        status: pass
      - kind: manual
        ref: "01-02-PLAN.md Manual-Only チェック（アプリ起動・マスク表示/トグル目視）"
        status: deferred
    human_judgment: true
  - id: T2
    description: "_apply 実行後、入力値が app._session_api_keys へ格納・空欄でクリアされ、llm_settings/settings.json には流入しない"
    requirement: "V171-KEY-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestApiKeyNotInSettings（2 tests）"
        status: pass
      - kind: unit
        ref: "tests/test_provider_ui.py::TestSessionKeyStoreAndClear（3 tests）"
        status: pass
    human_judgment: false
  - id: T3
    description: "RunPod セッションキーが _session_api_keys['runpod'] に正しく格納され claude スロットを汚染しない"
    requirement: "V171-KEY-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestRunpodSessionKeySlot（3 tests）"
        status: pass
    human_judgment: false
  - id: T4
    description: "SettingsDialog 経由・OCRDialog 経由の双方で同一 _session_api_keys 参照が配線される（本プランは SettingsDialog 経路のみ担当）"
    requirement: "V171-KEY-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py（既存回帰67件・app.py/settings.py 変更後もグリーン維持）"
        status: pass
    human_judgment: false
  - id: T5
    description: "モデル取得ボタンがライブ入力値 → 環境変数の順で解決する"
    requirement: "V171-KEY-01"
    verification:
      - kind: manual
        ref: "01-02-PLAN.md Manual-Only チェック（環境変数未設定でダイアログ入力 → その場でモデル取得）"
        status: deferred
    human_judgment: true

duration: 約15分
completed: 2026-07-05
status: complete
---

# Phase 01 Plan 02: LLMConfigDialog への APIキー入力欄追加 + SettingsDialog 経由配線 Summary

**LLMConfigDialog の claude/gemini/runpod 各セクションにマスク付き APIキー入力欄・トグル・セッション限定注記を追加し、SettingsDialog 経由の session_api_keys 配線とモデル取得のライブ値優先解決を実装**

## Performance

- **Duration:** 約15分
- **Tasks:** 3/3 completed
- **Files modified:** 4（pagefolio/dialogs/llm_config.py, pagefolio/app.py, pagefolio/dialogs/settings.py, tests/test_provider_ui.py）

## Accomplishments

- `LLMConfigDialog.__init__` に `session_api_keys=None` 引数を追加し、複製せず参照をそのまま `self._session_api_keys` として保持。claude/gemini/runpod の3セクションそれぞれへ、モデル選択行の直後・モデル更新ボタン行の直前に「マスク付き `tk.Entry(show="*")` + 👁/🙈 トグルボタン + セッション限定注記（環境変数設定済みなら動的追記）」を追加（D-01〜D-03/D-05/D-07）
- `_apply()` へ、既存の `llm_settings` dict 構築ロジックとは独立したループを追加し、3プロバイダの入力値を `self._session_api_keys` へ同期（非空→格納、空欄→`pop` でクリア）。`llm_settings` dict には `api_key` 系キーを一切追加しない構造を維持（D-04/D-06・T-05-12 継続）
- `_refresh_claude_models` / `_refresh_gemini_models` / `_refresh_runpod_models` を、ダイアログ入力欄のライブ値（OK 前でも）→ 環境変数の順で解決するよう変更（D-10）。既存の静的推奨モデルフォールバック（D-08/D-11）は維持
- `PDFEditorApp._open_settings` → `SettingsDialog.__init__` → `SettingsDialog._open_llm_config` の3段階に `session_api_keys` を配線し、`SettingsDialog` 経由で開いた `LLMConfigDialog` も `app._session_api_keys` の実体を共有するようにした（RESEARCH.md Pitfall 5 対応・OCRDialog 経由の配線は Plan 03 の担当範囲）
- `tests/test_provider_ui.py` へ `TestApiKeyNotInSettings`（2件）・`TestSessionKeyStoreAndClear`（3件）・`TestRunpodSessionKeySlot`（3件）の計8件を新設し、APIキー非流入・格納/クリア・RunPod スロットの正しさを回帰テスト化

## Task Commits

Each task was committed atomically:

1. **Task 1: LLMConfigDialog に3セクション分の APIキー欄・トグル・注記・_apply 同期・ライブ値モデル取得を実装** - `72951f3` (feat)
2. **Task 2: SettingsDialog 経由の session_api_keys 配線（app.py → settings.py → LLMConfigDialog）** - `3d8c113` (feat)
3. **Task 3: APIキー非流入・_session_api_keys 格納/クリア・RunPod スロットの回帰テストを新設** - `592f1fb` (test)

## Files Created/Modified

- `pagefolio/dialogs/llm_config.py` - `session_api_keys` __init__ 引数、claude/gemini/runpod 各セクションへの APIキー行（`*_api_key_var`/`*_api_key_entry`/トグル）追加、`_apply()` への session_api_keys 同期処理追加、`_refresh_*_models` のライブ値優先解決化
- `pagefolio/app.py` - `_open_settings` の `SettingsDialog(...)` 呼び出しへ `session_api_keys=getattr(self, "_session_api_keys", None)` を追加
- `pagefolio/dialogs/settings.py` - `SettingsDialog.__init__` に `session_api_keys=None` 引数追加（複製せず保持）、`_open_llm_config` の `LLMConfigDialog(...)` 呼び出しへ中継追加
- `tests/test_provider_ui.py` - `TestApiKeyNotInSettings`/`TestSessionKeyStoreAndClear`/`TestRunpodSessionKeySlot`（計8テスト）を新設

## Decisions Made

- `app.py._open_settings` は `self._session_api_keys` を直接参照せず `getattr(self, "_session_api_keys", None)` 経由で渡す設計にした。既存の `TestOpenSettingsDoubleLaunchGuard` テストが `_session_api_keys` を持たない完全 `SimpleNamespace` スタブを使っており、直接参照すると `AttributeError` で既存回帰テストが壊れるため。この防御的パターンは `pagefolio/ocr.py:778` 等で既に確立済みの慣例に倣った（Rule 3: ブロッキング問題の自動修正）
- `SettingsDialog.__init__` は `current_settings`（`dict(...)` で複製）と異なり `session_api_keys` を複製せず参照のまま保持する設計を厳守（RESEARCH.md Pitfall 5・複製すると `app._session_api_keys` の実体へ変更が反映されなくなる）
- gemini の環境変数注記（D-07）は `GEMINI_API_KEY` が設定済みならその名を表示し、未設定で `GOOGLE_API_KEY` のみ設定済みならそちらを表示する（既存の dual env var 優先順 `GEMINI_API_KEY` > `GOOGLE_API_KEY` と整合させた）
- Task 3 の回帰テストは実 Tk ウィジェットを生成せず、`LLMConfigDialog._apply` が参照する全属性（プロバイダ別設定行・数値設定・カスタムプロンプト等）を軽量な `_GetVarStub`/`_GetTextStub` で埋めた `SimpleNamespace` に対して非バインドメソッド呼び出しを行う、本ファイル内の既存パターン（`_call_update_ocr_buttons_state` 等）を踏襲した

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] `app.py._open_settings` の直接属性参照が既存テストスタブと非互換**
- **Found during:** Task 2
- **Issue:** `SettingsDialog(...)` 呼び出しに `session_api_keys=self._session_api_keys` を直接渡す実装にしたところ、`tests/test_provider_ui.py::TestOpenSettingsDoubleLaunchGuard` の2テストが `AttributeError: 'types.SimpleNamespace' object has no attribute '_session_api_keys'` で失敗した（既存スタブは `_session_api_keys` を含まない最小構成のため）
- **Fix:** `getattr(self, "_session_api_keys", None)` へ変更（コードベース内の既存確立パターン `getattr(self, '_session_api_keys', {})` を踏襲）。実運用では `PDFEditorApp.__init__` で `self._session_api_keys = {}` が必ず初期化されるため挙動に影響なし
- **Files modified:** `pagefolio/app.py`
- **Commit:** `3d8c113`

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03（OCRDialog の旧セッションキー UI 撤去・`_check_cloud_api_key` 新設・エラー文言差し替え）が必要とする `LLMConfigDialog` の `session_api_keys` 引数は整備済み。Plan 03 では `OCRDialog._open_llm_config` の `LLMConfigDialog(...)` 呼び出しへ `session_api_keys=self.app._session_api_keys` を1行追加するだけで OCRDialog 経路の配線が完了する
- フルスイート 720 件グリーン（ベースライン712件 + 新規8件）・`ruff check . && ruff format .` クリーン確認済み
- Manual-Only 項目（アプリ起動でのマスク表示/トグル実描画目視・入力直後のモデル取得疎通確認・両経路の目視対称性確認）は未実施（コード検証は完了・実描画/実 API のみ未確認）

---
*Phase: 01-api-llm*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/dialogs/llm_config.py
- FOUND: pagefolio/app.py
- FOUND: pagefolio/dialogs/settings.py
- FOUND: tests/test_provider_ui.py
- FOUND commit: 72951f3
- FOUND commit: 3d8c113
- FOUND commit: 592f1fb
