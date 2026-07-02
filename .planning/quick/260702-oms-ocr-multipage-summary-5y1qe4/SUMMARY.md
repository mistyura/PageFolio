---
quick_id: 260702-oms
slug: ocr-multipage-summary-5y1qe4
date: 2026-07-02
status: complete
---

# Summary: 複数ページ OCR の全ページ統合サマリ生成機能（v1.7.0）

ブランチ: `claude/ocr-multipage-summary-5y1qe4`（コミット `11001a6`）
品質確認: `ruff check` / `ruff format` クリーン / `pytest` 667 件パス
（※実行環境に tkinter 3.11 が無く、`python3.12` で pytest を実行）

複数ページ OCR で各ページ毎の表しか作成されなかった問題に対し、全ページの OCR
結果を LLM へ再送信して統合サマリ（マージ表）を生成する機能を v1.7.0 として実装した。

## 実施内容

### 1. プロバイダ層 — text-only 補完 API（`ocr_providers.py`）

- `OCRProvider` 基底に `complete_text_ex(text, prompt)`（`(text, truncated)` 契約・
  既定 `NotImplementedError`）と capability フラグ `supports_text_prompt`（既定 False）を追加。
- LM Studio / Ollama / RunPod（OpenAI 互換・`finish_reason=="length"` で途切れ検出）、
  Claude（`stop_reason=="max_tokens"`）、Gemini（`finishReason=="MAX_TOKENS"`）に
  `_build_text_payload`（画像ブロックなし・「文書テキスト→指示」順）+ `complete_text_ex` を実装。
  Tesseract は非 LLM のため非対応のまま（`supports_text_prompt=False`）。
- HTTP 送信部を `_post_chat` / `_post_payload` に抽出し画像あり/テキストのみで共有
  （**`_build_payload` のシグネチャは既存テスト互換のため不変**）。Claude の
  effort/temperature 分岐は `_apply_gen_params`、Gemini の generationConfig は
  `_build_generation_config` に共通化（挙動不変リファクタ）。

### 2. サマリプロンプト解決・設定（`ocr.py` / `llm_config.py` / `lang.py`）

- `DEFAULT_SUMMARY_PROMPT`（ドメイン非依存・`--- Page N ---` 区切り前提・マージ一覧表
  + 合計行指示）・`PROVIDER_SUMMARY_PROMPTS`（claude=XML / gemini=命令調）・
  `resolve_summary_prompt`（custom > プロバイダ別 > 既定・純関数）を追加。
- LLM 設定ダイアログに「サマリプロンプト」欄を新設し `ocr_summary_prompt` として永続化。
  レシート集計（日付・相手先・税率・税率毎合計・総合計・インボイス有無・勘定科目）の
  ような業務固有の列指定はこの欄で与える。
- `ocr_summary_*` LANG キー 12 個を ja/en 両方へ追加（parity テスト維持）。

### 3. OCR ダイアログ — サマリ実行系（`ocr_dialog.py`）

- 「📊 サマリ作成」ボタンを新設。OCR 完了後（results あり・非実行中・
  `supports_text_prompt`）のみ有効化する手動トリガー方式（クラウドコスト配慮）。
- `_on_summary`: ガード → クラウド時は `_ensure_cloud_session_key`（`_on_run` から
  抽出・共有）+ `_confirm_summary_cost`（送信テキスト概算文字数を毎回確認）→
  `_format_pages_text` で入力確定 → `_run_gen` 世代を進めてワーカースレッド 1 本起動。
- `_summary_worker`: `complete_text_ex` を MAX_RETRIES 回まで指数バックオフ
  （`clamp_retry_after` 60 秒上限・`interruptible_sleep`）でリトライし、世代ガード後に
  after(0) で `_on_summary_done` / `_on_summary_error` / `_on_summary_cancelled` を投函。
- **サマリ専用キャンセルフラグ `_summary_cancel_flag`** を新設（OCR 用 `_cancel_flag` を
  clear すると旧ワーカー残留時に queue ループから抜けられなくなるため共有しない）。
- 結果は Text 末尾へ `--- Summary ---` 付きで追記（`preset=="markdown"` のみ整形描画）。
  `_format_full_text` を `_format_pages_text` + サマリ raw 連結に分離し、コピー/保存に
  サマリを含めつつ、サマリ再生成時に旧サマリが LLM 入力へ混入しない構造にした。
- 途切れ（max_tokens）は部分サマリ保持 + 警告併記（D-05 同方針）。サマリ失敗は OCR
  結果を破壊せず再実行可能。`_clear_text` / `_on_run` / `_on_cancel` / `_on_close` /
  `_open_llm_config` にサマリ状態の破棄・ガードを追加。
- 非対応プロバイダは三重ガード（ボタン無効 + `_on_summary` 内チェック +
  `NotImplementedError` 捕捉）。

## 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `pagefolio/ocr_providers.py` | `complete_text_ex` / `supports_text_prompt` / `_build_text_payload`・POST 共有化 |
| `pagefolio/ocr.py` | `DEFAULT_SUMMARY_PROMPT` / `PROVIDER_SUMMARY_PROMPTS` / `resolve_summary_prompt` |
| `pagefolio/ocr_dialog.py` | サマリボタン・`_on_summary` / `_summary_worker` / 完了ハンドラ・`_ensure_cloud_session_key` 抽出・`_format_pages_text` 分離 |
| `pagefolio/dialogs/llm_config.py` | 「サマリプロンプト」欄・`ocr_summary_prompt` 収集 |
| `pagefolio/lang.py` | `ocr_summary_*` キー（ja/en） |
| `pagefolio/constants.py` | `APP_VERSION` v1.7.0 |
| `tests/test_ocr_providers.py` / `tests/test_provider_ui.py` / `tests/test_ocr.py` | 新規テスト 41 件・既存 fake へ新属性追加 |
| CLAUDE.md / 開発履歴.md / README.md | ドキュメント・バッジ更新 |

## テスト

- 新規 41 件: text-only payload に画像ブロックが無いこと・途切れ検出・429 リトライ・
  RunPod キー未設定・`resolve_summary_prompt` 純関数・`_format_full_text` サマリ連結・
  `_update_summary_btn_state`・`_summary_worker`（正常/世代不一致/リトライ上限/
  キャンセル）・`_on_summary_done` 描画。
- 合計 667 件パス（v1.6.3 時点 626 → +41）。

## 注意点・潜在リスク

- **実 LLM プロバイダでの実機確認は未実施**（headless 環境のため GUI 起動不可。
  ワーカー・プロンプト解決・payload 生成はユニットテストで検証済み）。
- サマリのコスト確認は概算文字数のみ表示（画像 OCR のような $ 概算は未実装。
  トークン単価換算の追加が将来候補）。
- ページ数が非常に多い場合、連結テキストがモデルのコンテキスト長を超える可能性
  （分割サマリは将来候補）。
- 送信中の 1 リクエストは urlopen の制約上即時中断不可（既存 OCR と同じ制約）。
- RunPod 選択時のコスト確認の送信先ホスト表示は claude 側へフォールバック
  （既存 `_confirm_cost` と同挙動）。

## 実行推奨コマンド

```
ruff check . && pytest
```
