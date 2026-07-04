---
phase: 01-api-llm
verified: 2026-07-04T16:48:17Z
status: gaps_found
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "RunPod のクラウド送信前確認ダイアログ（_confirm_cost / _confirm_summary_cost）が正しい送信先ホスト・モデルを開示する（透明性・成功基準1『実行できる』の前提となるコスト/送信先の正確な開示）"
    status: failed
    reason: "01-REVIEW.md CR-01（Critical・severity未対応）: pagefolio/ocr_dialog.py の _confirm_cost（:1012）と _confirm_summary_cost（:1048）は `if name == \"gemini\": ... else: # claude` の2分岐のみで runpod 分岐が存在しない。_is_cloud_provider() は runpod もクラウド扱いするため、RunPod 選択時にもこの2メソッドが呼ばれ、else 節に落ちて host=\"api.anthropic.com\"・model=claude_model が表示される。実際の送信先は self.app.settings.get(\"runpod_url\") であり、ユーザーは誤った送信先/コストの開示のまま実行を承認させられる。レビュー日（2026-07-05）以降、ocr_dialog.py に対する追加コミットは無く（`git log --oneline -- pagefolio/ocr_dialog.py` で確認）、本フェーズの成果物提出時点で未修正のまま残っている。RunPod はこのフェーズが APIキー入力導線を新設した対象プロバイダの一つであり、スコープ内の欠陥である。"
    artifacts:
      - path: "pagefolio/ocr_dialog.py:1012-1046 (_confirm_cost)"
        issue: "runpod 分岐が無く、RunPod選択時に claude の host/model を誤表示する"
      - path: "pagefolio/ocr_dialog.py:1048-1071 (_confirm_summary_cost)"
        issue: "同上（サマリ生成の送信前確認でも同じ誤表示）"
    missing:
      - "_confirm_cost / _confirm_summary_cost へ `elif name == \"runpod\":` 分岐を追加し、host は self.app.settings.get(\"runpod_url\", ...)、model は self.app.settings.get(\"runpod_model\", ...) を使う"
      - "RunPod 選択時に表示される host/model が runpod_url/runpod_model と一致することを assert する回帰テスト（TestConfirmCost は現状 claude ケースのみ）"
      - "（任意・WR-02 関連）ocr_provider_name_runpod の LANG キー追加と _provider_display_name への runpod 分岐追加"
---

# Phase 1: APIキー入力欄（LLM設定への一元化） Verification Report

