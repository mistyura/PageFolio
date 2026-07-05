---
phase: 01-api-llm
verified: 2026-07-05T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/5 (with 1 blocker gap outside the strict truth count)
  gaps_closed:
    - "RunPod のクラウド送信前確認ダイアログ（_confirm_cost / _confirm_summary_cost）が正しい送信先ホスト・モデルを開示する（01-REVIEW.md CR-01・旧 01-VERIFICATION.md gaps[0]）"
  gaps_remaining: []
  regressions: []
---

# Phase 1: APIキー入力欄（LLM設定への一元化） Verification Report

**Phase Goal:** ユーザーは Claude / Gemini / RunPod の APIキーを LLM 設定ダイアログで一元的に入力でき、キーは「入力値 → 環境変数」の優先順で解決される（セッション限定・非永続）。
**Verified:** 2026-07-05T00:00:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plan 01-04 closed the CR-01 RunPod send-to-host disclosure gap recorded in the previous 01-VERIFICATION.md)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ユーザーは LLM設定ダイアログで Claude/Gemini/RunPod の APIキーを入力でき、その入力キーでクラウド OCR を実行できる（settings.json 非保存） | ✓ VERIFIED | `pagefolio/dialogs/llm_config.py` の claude/gemini/runpod 各セクションに `*_api_key_var` (`tk.Entry(show="*")`, lines 371-389/469-487/566-584) + プリフィル + トグルが実装済み。`_apply()`（:1404-1415）が非空入力を `self._session_api_keys[provider]` へ格納・空欄で `pop`。`llm_settings` dict には api_key 系キーが一切追加されない（コード再読で確認）。`TestApiKeyNotInSettings`/`TestSessionKeyStoreAndClear`/`TestRunpodSessionKeySlot` が pytest でグリーン |
| 2 | キー解決は「ダイアログ入力値 → 環境変数」の優先順で行われ（現行の環境変数優先から反転）、両方未設定でクラウド OCR を開始すると明示的なエラーが表示される | ✓ VERIFIED | `pagefolio/ocr.py::_resolve_api_key`（:209-268）を実読：claude/gemini/runpod 全分岐で `session_keys.get(...)` を先に判定し、非空ならそれを返す。未設定時のみ `os.environ.get(...)` にフォールバック（gemini の dual env var 内部順序 GEMINI_API_KEY→GOOGLE_API_KEY は維持）。両方未設定なら `OCRAPIKeyError` を raise。`os.environ` への書き込みコードパスは存在しない。`_check_cloud_api_key`（ocr_dialog.py:1088-1122）が3プロバイダで未解決時に `messagebox.showerror` を出し False を返す。`TestResolveApiKey`/`TestResolveApiKeyGemini`/`TestResolveApiKeyRunPod`/`TestCheckCloudApiKey` が全件 pytest でグリーン（実行確認: 18/18 対象テスト PASS） |
| 3 | OCRDialog に旧セッションキー入力欄が存在せず、キー設定の導線が LLM設定ダイアログに一元化されている（OCR 実行フローは従来どおり動作する） | ✓ VERIFIED | `grep -n "_needs_session_key|_ensure_cloud_session_key|_key_frame|api_key_var\b" pagefolio/ocr_dialog.py` → 0件（実行確認）。`_open_llm_config` が `session_api_keys=getattr(self.app, "_session_api_keys", None)` を `LLMConfigDialog` へ配線（ocr_dialog.py:839）。フルスイート 728 件グリーンで OCR 実行・サマリ・キャンセル・進捗・リトライの既存フローに回帰なし |
| 4 | RunPod も `_session_api_keys` のセッションキー機構で扱え、環境変数 `RUNPOD_API_KEY` なしでも入力キーだけで OCR を実行できる | ✓ VERIFIED | `_resolve_api_key("runpod", session_keys)` が `session_keys["runpod"]` を最優先で解決（ocr.py:257-265）。`llm_config.py` の runpod セクションにも同型の入力欄・`_apply` 同期あり。`TestRunpodSessionKeySlot`（3件）・`TestCheckCloudApiKey::test_runpod_session_key_does_not_use_claude_slot` が PASS。旧 `_ensure_cloud_session_key` の claude スロット誤格納バグ（Pitfall 1）は関数自体の撤去により構造的に消滅（コード上に痕跡なし） |
| 5 | 優先順解決（入力値→環境変数→エラー）と `_SENSITIVE_KEYS` 非保存ガードの回帰テストが pytest でグリーン（V171-TEST-02） | ✓ VERIFIED | 本検証で `python -m pytest -q` を実行し **728 passed**（前回検証の725件 + Plan 04 の新規3件、SUMMARY 記載と一致）。`ruff check .` / `ruff format --check .` ともにクリーン（実行確認）。`tests/test_settings_keyguard.py`・`tests/test_lang_parity.py` も本検証内で回帰確認済み（フルスイートに含まれ全件 PASS） |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Gap Closure Confirmation（前回 01-VERIFICATION.md からの再検証）

