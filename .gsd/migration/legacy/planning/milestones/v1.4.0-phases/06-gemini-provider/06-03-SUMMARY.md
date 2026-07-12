---
phase: 06-gemini-provider
plan: "03"
subsystem: ocr-provider-ui
tags: [gemini, ocr, ui, settings, provider-selection, cost-confirm, session-key, ocr-scale]
dependency_graph:
  requires:
    - Plan 06-01 (GeminiProvider クラス・build_provider・_resolve_api_key)
  provides:
    - ocr_scale 既定 1.5（pagefolio/settings.py）
    - gemini_model 既定（pagefolio/settings.py）
    - Gemini/ヒント文言 ja/en（pagefolio/lang.py）
    - LLMConfigDialog に gemini プロバイダ欄・ocr_scale 常設ヒント（pagefolio/dialogs/llm_config.py）
    - OCRDialog のプロバイダ判定系全メソッドの gemini 対応（pagefolio/ocr_dialog.py）
    - APP_VERSION v1.4.0・開発履歴.md・README バッジ同期
  affects:
    - Plan 06-02（逐次レンダリング — 同波）
tech_stack:
  added: []
  patterns:
    - クラウドプロバイダ判定を name in ('claude','gemini') + isinstance で実装（Pitfall-F 対応）
    - dual env var フォールバック（GEMINI_API_KEY → GOOGLE_API_KEY）を _needs_session_key に適用（Pitfall-G）
    - gemini_section_frame を claude_section_frame と同パターンで実装し _on_provider_change で pack/pack_forget
    - ocr_scale 常設ヒント Label を scale_row 直後に C["TEXT_SUB"] テーマ色で配置（テーマ色ハードコード禁止）
    - セッションキーは _session_api_keys["gemini"] に格納（settings/os.environ への書き込みなし・T-06-11）
key_files:
  created: []
  modified:
    - pagefolio/settings.py
    - pagefolio/lang.py
    - pagefolio/dialogs/llm_config.py
    - pagefolio/ocr_dialog.py
    - pagefolio/constants.py
    - 開発履歴.md
    - README.md
    - tests/test_settings_keyguard.py
    - tests/test_provider_ui.py
decisions:
  - "[Phase 06-03]: ocr_scale 既定を 2.0 → 1.5 に変更（D-11・OCR-PERF-05）。既存保存値は setdefault のため据え置き"
  - "[Phase 06-03]: gemini_model 既定値 'gemini-2.5-flash' を settings.py に追加（D-08・無害な設定値）"
  - "[Phase 06-03]: _is_cloud_provider は name in ('claude','gemini') + isinstance((ClaudeProvider, GeminiProvider)) で判定（Pitfall-F）"
  - "[Phase 06-03]: _needs_session_key の gemini 分岐は GEMINI_API_KEY or GOOGLE_API_KEY の dual env var（D-06/Pitfall-G）"
  - "[Phase 06-03]: _confirm_cost の送信先ホストはプロバイダ別（gemini: generativelanguage.googleapis.com / claude: api.anthropic.com）"
  - "[Phase 06-03]: gemini セッションキーは _session_api_keys['gemini'] のみに格納（T-06-11・settings 非永続化）"
  - "[Phase 06-03]: gemini の _apply では gemini_model のみ収集（api_key 系収集ゼロ・T-06-10）"
metrics:
  duration: "約 12 分"
  completed: "2026-06-07"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 9
---

# Phase 06 Plan 03: Gemini UI 統合・ocr_scale 最適化 Summary

**One-liner:** ocr_scale 既定を 1.5 に変更・Gemini プロバイダを SettingsDialog と OCRDialog に統合し、プロバイダ判定系全メソッド（_is_cloud_provider/_needs_session_key/_provider_display_name/_apply_llm_settings/_confirm_cost）を dual env var 対応で gemini 対応化。

---

## Objective

OCR-PERF-05（ocr_scale 1.5 + ヒント）と OCR-API-02 の UI 統合部分・OCR-QA-01 補助文言を満たす。
Plan 01（GeminiProvider コア）を基盤として UI 層に gemini を接続。

---

## Tasks Completed

| Task | 説明 | Commit | ファイル |
|------|------|--------|---------|
| 1 | ocr_scale 既定 1.5 化・gemini_model 既定追加・Gemini/ヒント文言追加・テスト | c1306b8 | settings.py, lang.py, tests/test_settings_keyguard.py |
| 2 | llm_config.py に gemini プロバイダ欄と ocr_scale 常設ヒントを追加 | d5e066b | dialogs/llm_config.py, tests/test_provider_ui.py |
| 3 | ocr_dialog.py の gemini 分岐追加・v1.4.0 バージョン同期 | 6e54067 | ocr_dialog.py, constants.py, 開発履歴.md, README.md, tests/test_provider_ui.py |

---

## Implementation Details

### Task 1: settings.py・lang.py

- `settings.py` defaults: `"ocr_scale": 2.0` → `"ocr_scale": 1.5`（D-11）
- `settings.py` defaults: `"gemini_model": "gemini-2.5-flash"` を追加（D-08）
- `lang.py` ja/en 両辞書: `ocr_provider_name_gemini`・`ocr_api_key_missing_gemini`・`ocr_scale_tradeoff_hint` を `ocr_provider_name_claude` 近傍に追加
- `test_settings_keyguard.py`: `TestLoadSettingsDefaults` に `test_ocr_scale_default_is_1_5`・`test_gemini_model_default`・既存の `test_load_with_existing_file_preserves_defaults` への追加アサーションを追加