**Phase Goal:** ユーザーは Claude / Gemini / RunPod の APIキーを LLM 設定ダイアログで一元的に入力でき、キーは「入力値 → 環境変数」の優先順で解決される（セッション限定・非永続）。
**Verified:** 2026-07-04T16:48:17Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ユーザーは LLM設定ダイアログで Claude/Gemini/RunPod の APIキーを入力でき、その入力キーでクラウド OCR を実行できる（settings.json 非保存） | ✓ VERIFIED | `pagefolio/dialogs/llm_config.py` に3セクション全てで `*_api_key_var`(`tk.Entry(show="*")`) + トグル + 注記が実装済み（claude:462-517, gemini:559-614, runpod:358-413）。`_apply()`（:1400-1415）が `self._session_api_keys` へ同期し `llm_settings` dict には含めない。`tests/test_provider_ui.py::TestApiKeyNotInSettings`（2件）が PASS |
| 2 | キー解決は「ダイアログ入力値 → 環境変数」の優先順で行われ、両方未設定なら明示エラー | ✓ VERIFIED | `pagefolio/ocr.py::_resolve_api_key`（:209-267）実コードで claude/gemini/runpod 全分岐が `session_keys.get(...)` を先に判定し、未設定時のみ `os.environ.get(...)` へフォールバック、両方無ければ `OCRAPIKeyError` を raise。`_check_cloud_api_key`（`ocr_dialog.py:1073`）が3プロバイダで `messagebox.showerror` を表示し実行を中断。`TestResolveApiKey`/`TestResolveApiKeyGemini`/`TestResolveApiKeyRunPod`（15件）・`TestCheckCloudApiKey`（11件）が PASS |
| 3 | OCRDialog に旧セッションキー入力欄が存在せず、キー設定導線が LLM設定ダイアログに一元化されている | ✓ VERIFIED | `grep -n "_needs_session_key\|_ensure_cloud_session_key\|_key_frame\|api_key_var" pagefolio/ocr_dialog.py` が0件。`_open_llm_config` が `session_api_keys=getattr(self.app, "_session_api_keys", None)` を `LLMConfigDialog` へ配線（実コード確認済み） |
| 4 | RunPod も `_session_api_keys` のセッションキー機構で扱え、環境変数なしでも入力キーだけで OCR を実行できる | ✓ VERIFIED | `_resolve_api_key("runpod", ...)` が session_keys["runpod"] を最優先で解決。`TestRunpodSessionKeySlot`（3件）・`TestCheckCloudApiKey::test_runpod_session_key_does_not_use_claude_slot` が PASS。旧 `_ensure_cloud_session_key` の claude スロット誤格納バグ（Pitfall 1）は関数自体の撤去により構造的に消滅 |
| 5 | 優先順解決・`_SENSITIVE_KEYS` 非保存ガードの回帰テストが pytest でグリーン | ✓ VERIFIED | フルスイート `python -m pytest -q` → **725 passed**（実行確認済み）。`ruff check .` / `ruff format --check .` ともにクリーン（実行確認済み）。`tests/test_settings_keyguard.py`（17件）・`tests/test_lang_parity.py` も PASS |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pagefolio/ocr.py::_resolve_api_key` | 優先順反転（session_keys→env→raise）、シグネチャ不変 | ✓ VERIFIED | 実装確認済み（3分岐すべて反転・os.environ書込みコードパス無し） |
| `pagefolio/dialogs/llm_config.py` | 3セクションの APIキー欄・トグル・注記・_apply同期・ライブ値モデル取得 | ✓ VERIFIED | `*_api_key_var`/`*_api_key_entry`/トグル関数/`_apply`同期ループ/`_refresh_*_models`のライブ値解決すべて実装確認 |
| `pagefolio/app.py::_open_settings` | `session_api_keys` を `SettingsDialog` へ配線 | ✓ VERIFIED | `session_api_keys=getattr(self, "_session_api_keys", None)`（app.py:481） |
| `pagefolio/dialogs/settings.py` | `session_api_keys` を保持し `LLMConfigDialog` へ中継 | ✓ VERIFIED | `__init__`複製せず保持（:43-44）、`_open_llm_config`で中継（:206） |
| `pagefolio/ocr_dialog.py::_check_cloud_api_key` | 値収集をしない軽量ゲート | ✓ VERIFIED | 実装確認済み（`_on_run`:1132・`_on_summary`:1813 の両ゲートで呼び出し） |
| `pagefolio/lang.py`（新規/更新キー） | ja/en 同一キーで整備 | ✓ VERIFIED | `llm_api_key_label`/`llm_key_toggle_show`/`llm_key_toggle_hide`/`llm_key_session_note`/`llm_key_env_set_note`/`ocr_api_key_missing_runpod` ともに ja/en 存在確認済み。`ocr_session_key_label` は ja/en 両方から削除確認済み（grep 0件） |
| `tests/test_ocr.py::TestResolveApiKeyRunPod` | 新設（3ケース+非書込み） | ✓ VERIFIED | 収集で4テスト確認（`--collect-only`） |
| `tests/test_provider_ui.py::TestCheckCloudApiKey` | `TestNeedsSessionKey`後継 | ✓ VERIFIED | 収集で11テスト確認。`TestNeedsSessionKey`は0件（撤去済み） |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `LLMConfigDialog._apply` | `app._session_api_keys` | 直接dict同期（llm_settings非経由） | ✓ WIRED | `_apply()`ループで確認済み。`api_key`系キーが`llm_settings`に含まれないことをテストで担保 |
| `app._open_settings` | `SettingsDialog` → `LLMConfigDialog` | `session_api_keys=`引数の3段階配線 | ✓ WIRED | app.py→settings.py→llm_config.py の3段階すべてで参照渡し（複製なし）確認済み |
| `OCRDialog._on_run`/`_on_summary` | `_check_cloud_api_key` → `_resolve_api_key` | ゲート呼び出し | ✓ WIRED | 実コードで両呼び出し箇所確認済み |
| `OCRDialog._open_llm_config` | `LLMConfigDialog(session_api_keys=...)` | 1行配線 | ✓ WIRED | 確認済み |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| V171-KEY-01 | 01-02 | LLM設定ダイアログでAPIキー入力・非永続 | ✓ SATISFIED | 3セクションの入力欄・トグル・非流入テスト |
| V171-KEY-02 | 01-01, 01-03 | 入力値→環境変数の優先順反転・明示エラー | ✓ SATISFIED | `_resolve_api_key`反転・`_check_cloud_api_key`のエラー表示 |
| V171-KEY-03 | 01-03 | OCRDialog旧キー欄撤去・導線一元化 | ✓ SATISFIED | 旧UI/ヘルパー0件・`_open_llm_config`配線 |
| V171-KEY-04 | 01-01, 01-02, 01-03 | RunPodもセッションキー機構で扱える | ✓ SATISFIED (with caveat) | スロット格納/解決は正しく機能。ただし関連するRunPod送信前確認ダイアログの開示内容に未解決の欠陥あり（下記CR-01） |
| V171-TEST-02 | 01-01, 01-02, 01-03 | 優先順解決・非保存ガードの回帰テスト整備 | ✓ SATISFIED | フルスイート725件グリーン・ruffクリーン（実行確認済み） |

要件トレーサビリティ: REQUIREMENTS.md の Phase 1 マッピング（V171-KEY-01〜04, V171-TEST-02）と各PLANのrequirements frontmatterが完全一致。孤立要件なし。

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pagefolio/ocr_dialog.py` | 1012-1046 (`_confirm_cost`) | runpod分岐の欠落による誤った送信先/モデル開示（01-REVIEW.md CR-01） | 🛑 Blocker | RunPod選択時に `api.anthropic.com`（Claudeの送信先）を誤表示。ユーザーが実際の送信先（`runpod_url`）を認識できないままクラウド送信を承認する（セキュリティ/透明性上の欠陥）。レビュー後も未修正 |
| `pagefolio/ocr_dialog.py` | 1048-1071 (`_confirm_summary_cost`) | 同上（サマリ生成側） | 🛑 Blocker | 同上 |
| `pagefolio/ocr_dialog.py` | 693-710 (`_provider_display_name`) | RunPod用ローカライズ表示名が無く生の`"runpod"`文字列を返す（01-REVIEW.md WR-02） | ⚠️ Warning | UI表示の一貫性欠如。機能ブロッカーではない |
| `pagefolio/ocr_dialog.py` | 1096-1104 (`_check_cloud_api_key`内`env_var`dict) | gemini/runpodの`env_var`値が`{env_var}`プレースホルダを持たない文言に対して未使用（01-REVIEW.md WR-03） | ⚠️ Warning | Dead code的な保守リスクのみ。実行時エラーなし |
| `pagefolio/dialogs/llm_config.py` | 75, 969-981 | `_last_valid_provider`初期化がTesseract利用不可時に自己参照フォールバックとなる（01-REVIEW.md WR-01） | ⚠️ Warning | 本フェーズの新規コードではなく既存挙動。本フェーズのAPIキー機能とは独立 |
| `pagefolio/ocr_dialog.py` | 920-936 (`_apply_llm_settings`) | provider="off"切替時にRun/Resumeボタンが無効化されない（01-REVIEW.md WR-04） | ⚠️ Warning | 本フェーズ範囲外の既存挙動 |