前回検証（2026-07-04T16:48:17Z）で `gaps_found` の唯一の理由だった 01-REVIEW.md CR-01（RunPod 選択時に `_confirm_cost`/`_confirm_summary_cost` が誤って `api.anthropic.com`/Claude モデルを開示する透明性欠陥）は、01-04 プラン（gap_closure: true）で解消されたことを本検証で実コード読解 + テスト実行により確認した。

| 項目 | 状態 | 証拠 |
|------|------|------|
| `_confirm_cost` が RunPod で `runpod_url`/`runpod_model` を開示（api.anthropic.com へフォールスルーしない） | ✓ 解消確認 | `pagefolio/ocr_dialog.py:1030-1043` に `elif name == "runpod":` 分岐実在。`self.app.settings.get("runpod_url", "") or self._L["llm_runpod_host_unset"]` / `self.app.settings.get("runpod_model", "") or "runpod"` |
| `_confirm_summary_cost` が RunPod で `runpod_url` を開示 | ✓ 解消確認 | `pagefolio/ocr_dialog.py:1067-1077` に同型の `elif name == "runpod":` 分岐実在 |
| runpod_url 未設定時は `llm_runpod_host_unset` プレースホルダ表示（api.anthropic.com にフォールバックしない） | ✓ 解消確認 | 上記コード + `pagefolio/lang.py` に ja/en 両方で `llm_runpod_host_unset` 存在（:503, :1079） |
| RunPod 送信先開示の回帰テスト | ✓ 解消確認 | `TestConfirmCost::test_confirm_cost_runpod_shows_runpod_host` / `test_confirm_summary_cost_runpod_shows_runpod_host` / `test_confirm_cost_runpod_url_unset_shows_placeholder` の3件が pytest で PASS（実行確認） |
| `_provider_display_name` の runpod ローカライズ表示名（WR-02・任意） | ✓ 解消確認 | `pagefolio/ocr_dialog.py:709-710` に `if name == "runpod": return self._L["ocr_provider_name_runpod"]`。ja/en 両辞書に `ocr_provider_name_runpod`（:454, :1030）存在 |

