---
phase: 01-api-llm
plan: 03
subsystem: ui
tags: [ocr-dialog, api-key-resolution, session-keys, lang-i18n, tkinter]

# Dependency graph
requires:
  - "01-api-llm/01-01-PLAN（_resolve_api_key の優先順反転・ocr_api_key_missing_runpod 等 LANG キー先行整備）"
  - "01-api-llm/01-02-PLAN（LLMConfigDialog への APIキー入力欄追加・session_api_keys 引数対応）"
provides:
  - "OCRDialog の旧セッションキー入力 UI（api_key_var/_key_frame）とヘルパー（_needs_session_key/_ensure_cloud_session_key）の完全撤去"
  - "値収集をしない軽量ゲート _check_cloud_api_key（claude/gemini/runpod 3プロバイダの明示エラー・messagebox.showerror）"
  - "OCRDialog._open_llm_config → LLMConfigDialog(session_api_keys=...) の配線（OCRDialog 経路の session_api_keys 共有）"
  - "TestCheckCloudApiKey（TestNeedsSessionKey の後継・RunPod スロット誤格納なしの回帰テスト込み）"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "クラウド実行ゲートは _resolve_api_key の解決可否のみを確認する薄い関数に一本化（値の収集・保持は一切行わない）"
    - "既存の完全 SimpleNamespace テストスタブとの後方互換のため self.app._session_api_keys への参照は getattr(self.app, '_session_api_keys', None) 経由（Plan 02 と同じ防御的パターン）"

key-files:
  created: []
  modified:
    - pagefolio/ocr_dialog.py
    - pagefolio/lang.py
    - tests/test_provider_ui.py

key-decisions:
  - "_check_cloud_api_key は _is_cloud_provider() が偽なら無条件 True を返し、真なら _resolve_api_key(name, session_keys) の解決可否のみで判定する（値の保持・返却は一切しない）"
  - "OCRDialog._open_llm_config の LLMConfigDialog(...) 呼び出しへの session_api_keys 配線は、Plan 02 で確立した getattr(self.app, '_session_api_keys', None) の防御的パターンを踏襲（既存 TestOpenLlmConfigDoubleLaunchGuard の完全 SimpleNamespace スタブとの後方互換のため。実運用では app.py:81 で必ず初期化済み）"
  - "撤去に伴い未使用となった os import を pagefolio/ocr_dialog.py から削除（ruff F401 対応）"
  - "ocr_session_key_label を ja/en 両辞書から同時削除（キー数一致を維持・test_lang_parity.py で担保）"

patterns-established:
  - "OCR実行前ゲートは「値を集めて格納する」責務を持たず「解決可否を確認するだけ」の関数に限定する（RunPod の claude スロット誤格納バグの再発を構造的に防止）"

requirements-completed: [V171-KEY-02, V171-KEY-03, V171-KEY-04, V171-TEST-02]