### Task 2: dialogs/llm_config.py

- import に `GeminiProvider` を追加
- `provider_combo.values`: `["off", "lmstudio", "claude", "gemini"]`
- `gemini_section_frame`: `claude_section_frame` と同パターン。`gemini_model_var`（既定 current_settings.get("gemini_model","gemini-2.5-flash")）・`gemini_model_combo`（values=GeminiProvider.RECOMMENDED_MODELS）・「モデル更新」ボタン（_refresh_gemini_models）
- `_refresh_gemini_models`: GEMINI_API_KEY / GOOGLE_API_KEY 読取・静的リストフォールバック（D-08）
- `_on_provider_change` gemini 分岐: gemini_section_frame pack・claude_section_frame pack_forget・effort_frame pack_forget・temperature_frame pack（D-09: temperature のみ）
- ocr_scale 常設ヒント Label: `C["TEXT_SUB"]`・`self._font(-2)`（テーマ色ハードコードなし）
- `_apply` に `gemini_model` 収集を追加（api_key 系収集ゼロを維持・T-06-10）

### Task 3: ocr_dialog.py + バージョン同期

- `_provider_display_name`: `name == "gemini" or isinstance(provider, GeminiProvider)` → `ocr_provider_name_gemini`
- `_is_cloud_provider`: `name in ("claude", "gemini")` + `isinstance(provider, (ClaudeProvider, GeminiProvider))`（Pitfall-F）
- `_estimate_cost`: Gemini モデル判定（"gemini" in model）→ gemini-2.5-flash $0.075/$0.30 / gemini-2.5-pro $1.25/$10 MTok の粗い見積もり（D-10）
- `_needs_session_key`: `name == "gemini"` のとき `not (GEMINI_API_KEY or GOOGLE_API_KEY)`（dual env var・D-06/Pitfall-G）
- `_confirm_cost`: gemini 時 host="generativelanguage.googleapis.com"・model=gemini_model（claude 時は従来通り）
- `_apply_llm_settings` provider 再生成: `elif name == "gemini":` 分岐を追加（_resolve_api_key("gemini") → build_provider）
- `_on_run` クラウドゲート: セッションキーエラー文言を gemini 用（ocr_api_key_missing_gemini）で出し分け・格納先を `_session_api_keys["gemini"]`（T-06-11）
- `_on_run` provider 再生成: `elif name == "gemini":` 分岐を追加
- `constants.py`: APP_VERSION = "v1.4.0"
- `開発履歴.md`: v1.4.0 正式リリースエントリ追加
- `README.md`: バッジ v1.4.0 に同期

---

## Test Results

| テストスイート | 結果 |
|--------------|------|
| `pytest tests/test_settings_keyguard.py -q` | 16 passed |
| `pytest tests/test_provider_ui.py -q` | 36 passed |
| `pytest -q`（全件・回帰含む） | 370 passed |
| `ruff check .` | クリーン |

---

## Deviations from Plan

なし — プランどおりに実行。

---

## Threat Model Coverage

| Threat ID | 対応状況 |
|-----------|---------|
| T-06-10 | `_apply` に api_key 系キーの収集なしを実装・grep 検証済み |
| T-06-11 | gemini セッションキーを `_session_api_keys["gemini"]` に格納・settings への書き込みなし |
| T-06-12 | gemini もコスト確認ダイアログ（generativelanguage.googleapis.com・ページ数・概算コスト）を毎回表示 |
| T-06-13 | _refresh_gemini_models は失敗時に静的 RECOMMENDED_MODELS へフォールバック（D-08） |

---

## Known Stubs

なし。

---

## Threat Flags

なし（計画された Gemini API 境界のみ。新規境界の追加なし）。

---

## Self-Check

**ファイル存在確認:**
- `pagefolio/settings.py` に `"ocr_scale": 1.5` が存在する: OK
- `pagefolio/settings.py` に `"gemini_model": "gemini-2.5-flash"` が存在する: OK
- `pagefolio/lang.py` に `ocr_provider_name_gemini` が ja/en 両方に存在する: OK
- `pagefolio/lang.py` に `ocr_scale_tradeoff_hint` が ja/en 両方に存在する: OK
- `pagefolio/dialogs/llm_config.py` に `"gemini"` が provider_combo values に存在する: OK
- `pagefolio/dialogs/llm_config.py` に `gemini_section_frame` が存在する: OK
- `pagefolio/ocr_dialog.py` に `_is_cloud_provider` の gemini 分岐が存在する: OK
- `pagefolio/ocr_dialog.py` に `_needs_session_key` の gemini dual env var 分岐が存在する: OK
- `pagefolio/ocr_dialog.py` に `generativelanguage.googleapis.com` が存在する: OK
- `pagefolio/constants.py` に `APP_VERSION = "v1.4.0"` が存在する: OK

**コミット存在確認:**
- c1306b8: feat(06-03) Task 1 — 存在確認 OK
- d5e066b: feat(06-03) Task 2 — 存在確認 OK
- 6e54067: feat(06-03) Task 3 — 存在確認 OK

## Self-Check: PASSED