回帰（regressions）: なし。既存 claude/gemini ケースの `TestConfirmCost` 4件も継続 PASS。

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/ocr.py::_resolve_api_key` | 優先順反転（session_keys→env→raise）、シグネチャ不変 | ✓ VERIFIED | 3分岐すべて反転済み・`os.environ` 書込みコードパスなし（実読確認） |
| `pagefolio/dialogs/llm_config.py` | 3セクションの APIキー欄・トグル・注記・_apply同期・ライブ値モデル取得 | ✓ VERIFIED | `*_api_key_var`/`*_api_key_entry`/`_apply`同期ループ(:1404-1415)/`_refresh_*_models`のライブ値解決(:1218,1256,1294)すべて実装確認 |
| `pagefolio/app.py::_open_settings` | `session_api_keys` を `SettingsDialog` へ配線 | ✓ VERIFIED | `session_api_keys=getattr(self, "_session_api_keys", None)`（app.py:481） |
| `pagefolio/dialogs/settings.py` | `session_api_keys` を保持し `LLMConfigDialog` へ中継 | ✓ VERIFIED | `__init__` 複製せず保持（:41-44）、`_open_llm_config` で中継（:206） |
| `pagefolio/ocr_dialog.py::_check_cloud_api_key` | 値収集をしない軽量ゲート | ✓ VERIFIED | `_on_run`/`_on_summary` の両ゲートで呼び出し確認済み（:1088-1122） |
| `pagefolio/ocr_dialog.py::_confirm_cost` / `_confirm_summary_cost` | runpod 分岐を持ち host/model を正しく開示（CR-01解消） | ✓ VERIFIED | :1030-1043 / :1067-1077 に elif runpod 分岐実在 |
| `pagefolio/lang.py`（新規/更新キー） | ja/en 同一キーで整備 | ✓ VERIFIED | `llm_api_key_label`/`llm_key_toggle_show`/`llm_key_toggle_hide`/`llm_key_session_note`/`llm_key_env_set_note`/`ocr_api_key_missing_runpod`/`llm_runpod_host_unset`/`ocr_provider_name_runpod` すべて ja/en 存在確認済み。`ocr_session_key_label` は ja/en 両方から削除確認済み（grep 0件） |
| `tests/test_ocr.py::TestResolveApiKeyRunPod` | 新設（3ケース+非書込み） | ✓ VERIFIED | 収集4テスト（フルスイートに含まれ PASS） |
| `tests/test_provider_ui.py::TestCheckCloudApiKey` | `TestNeedsSessionKey`後継 | ✓ VERIFIED | 11ケース PASS（実行確認）。`TestNeedsSessionKey` は0件 |
| `tests/test_provider_ui.py::TestConfirmCost` | RunPod送信先開示3件を含む | ✓ VERIFIED | 既存4件+新規3件=7件、実行確認で全PASS |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `LLMConfigDialog._apply` | `app._session_api_keys` | 直接dict同期（llm_settings非経由） | ✓ WIRED | `_apply()` ループで確認済み。`llm_settings` に `api_key` を含むキーが存在しないことを再読で確認 |
| `app._open_settings` | `SettingsDialog` → `LLMConfigDialog` | `session_api_keys=` 引数の3段階配線 | ✓ WIRED | app.py→settings.py→llm_config.py の3段階すべてで参照渡し（複製なし）確認済み |
| `OCRDialog._on_run`/`_on_summary` | `_check_cloud_api_key` → `_resolve_api_key` | ゲート呼び出し | ✓ WIRED | 実コードで両呼び出し箇所確認済み |
| `OCRDialog._open_llm_config` | `LLMConfigDialog(session_api_keys=...)` | 1行配線 | ✓ WIRED | 確認済み |
| `_confirm_cost`/`_confirm_summary_cost` | `self.app.settings.get("runpod_url"/"runpod_model")` | runpod 分岐 | ✓ WIRED | 確認済み（CR-01解消の核心配線） |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| V171-KEY-01 | 01-02, 01-04 | LLM設定ダイアログでAPIキー入力・非永続 | ✓ SATISFIED | 3セクションの入力欄・トグル・非流入テスト |
| V171-KEY-02 | 01-01, 01-03, 01-04 | 入力値→環境変数の優先順反転・明示エラー | ✓ SATISFIED | `_resolve_api_key`反転・`_check_cloud_api_key`のエラー表示 |
| V171-KEY-03 | 01-03 | OCRDialog旧キー欄撤去・導線一元化 | ✓ SATISFIED | 旧UI/ヘルパー0件・`_open_llm_config`配線 |
| V171-KEY-04 | 01-01, 01-02, 01-03, 01-04 | RunPodもセッションキー機構で扱える | ✓ SATISFIED | スロット格納/解決が正しく機能し、送信前確認ダイアログの開示欠陥（CR-01）も01-04で解消済み |
| V171-TEST-02 | 01-01, 01-02, 01-03, 01-04 | 優先順解決・非保存ガードの回帰テスト整備 | ✓ SATISFIED | フルスイート728件グリーン・ruffクリーン（本検証で実行確認） |

要件トレーサビリティ: REQUIREMENTS.md の Phase 1 マッピング（V171-KEY-01〜04, V171-TEST-02）と各PLANのrequirements frontmatterが完全一致。孤立要件なし。

### Anti-Patterns Found

本フェーズ変更ファイル（`pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/llm_config.py`, `pagefolio/dialogs/settings.py`, `pagefolio/app.py`, `pagefolio/lang.py`, `tests/test_ocr.py`, `tests/test_provider_ui.py`）に TBD/FIXME/XXX の債務マーカーなし（grep実行確認・`tests/test_provider_ui.py:315` の "X.XXX" ヒットはコストのプレースホルダ表記の一部であり誤検知）。

01-REVIEW.md に記載の CR-01（新規発見・Python 3.8 型ヒント互換性バグ、`pagefolio/ocr_dialog.py:31,63` の `dict[str, ...]`/`tuple[...]` 直接サブスクリプト）は本フェーズのタスク指示（note）に従い、本フェーズのスコープ（APIキー入力導線・優先順解決）に対する成功基準へ影響しない既存不具合として扱い、フェーズゲートの gap とはしない。ただし将来対応が必要な既知の技術的負債として記録する（次フェーズ以降での棚卸し対象）。

WR-01〜WR-05（Ollama クラウド判定・OCR進捗カウント・コスト見積りフォールバック等）も同様に本フェーズのAPIキー機能の成功基準に影響しないため gap 扱いとしない。

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_resolve_api_key`の反転仕様（claude/gemini/runpod） | `pytest tests/test_ocr.py -k "ResolveApiKey" -q` | 含むフルスイートで確認 | ✓ PASS |
| `_check_cloud_api_key`/`_confirm_cost`系の18件 | `pytest tests/test_provider_ui.py -k "ConfirmCost or CheckCloudApiKey" -v` | 18 passed | ✓ PASS |
| フルスイート回帰 | `pytest -q` | 728 passed | ✓ PASS |
| リント/フォーマット | `ruff check . && ruff format --check .` | クリーン | ✓ PASS |