coverage:
  - id: D1
    description: "OCRDialog に旧セッションキー入力欄・ヘルパー（api_key_var/_key_frame/_needs_session_key/_ensure_cloud_session_key）が存在しない"
    requirement: "V171-KEY-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestCheckCloudApiKey（撤去メソッド参照なしで全11ケースがグリーン）"
        status: pass
      - kind: other
        ref: "grep -c '_needs_session_key\\|_ensure_cloud_session_key\\|_key_frame\\|api_key_var' pagefolio/ocr_dialog.py → 0件"
        status: pass
    human_judgment: false
  - id: D2
    description: "_check_cloud_api_key が3プロバイダ（claude/gemini/runpod）で未解決時に明示エラーを出し実行を中断する（成功基準2）"
    requirement: "V171-KEY-02"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestCheckCloudApiKey::test_unresolved_shows_error_and_returns_false[claude|gemini|runpod]"
        status: pass
    human_judgment: false
  - id: D3
    description: "RunPod のセッションキーが claude スロットへ誤格納される旧経路が消滅している（V171-KEY-04・Pitfall 1 の構造的解消）"
    requirement: "V171-KEY-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestCheckCloudApiKey::test_runpod_session_key_does_not_use_claude_slot"
        status: pass
    human_judgment: false
  - id: D4
    description: "OCRDialog._open_llm_config が LLMConfigDialog へ app._session_api_keys 参照を渡す（OCRDialog 経由の配線）"
    requirement: "V171-KEY-01"
    verification:
      - kind: unit
        ref: "tests/test_provider_ui.py::TestOpenLlmConfigDoubleLaunchGuard::test_ocr_dialog_reuses_existing_llm_config_dialog（既存回帰・配線変更後もグリーン維持）"
        status: pass
      - kind: manual
        ref: "01-03-PLAN.md Manual-Only チェック（OCR画面の「⚙ LLM 設定…」からキー入力欄への到達目視）"
        status: deferred
    human_judgment: true
    rationale: "実描画でのボタン到達・ダイアログ表示確認は目視が必要（コード配線はunit testで担保済み）"
  - id: D5
    description: "OCR 実行・サマリ・キャンセル・進捗・リトライの既存フローが回帰なく動作する"
    requirement: "V171-TEST-02"
    verification:
      - kind: unit
        ref: "pytest（フルスイート725件）"
        status: pass
    human_judgment: false

duration: 約10分
completed: 2026-07-05
status: complete
---

# Phase 01 Plan 03: OCRDialog 旧セッションキーUI撤去 + _check_cloud_api_key 一元化 Summary

**OCRDialog の旧セッションキー入力欄（api_key_var/_key_frame）とヘルパー（_needs_session_key/_ensure_cloud_session_key）を撤去し、値収集をしない軽量ゲート _check_cloud_api_key へ置換。RunPod キーの claude スロット誤格納バグを構造的に解消し、後継テスト TestCheckCloudApiKey で3プロバイダの明示エラーを回帰保証**

## Performance

- **Duration:** 約10分
- **Tasks:** 2/2 completed
- **Files modified:** 3（pagefolio/ocr_dialog.py, pagefolio/lang.py, tests/test_provider_ui.py）

## Accomplishments

- OCRDialog から `api_key_var`（StringVar 初期化）・`_key_frame`（入力欄フレーム構築 + プロバイダ切替時の再表示ロジック）・`_needs_session_key()`（env変数未設定判定）・`_ensure_cloud_session_key()`（値収集 + claude/gemini 2分岐のみで RunPod 選択時に claude スロットへ誤格納するバグの実体）を完全撤去
- 代替として `_check_cloud_api_key()` を新設。`_is_cloud_provider()` が偽なら無条件 True、真なら `_resolve_api_key(name, session_keys)` の解決可否のみを確認し、`OCRAPIKeyError` 捕捉時のみ3プロバイダ別 LANG キー（`ocr_api_key_missing`/`_gemini`/`_runpod`）で `messagebox.showerror` を表示して False を返す（値の保持・返却は一切しない）
- `_on_run`（クラウド実行ゲート）と `_on_summary`（サマリ実行ゲート）の呼び出しを `self._ensure_cloud_session_key()` → `self._check_cloud_api_key()` へメソッド名差し替え
- `_open_llm_config` の `LLMConfigDialog(...)` 呼び出しへ `session_api_keys=getattr(self.app, "_session_api_keys", None)` を1行追加し、OCRDialog 経由でも `LLMConfigDialog` が `app._session_api_keys` の実体を共有するよう配線（Plan 02 で確立した防御的パターンを踏襲し既存 `TestOpenLlmConfigDoubleLaunchGuard` の完全 SimpleNamespace スタブとの後方互換を維持）
- 不要化した `ocr_session_key_label` を `pagefolio/lang.py` の ja/en 両辞書から同時削除
- `tests/test_provider_ui.py` の `TestNeedsSessionKey`（6テスト）と `_make_dialog_stub` 内の `_needs_session_key` 束縛行を削除し、後継 `TestCheckCloudApiKey`（11テストケース: 非クラウド True/messagebox非呼び出し・claude/gemini/runpod の未解決時エラー表示/False・セッションキー優先解決・環境変数フォールバック解決・RunPod スロット誤格納なし回帰）を新設

