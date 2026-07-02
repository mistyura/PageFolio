---
quick_id: 260702-oms
slug: ocr-multipage-summary-5y1qe4
date: 2026-07-02
type: quick
mode: quick
---

# Plan: 複数ページ OCR の全ページ統合サマリ生成機能（v1.6.4）

## 背景

複数ページの OCR テキスト変換では各ページ毎の表のみが生成され、最終頁までの
**マージ・サマリ表**（例: レシート束の「日付・相手先・税率・税率毎の合計金額（税込）・
総合計金額（税込）・インボイス有無・想定勘定科目」一覧）は作成されなかった。

OCR 完了後に全ページの OCR 結果テキストを LLM へ再送信し、統合サマリを生成する
機能を追加する。ユーザー確認済みの決定事項:

- **トリガー**: 手動ボタン「📊 サマリ作成」（クラウド API コストをユーザーが制御。
  自動生成はしない）
- **プロンプト設定場所**: LLM 設定ダイアログの新設欄（`ocr_summary_prompt` として
  settings に永続化。空欄なら既定のドメイン非依存サマリ指示。レシート集計のような
  業務固有の列指定はこの欄で与える）

## タスク

### Task 1: プロバイダ層 — text-only 補完 API
- **files**: `pagefolio/ocr_providers.py`
- **action**: `OCRProvider` 基底に `complete_text_ex(text, prompt)`（既定
  `NotImplementedError`・`(text, truncated)` 契約は `ocr_image_ex` と同一）と
  capability フラグ `supports_text_prompt`（既定 False）を追加。
  LM Studio / Ollama / RunPod（OpenAI 互換・`finish_reason=="length"` で途切れ検出）、
  Claude（`stop_reason=="max_tokens"`）、Gemini（`finishReason=="MAX_TOKENS"`）に
  `_build_text_payload`（画像ブロックなし・「文書テキスト→指示」順）+
  `complete_text_ex` を実装。Tesseract は非 LLM のため非対応のまま。
  HTTP 送信部を `_post_chat` / `_post_payload` に抽出して画像あり/テキストのみで共有
  （**`_build_payload` のシグネチャはテスト互換のため不変**）。Claude の
  effort/temperature 分岐は `_apply_gen_params`、Gemini の generationConfig は
  `_build_generation_config` に共通化。
- **verify**: 既存 `_build_payload` テストが無変更で通ること・新規テストグリーン
- **done**: 5 プロバイダで text-only 補完が可能、Tesseract は構造的に除外

### Task 2: プロンプト解決・設定・文言
- **files**: `pagefolio/ocr.py`, `pagefolio/dialogs/llm_config.py`, `pagefolio/lang.py`
- **action**: `ocr.py` に `DEFAULT_SUMMARY_PROMPT`（ドメイン非依存・
  `--- Page N ---` 区切り前提・マージ一覧表 + 合計行指示）、
  `PROVIDER_SUMMARY_PROMPTS`（claude=XML / gemini=命令調）、
  `resolve_summary_prompt(provider_name, custom_prompt)`（custom > プロバイダ別 >
  既定・`resolve_ocr_prompt` と同型の純関数）を追加。
  `llm_config.py` にカスタムプロンプト欄と同型の「サマリプロンプト」`tk.Text` を
  新設し `_apply` で `ocr_summary_prompt` に収集（`ocr_custom_prompt` と同じく
  settings デフォルト定義は追加せず `.get(..., "")` 参照で運用）。
  `lang.py` に `ocr_summary_*` キー 12 個を ja/en 両方へ追加（parity テスト維持）。
- **verify**: `test_lang_parity.py`・`TestResolveSummaryPrompt` グリーン
- **done**: プロンプトが custom > プロバイダ別 > 既定で解決され設定から編集できる

### Task 3: OCR ダイアログ — サマリ実行系
- **files**: `pagefolio/ocr_dialog.py`
- **action**: ボタン行に「📊 サマリ作成」を追加し `_update_summary_btn_state`
  （results あり・非実行中・`supports_text_prompt` で有効化）を `_after_run_ui_reset`
  / `_apply_llm_settings` から呼ぶ。`_on_summary`（ガード → クラウド時は
  `_ensure_cloud_session_key`（`_on_run` から抽出・共有）+ `_confirm_summary_cost`
  （概算文字数表示・毎回確認）→ `_format_pages_text` で入力確定 →
  `_run_gen` インクリメント → ワーカースレッド 1 本起動）。
  `_summary_worker` は `complete_text_ex` を MAX_RETRIES 回まで指数バックオフ
  （`clamp_retry_after` 60 秒上限・`interruptible_sleep`）でリトライし、世代ガード後に
  after(0) で `_on_summary_done` / `_on_summary_error` / `_on_summary_cancelled` を投函。
  **キャンセルはサマリ専用 `_summary_cancel_flag`**（OCR 用 `_cancel_flag` を clear
  すると旧ワーカー残留時に queue ループから抜けられなくなるため分離）。
  結果は Text 末尾へ `--- Summary ---` 付きで追記（`preset=="markdown"` のみ整形描画）、
  `_format_full_text` は `_format_pages_text` + サマリ raw 連結に分離
  （サマリ再生成時に旧サマリが LLM 入力へ混入しない構造）。途切れは部分サマリ保持 +
  警告併記（D-05 同方針）。`_clear_text` / `_on_run` / `_on_cancel` / `_on_close` /
  `_open_llm_config` にサマリ状態の破棄・ガードを追加。
- **verify**: `_summary_worker` の正常 / 世代不一致 / リトライ上限 / キャンセル経路テスト
- **done**: OCR 完了 → サマリ作成 → 表示・コピー/保存に含まれる一連の導線が動作

### Task 4: テスト・ドキュメント
- **files**: `tests/test_ocr_providers.py`, `tests/test_provider_ui.py`,
  `tests/test_ocr.py`, `pagefolio/constants.py`, `開発履歴.md`, `README.md`, `CLAUDE.md`
- **action**: 新規テスト 41 件（text-only payload に画像ブロックが無いこと・途切れ検出・
  429 リトライ・RunPod キー未設定・プロンプト解決純関数・`_format_full_text` サマリ連結・
  `_update_summary_btn_state`・`_summary_worker` 各経路・`_on_summary_done` 描画）。
  既存 fake（`types.SimpleNamespace`）へ新属性を追加。`APP_VERSION` を v1.6.4 へ更新し
  README バッジ・開発履歴.md・CLAUDE.md の OCR モジュール表を同期。
- **verify**: `ruff check . && ruff format .`・`pytest`（667 件）グリーン
- **done**: v1.6.4 としてドキュメント・バージョンが揃う

## must_haves

- truths: OCR 完了後に全ページ統合サマリを生成できる／Tesseract 等非対応プロバイダは
  三重ガード（ボタン無効 + 実行時チェック + NotImplementedError 捕捉）で除外／
  サマリ失敗・キャンセルで OCR 結果を破壊しない／コピー・保存にサマリが raw で含まれる／
  ruff・pytest 667 件グリーン
- artifacts: `complete_text_ex` / `supports_text_prompt`（5 プロバイダ実装）・
  `resolve_summary_prompt`・「📊 サマリ作成」ボタン一式・LLM 設定のサマリプロンプト欄・
  `ocr_summary_*` LANG キー（ja/en）・テスト 41 件・本 quick 文書
- key_links: pagefolio/ocr_providers.py, pagefolio/ocr.py, pagefolio/ocr_dialog.py,
  pagefolio/dialogs/llm_config.py, pagefolio/lang.py