### Human Verification Required

前回検証と同様、以下は各PLANのManual-Onlyセクションに明記され実施は人手・非ブロッキングとされている項目（コード面の検証は完了済み・フェーズ status には影響しない）:

1. **APIキー入力欄のマスク表示・トグル実描画**（Tkinter 実レンダリング品質）
2. **入力直後のモデル取得によるキー疎通確認（D-10・実APIコール）**
3. **設定メニュー経由・OCR画面経由の双方で同一挙動（配線対称性の目視）**
4. **RunPod送信前確認ダイアログの実描画目視（runpod_url表示・未設定時プレースホルダ表示）**
5. **RunPod実クラウドOCR実行（実API・課金を伴う）**

これらは all-code-path-verified の上での目視確認のみであり、status 判定には計上しない（Step 8 の "Always needs human" 分類・非ブロッキング）。

### Gaps Summary

前回検証（01-VERIFICATION.md, 2026-07-04T16:48:17Z）で `gaps_found` の原因だった唯一のギャップ（01-REVIEW.md CR-01・RunPod送信前確認ダイアログの誤開示）は、01-04プラン（gap_closure: true）により完全に解消されたことを本検証で実コード読解 + 回帰テスト実行により確認した。5つのROADMAP成功基準すべてが実コード・実テスト実行で VERIFIED。フルスイート728件グリーン・ruffクリーン。要件 V171-KEY-01〜04・V171-TEST-02 すべて SATISFIED。孤立要件・回帰・新規ブロッカーなし。

01-REVIEW.md記載の新規CR-01（Python 3.8型ヒント互換性）・WR-01〜05は本フェーズのタスク指示により対象外（フェーズ成功基準に影響しないスコープ外の既存/独立不具合）として扱った。

---

_Verified: 2026-07-05T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