**Debt markers（TBD/FIXME/XXX）:** 本フェーズ変更ファイル（`pagefolio/ocr.py`, `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/llm_config.py`, `pagefolio/dialogs/settings.py`, `pagefolio/app.py`, `pagefolio/lang.py`, `tests/test_ocr.py`, `tests/test_provider_ui.py`）に該当なし（grep実行確認済み）。

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_resolve_api_key`の反転仕様（claude/gemini/runpod） | `pytest tests/test_ocr.py -k "ResolveApiKey" -q` | 全15件PASS | ✓ PASS |
| `_check_cloud_api_key`の3プロバイダ分岐 | `pytest tests/test_provider_ui.py -k "CheckCloudApiKey" -q` | 全11件PASS | ✓ PASS |
| APIキー非流入・格納/クリア・RunPodスロット | `pytest tests/test_provider_ui.py -k "ApiKeyNotInSettings or SessionKeyStoreAndClear or RunpodSessionKeySlot" -q` | 全8件PASS | ✓ PASS |
| `test_lang_parity` | `pytest tests/test_lang_parity.py -q` | PASS | ✓ PASS |
| フルスイート回帰 | `pytest -q` | 725 passed | ✓ PASS |
| リント/フォーマット | `ruff check . && ruff format --check .` | クリーン | ✓ PASS |

### Human Verification (Deferred / Manual-Only — informational, non-blocking per plan)

以下は各PLANのManual-Onlyセクションに記載され、実施は明示的に人手・非ブロッキングとされている項目（コード面の検証は完了済み）:

1. **APIキー入力欄のマスク表示・トグル実描画**
   - Test: アプリ起動 → LLM設定ダイアログ → claude/gemini/runpod各セクションで表示/隠すトグルを目視
   - Expected: 常時マスク表示、トグルで平文表示切替
   - Why human: Tkinter実レンダリング品質は自動化不可

2. **入力直後のモデル取得によるキー疎通確認（D-10）**
   - Test: 環境変数未設定でダイアログにキー入力 → 再オープンでマスク付きプリフィル確認 → モデル取得ボタンで疎通確認
   - Expected: ライブ入力値で疎通確認が成功する
   - Why human: 実APIコール・実描画が必要

3. **設定メニュー経由・OCR画面経由の双方で同一挙動（配線対称性）**
   - Test: 「設定」メニュー経由・OCR画面「⚙ LLM設定…」経由の双方で入力・保存挙動を目視比較
   - Expected: 両経路で同一の`_session_api_keys`実体を共有した挙動
   - Why human: 目視によるUI対称性確認

4. **鍵未設定時のクラウドOCR実行エラー目視 + 旧UI非表示確認**
   - Test: 環境変数・入力値とも未設定でclaude/gemini/runpodのクラウドOCRを実行 → D-08導線案内エラー表示を確認。旧「APIキー（このセッションのみ…）」入力欄が表示されないことを確認
   - Expected: 明示エラー表示・実行中断、旧UI非表示
   - Why human: 実行時UIの目視確認

5. **RunPod実クラウドOCR実行（実API・課金を伴う）**
   - Test: 入力キー（環境変数なし）でRunPod実クラウドOCRを実行
   - Expected: 入力キーのみでOCRが成功する
   - Why human: 実API呼び出し・課金を伴うため

### Gaps Summary

コード面の5成功基準（V171-KEY-01〜04・V171-TEST-02）はすべて実コード・実テスト実行で確認済み（フルスイート725件グリーン・ruffクリーン）。

しかし、01-REVIEW.md で指摘された **CR-01（Critical・未修正）** が本フェーズのスコープ内（RunPodのAPIキー機構そのもの）に存在する: `_confirm_cost`/`_confirm_summary_cost` が RunPod 選択時に誤って Claude の送信先ホスト（`api.anthropic.com`）とモデルのコスト見積りを表示し、実際の送信先（ユーザー設定の `runpod_url`）を開示しない。レビュー報告（`01-REVIEW.md`、2026-07-05作成）以降、`pagefolio/ocr_dialog.py` への追加コミットは存在せず、未修正のまま本フェーズが完了として提出されている。

この欠陥はRunPodのOCR実行そのものをブロックしない（入力キーでの実行自体は成功する）ため、ROADMAP.md の5つの成功基準の字義通りの充足は妨げないが、この機能（RunPodのAPIキー導線）が本フェーズの3本柱の一つであること、Criticalな透明性/セキュリティ上の欠陥であること、レビューで名指しされ未対応のまま残っていることから、gaps_found として扱い次フェーズ着手前の対応を推奨する。

**This looks intentional? No.** 実装漏れであり、意図的な設計判断の痕跡（コメント・SUMMARY記載）はない。overrideではなく修正を推奨する。

---

_Verified: 2026-07-04T16:48:17Z_
_Verifier: Claude (gsd-verifier)_