## Task Commits

Each task was committed atomically:

1. **Task 1: 旧セッションキー UI/ヘルパーを撤去し _check_cloud_api_key へ置換・_open_llm_config を配線・不要 LANG キー削除** - `69a6b0f` (refactor)
2. **Task 2: TestNeedsSessionKey を削除し TestCheckCloudApiKey を新設** - `414668c` (test)

## Files Created/Modified

- `pagefolio/ocr_dialog.py` - `api_key_var`/`_key_frame`/`_needs_session_key`/`_ensure_cloud_session_key` を撤去、`_check_cloud_api_key` を新設し `_on_run`/`_on_summary` のゲート呼び出しを差し替え、`_open_llm_config` へ `session_api_keys` 配線、未使用 `os` import を削除
- `pagefolio/lang.py` - `ocr_session_key_label` を ja/en 両辞書から削除
- `tests/test_provider_ui.py` - `TestNeedsSessionKey` を削除し `TestCheckCloudApiKey` を新設（11テストケース）、`_make_dialog_stub` の `_needs_session_key` 束縛行を削除

## Decisions Made

- `_check_cloud_api_key` は「鍵の収集」と「鍵の存在確認」が同居していた旧 `_ensure_cloud_session_key` を分解し、値を一切保持・返却しない確認専用関数として実装（RESEARCH.md Pitfall 2 の指摘通り、単純削除では成功基準2の明示エラーが失われるため）
- `_open_llm_config` の `session_api_keys` 配線は Plan 02 の `app.py._open_settings` と同じ `getattr(self.app, "_session_api_keys", None)` 防御的パターンを踏襲（直接 `self.app._session_api_keys` を渡すと既存の完全 `SimpleNamespace` スタブを使う `TestOpenLlmConfigDoubleLaunchGuard::test_ocr_dialog_reuses_existing_llm_config_dialog` が `AttributeError` で壊れるため。実運用では `app.py:81` で必ず初期化済みのため挙動に影響なし）
- `_needs_session_key` 撤去で `os.environ` への参照が `ocr_dialog.py` から消滅したため、未使用となった `import os` を削除（ruff F401 対応。他の環境変数参照は全て `_resolve_api_key` 内に集約済みのため影響なし）
- `TestCheckCloudApiKey` は RunPod 固有の回帰テスト（`test_runpod_session_key_does_not_use_claude_slot`）を追加し、claude スロットのみにキーがある状態で runpod を選択しても解決できない（誤って claude 経由で解決しない）ことを明示的に確認する構造にした

## Deviations from Plan

None - plan executed exactly as written（`os` import の削除は撤去に伴う自然な後始末であり、CLAUDE.md のリント必須ルールに従った対応。新規逸脱ではない）

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1（APIキー入力欄・LLM設定への一元化）の全3プラン完了。V171-KEY-01〜04・V171-TEST-02 の要件をコード面で充足
- フルスイート 725 件グリーン（ベースライン720件 + Task 2 新規テスト再構成分の純増5件）・`ruff check . && ruff format --check .` クリーン確認済み
- Manual-Only 項目（環境変数・入力値とも未設定時のクラウドOCR実行エラー目視・旧キー入力欄非表示の目視・入力キーでのRunPod実クラウドOCR実行）は未実施（コード検証は完了・実描画/実API のみ未確認・実API課金を伴うため人手推奨のまま据え置き）

---
*Phase: 01-api-llm*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/ocr_dialog.py
- FOUND: pagefolio/lang.py
- FOUND: tests/test_provider_ui.py
- FOUND commit: 69a6b0f
- FOUND commit: 414668c
