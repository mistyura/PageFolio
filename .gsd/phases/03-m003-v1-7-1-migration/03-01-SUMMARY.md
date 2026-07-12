---
id: S01
parent: M003
milestone: M003
provides:
  - _resolve_api_key（pagefolio/ocr.py）の優先順を「セッションキー(入力値) → 環境変数」へ反転（claude/gemini/runpod 全分岐）
  - 反転仕様を固定する回帰テスト（claude/gemini 書き換え + RunPod 新設 TestResolveApiKeyRunPod）
  - 後続プラン（Plan 02 の入力欄・Plan 03 のエラー文言）が参照する新規/更新 LANG キー（ja/en）
  - LLMConfigDialog の claude/gemini/runpod 各セクションへのマスク付き APIキー入力欄（トグル + セッション限定注記）
  - LLMConfigDialog._apply による app._session_api_keys への同期（llm_settings 非流入を維持）
  - SettingsDialog 経由の session_api_keys 配線（app.py → settings.py → LLMConfigDialog）
  - _refresh_claude_models / _refresh_gemini_models / _refresh_runpod_models のライブ値優先キー解決
  - OCRDialog の旧セッションキー入力 UI（api_key_var/_key_frame）とヘルパー（_needs_session_key/_ensure_cloud_session_key）の完全撤去
  - 値収集をしない軽量ゲート _check_cloud_api_key（claude/gemini/runpod 3プロバイダの明示エラー・messagebox.showerror）
  - OCRDialog._open_llm_config → LLMConfigDialog(session_api_keys=...) の配線（OCRDialog 経路の session_api_keys 共有）
  - TestCheckCloudApiKey（TestNeedsSessionKey の後継・RunPod スロット誤格納なしの回帰テスト込み）
  - _confirm_cost / _confirm_summary_cost の runpod 分岐（正しい送信先ホスト・モデル開示）
  - _provider_display_name の runpod ローカライズ表示名（WR-02）
  - llm_runpod_host_unset / ocr_provider_name_runpod の ja/en LANG キー
  - TestConfirmCost の RunPod 送信先開示回帰テスト3件
requires: []
affects: []
key_files: []
key_decisions:
  - _resolve_api_key の優先順を claude/gemini/runpod 全分岐で「session_keys → 環境変数 → OCRAPIKeyError」へ反転（V171-KEY-02・シグネチャ不変）
  - gemini の dual env var 内部優先順（GEMINI_API_KEY 優先）は反転対象外として維持
  - 既存の env優先固定テスト（test_env_var_takes_priority_over_session_key 等）は新規追加ではなく書き換え・リネームで対応（Pitfall 4 の指摘通り）
  - llm_env_key_unset_static[_gemini/_runpod] のヒント文言も UI-SPEC の D-11 更新後文言へ ja/en 同時調整（新規キー追加はせず既存キーの text のみ更新）
  - ocr_session_key_label は本プランでは未削除（撤去対象 UI を撤去する Plan 03 と同一プランで削除し、実行時 KeyError の窓を作らない）
  - app.py._open_settings は self._session_api_keys を getattr(self, '_session_api_keys', None) 経由で渡す（既存の完全 SimpleNamespace テストスタブとの後方互換のための防御的コーディング・実運用では app.py:81 で必ず初期化済み）
  - SettingsDialog.__init__ は current_settings（dict(...) で複製）とは異なり session_api_keys を複製せず参照のまま保持（RESEARCH.md Pitfall 5 対応）
  - gemini の注記（D-07）は GEMINI_API_KEY 設定済みならその名を、無ければ GOOGLE_API_KEY を表示（既存 dual env var 優先順と整合）
  - Task 3 のテストは実 Tk ウィジェットを生成せず、_apply が参照する全属性を SimpleNamespace + 軽量 Get系スタブで埋めて LLMConfigDialog._apply を直接呼ぶ既存パターン（_call_update_ocr_buttons_state 等）を踏襲
  - _check_cloud_api_key は _is_cloud_provider() が偽なら無条件 True を返し、真なら _resolve_api_key(name, session_keys) の解決可否のみで判定する（値の保持・返却は一切しない）
  - OCRDialog._open_llm_config の LLMConfigDialog(...) 呼び出しへの session_api_keys 配線は、Plan 02 で確立した getattr(self.app, '_session_api_keys', None) の防御的パターンを踏襲（既存 TestOpenLlmConfigDoubleLaunchGuard の完全 SimpleNamespace スタブとの後方互換のため。実運用では app.py:81 で必ず初期化済み）
  - 撤去に伴い未使用となった os import を pagefolio/ocr_dialog.py から削除（ruff F401 対応）
  - ocr_session_key_label を ja/en 両辞書から同時削除（キー数一致を維持・test_lang_parity.py で担保）
  - runpod_model が空文字のとき見積りモデル名は 'runpod' 固定文字列にフォールバック（_lookup_price は未知モデルを _PRICE_FALLBACK で吸収し例外を投げない）
  - runpod_url 未設定時のプレースホルダは新規 LANG キー llm_runpod_host_unset とし、api.anthropic.com への誤フォールバックを避ける
patterns_established:
  - APIキー解決順反転はロジック層1関数（_resolve_api_key）への集約で全経路へ波及させる（UI層・実行ゲート層は再実装しない）
  - LLMConfigDialog の3セクション共通パターン（キー入力行 + トグル + 注記）は claude/gemini/runpod で完全に並行実装（analog は同ファイル内モデル選択行）
  - OCR実行前ゲートは「値を集めて格納する」責務を持たず「解決可否を確認するだけ」の関数に限定する（RunPod の claude スロット誤格納バグの再発を構造的に防止）
  - _make_confirm_stub（tests/test_provider_ui.py）を provider/runpod_url/runpod_model 引数で拡張し _confirm_summary_cost も束縛するパターン。以後 provider 別の送信先開示テストを追加する際はこのスタブを再利用する
observability_surfaces: []
drill_down_paths: []
duration: 約15分
verification_result: passed
completed_at: 2026-07-04
blocker_discovered: false
---
# S01: Api Llm

**# Phase 01 Plan 01: APIキー解決優先順反転 + LANG先行整備 Summary**

## What Happened

# Phase 01 Plan 01: APIキー解決優先順反転 + LANG先行整備 Summary

**`_resolve_api_key` の解決優先順を「環境変数優先」から「セッションキー(入力値)優先」へ反転し、claude/gemini書き換え + RunPod新設の回帰テストと、後続プラン参照用のLANGキー（ja/en）を整備**

## Performance

- **Duration:** 約5分
- **Tasks:** 3/3 completed
- **Files modified:** 3（pagefolio/ocr.py, tests/test_ocr.py, pagefolio/lang.py）

## Accomplishments
- `_resolve_api_key`（`pagefolio/ocr.py`）の claude/gemini/runpod 全分岐で「session_keys(入力値) → 環境変数 → OCRAPIKeyError」の順序へ反転。gemini の dual env var（GEMINI_API_KEY→GOOGLE_API_KEY）内部順序は不変。関数シグネチャ `(provider_name, session_keys)` も不変のため呼び出し元（build_provider・OCRDialog）は無変更で追従
- 既存の env優先固定テスト（`TestResolveApiKey`/`TestResolveApiKeyGemini`）を入力値優先の期待値へ書き換え（新規追加ではなくリネーム＋アサーション反転）、`TestResolveApiKeyRunPod` を新設（入力優先/環境変数フォールバック/raise の3ケース + os.environ 非書込み確認）
- 新規 LANG キー6件（`llm_api_key_label`/`llm_key_toggle_show`/`llm_key_toggle_hide`/`llm_key_session_note`/`llm_key_env_set_note`/`ocr_api_key_missing_runpod`）を ja/en 両辞書へ整備し、既存エラー文言2件（`ocr_api_key_missing`/`_gemini`）を LLM設定ダイアログ導線案内へ更新

## Task Commits

Each task was committed atomically:

1. **Task 1: 解決系テストを入力値優先へ書き換え + RunPod 版を新設** - `ea3e6f5` (test)
2. **Task 2: _resolve_api_key の優先順を反転（session_keys → 環境変数）** - `b13870b` (fix)
3. **Task 3: 新規/更新 LANG キーを ja/en 両辞書へ整備** - `82f6a06` (docs)

_Note: Task 1 was the RED phase (TDD) — 3 priority-flip tests intentionally failed until Task 2 (GREEN)._

## Files Created/Modified
- `tests/test_ocr.py` - `TestResolveApiKey`/`TestResolveApiKeyGemini` を入力値優先の期待値へ書き換え、`TestResolveApiKeyRunPod` を新設（4テスト）
- `pagefolio/ocr.py` - `_resolve_api_key` の claude/gemini/runpod 全分岐で session_keys を先に判定するよう反転。docstring も更新
- `pagefolio/lang.py` - 新規キー6件（ja/en）追加、既存エラー文言2件（`ocr_api_key_missing`/`_gemini`）とヒント文言3件（`llm_env_key_unset_static`系）をUI-SPEC準拠へ更新

## Decisions Made
- `_resolve_api_key` の優先順反転は関数内部の順序入替のみで実装し、シグネチャ・呼び出し元は無変更（RESEARCH.md Pattern 1 の推奨通り・全経路が一括で追従）
- gemini の dual env var 内部優先順（GEMINI_API_KEY 優先）は反転対象外として明示的に維持
- `llm_env_key_unset_static`系の既存ヒント文言は UI-SPEC の D-11 更新後文言（「APIキー未設定のため推奨モデル一覧を表示中…」）へ ja/en 同時更新（Task 3 の action 指示通り、キー追加なし・text のみ調整）
- `ocr_session_key_label` は本プランでは削除せず維持（撤去対象 UI 自体を撤去する Plan 03 と同一プランで削除する方針を継続）

## Deviations from Plan

None - plan executed exactly as written（ruff の E501 対応で `# noqa: E501` を既存コードベースの確立済みパターンに倣って一部テストdocstring/lang.py の長い行へ付与したのみ。これは既存の `pagefolio/ocr_dialog.py`/`pagefolio/ocr_providers.py` 等で使われている既存パターンの踏襲であり、新規逸脱ではない）

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02（LLMConfigDialog へのAPIキー入力欄追加）が参照する LANG キー（`llm_api_key_label` 等）は整備済み
- Plan 03（OCRDialog の旧セッションキー UI 撤去・エラー文言差し替え）が参照する `ocr_api_key_missing_runpod` と更新後の `ocr_api_key_missing`/`_gemini` 文言は整備済み。`ocr_session_key_label` の削除は Plan 03 の撤去タスクと同時実施が前提
- フルスイート 712 件グリーン（ベースライン707件 + 新規5件）・`ruff check . && ruff format .` クリーン確認済み

---
*Phase: 01-api-llm*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: pagefolio/ocr.py
- FOUND: tests/test_ocr.py
- FOUND: pagefolio/lang.py
- FOUND commit: ea3e6f5
- FOUND commit: b13870b
- FOUND commit: 82f6a06

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

# Phase 1 Plan 4: RunPod送信先確認ダイアログのCR-01ギャップ閉塞 Summary

**`_confirm_cost`/`_confirm_summary_cost` に `elif name == "runpod":` 分岐を追加し、RunPod選択時に `api.anthropic.com`/claudeモデルを誤開示していたCritical欠陥（01-REVIEW.md CR-01）を解消**

## Performance

- **Duration:** 約15分
- **Started:** 2026-07-04T17:01:00Z (概算)
- **Completed:** 2026-07-04T17:16:42Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `_confirm_cost`/`_confirm_summary_cost` の両方に `elif name == "runpod":` 分岐を追加し、host は `runpod_url`、model（`_confirm_cost` のみ）は `runpod_model` から取得するよう修正（CR-01解消）
- `runpod_url` 未設定時は新規 LANG キー `llm_runpod_host_unset` のプレースホルダを表示し、`api.anthropic.com` への誤フォールバックを構造的に排除
- `_provider_display_name` に runpod 分岐を追加し、生の `"runpod"` 文字列ではなくローカライズ済み `ocr_provider_name_runpod`（"RunPod (Serverless)"）を返すよう修正（WR-02）
- `TestConfirmCost` を拡張し、RunPod選択時の送信先/モデル開示・未設定時プレースホルダの3ケースを回帰テストとして追加。既存claude/geminiケースは無改変で継続グリーン

## Task Commits

Each task was committed atomically:

1. **Task 1: _confirm_cost / _confirm_summary_cost に runpod 分岐を追加し、_provider_display_name の runpod 表示名と新規 LANG キーを整備する** - `9f13287` (fix)
2. **Task 2: TestConfirmCost を拡張し、_confirm_cost / _confirm_summary_cost の runpod 送信先開示を回帰テストで担保する** - `117ca42` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `pagefolio/ocr_dialog.py` - `_confirm_cost`/`_confirm_summary_cost` に runpod 分岐追加・`_provider_display_name` に runpod 分岐追加
- `pagefolio/lang.py` - `llm_runpod_host_unset`・`ocr_provider_name_runpod` を ja/en 両辞書に追加
- `tests/test_provider_ui.py` - `_make_confirm_stub` を provider/runpod_url/runpod_model 引数へ拡張し `_confirm_summary_cost` も束縛。RunPod送信先開示の回帰テスト3件を追加

## Decisions Made
- runpod_model が空文字/未設定のとき見積りモデル名は固定文字列 `"runpod"` にフォールバック（`_lookup_price` は未知モデルでも `_PRICE_FALLBACK` を返し例外を投げないため安全）
- `_confirm_summary_cost` は元々 model を扱わない（char_count のみ）ため、runpod 分岐は host のみ算出（`_confirm_cost` と非対称だが元設計を踏襲）

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 01-REVIEW.md の CR-01（Critical・唯一のBlocker）を解消。フルスイート 728 件グリーン（725 baseline + 3 新規）・`ruff check .`/`ruff format --check .` ともにクリーン
- 残る WR-01/WR-03/WR-04（Warning・本フェーズ範囲外の既存挙動）は今回のスコープ外として次回棚卸し対象に据え置き
- Manual-Only 項目（RunPod実クラウドOCR/サマリの実描画目視3件）は人手確認待ちだが非ブロッキング

---
*Phase: 01-api-llm*
*Completed: 2026-07-04*

## Self-Check: PASSED

- FOUND: .planning/phases/01-api-llm/01-04-SUMMARY.md
- FOUND: commit 9f13287
- FOUND: commit 117ca42
