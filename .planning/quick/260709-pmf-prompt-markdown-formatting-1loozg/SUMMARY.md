---
quick_id: 260709-pmf
slug: prompt-markdown-formatting-1loozg
date: 2026-07-09
status: complete
---

# Summary: プロンプト外部 md ファイル読込・Markdown 描画個別指定・モデル取得タイムアウト見直し（v1.7.4）

ブランチ: `claude/prompt-markdown-formatting-1loozg`
コミット: `5e013a4`（Markdown 描画個別指定 + タイムアウト見直し）→
`515e434`（外部 md ファイル読込方式）— いずれも push 済み
品質確認: `ruff check` / `ruff format` クリーン / `pytest` **883 件パス**
（実行環境に tkinter 3.11 が無く、`python3.12` で pytest を実行）

[PLAN.md](./PLAN.md) の方針どおりに実装した。要望 3（外部 md ファイル方式）は
要望 1・2 の実装後に追加で受領したため 2 コミットに分かれているが、いずれも
未リリースの v1.7.4 に統合した。プランからの逸脱はなし。

## 実施内容

### コミット `5e013a4`: Markdown 描画個別指定 + モデル取得タイムアウト見直し

- **`resolve_render_markdown` 新設**（`ocr.py`・純関数）: カスタムプロンプト非空なら
  個別フラグ、空なら従来どおり `preset == "markdown"` を返す。
  `_render_results_ordered`（OCR 本文）と `_on_summary_done`（サマリ）の判定を集約。
  サマリはサマリプロンプト（`ocr_summary_prompt`）+ `ocr_summary_markdown` で判定し、
  OCR プリセットとの不整合を解消。コピー/保存の raw 維持は不変。
- **LLM 設定にチェックボックス 2 個新設**: 「OCR結果をMarkdown整形で表示
  （カスタムプロンプト使用時）」「サマリをMarkdown整形で表示（サマリプロンプト使用時）」。
  設定キー `ocr_custom_prompt_markdown` / `ocr_summary_markdown`（既定 False・
  `settings.py` の defaults にも追加）。`_apply` は getattr フォールバック付きで格納。
- **`model_list_timeout` クラス属性新設**（`ocr_providers.py`）: 基底 10 秒 /
  Claude・Gemini 30 秒 / RunPod 90 秒（Serverless コールドスタート対応）。
  全プロバイダの `list_models`（Claude は `_fetch_models_page`）のハードコード
  `timeout = 10` を `self.model_list_timeout` へ置換。
- **クラウドモデル取得の非同期化**（`llm_config.py`）: 共有ヘルパー
  `_fetch_models_async`（ワーカースレッド + `after(0)` 投函・`_model_fetch_running`
  二重実行ガード・`winfo_exists` による破棄後破棄）を新設し、
  `_refresh_runpod_models` / `_refresh_claude_models` / `_refresh_gemini_models` を
  成功/失敗コールバック方式へ書き換え。D-08 の静的推奨リストフォールバックは維持。
  ローカル（LM Studio / Ollama）の同期プローブは従来どおり（10 秒・即応）。
- **i18n**: `ocr_custom_prompt_label/hint/md`・`ocr_summary_prompt_md` を ja/en へ追加
  （custom prompt label/hint は従来 `.get` フォールバックのみだったので正規キー化）。
  `llm_fetching_runpod_models` にコールドスタート注記を追記。

### コミット `515e434`: プロンプトの外部 md ファイル読込方式

- **読込層新設**（`settings.py`）: `load_prompt_file(filename)`（`utf-8-sig`・
  strip・不在/空/失敗は "" + `logger.warning`）と
  `load_custom_prompt(settings)` / `load_summary_prompt(settings)`
  （ファイル > 設定欄のフォールバック合成）。ファイル名は `constants.py` の
  `CUSTOM_PROMPT_FILE`（`ocr_custom_prompt.md`）/ `SUMMARY_PROMPT_FILE`
  （`ocr_summary_prompt.md`）。
- **配置基準の一元化**: `_get_settings_path` から `_get_base_dir()` を抽出
  （frozen 時は exe ディレクトリ / 開発時はプロジェクトルート）。
- **毎回再読込**: `OCRDialog._on_run`（ファイルがあれば `self.custom_prompt` を上書き）・
  `_on_summary`（`load_summary_prompt` 経由）・`_apply_llm_settings` の同期・
  `OCRMixin._start_ocr` の初期解決を更新。外部エディタでの編集が再起動なしで
  次回実行に反映される。
- **ファイル検出注記**（`llm_config.py`）: `_add_prompt_file_notice` を新設し、
  ファイル検出時のみ各プロンプト欄直下に「📄 {file} を検出 — 入力欄よりファイル内容を
  優先します」を WARNING 色で表示（`ocr_prompt_file_in_use` キー・ja/en）。
- **Markdown フラグとの連動**: `_on_summary_done` の描画判定・`_render_results_ordered`
  とも、外部ファイル使用時は「カスタム使用中」として個別フラグが適用される。
- `APP_VERSION` を `v1.7.3` → `v1.7.4` へ更新。README バッジ・開発履歴.md に追記。

## 検証内容

- 回帰テスト 24 件を追加し `pytest` 883 件グリーン:
  - `TestResolveRenderMarkdown`（5 件・test_provider_ui.py）: プリセット準拠の後方互換 /
    カスタム使用時のフラグ優先 / 既定 False。
  - `TestApplyPromptMarkdownFlags`（2 件・test_provider_ui.py）: `_apply` の新フラグ格納・
    変数未生成スタブ経路の False フォールバック。
  - `TestOnSummaryDone` 追加 2 件（test_ocr.py）: サマリプロンプト + フラグ ON で
    preset=text でも整形描画 / フラグ OFF で preset=markdown でも素朴描画。
  - `TestModelListTimeout`（6 件・test_ocr_providers.py）: プロバイダ別値
    （10/30/90 秒）と RunPod/Gemini の urlopen への timeout 伝播。
  - `TestPromptFileLoading`（9 件・test_utils.py）: 優先順位・フォールバック・BOM・
    空ファイル・定数一致（`_get_base_dir` を tmp_path へ monkeypatch）。
- 既存テストへの影響: `_make_apply_key_stub` へ新変数 2 個追加・
  `TestOnSummaryDone._make_fake` へ `app.settings` 追加のみ。md ファイル不在時は
  全経路が従来挙動へフォールバックするため他のテストは無変更で通過。
- `ruff check` / `ruff format` / `ast.parse`（pagefolio.py）クリーン。

## 注意点・潜在リスク

- **GUI 実機確認は未実施**（headless 環境のため）。Windows 実機（PyInstaller onedir
  ビルド）で、exe と同じフォルダに md を置いた場合の読込・LLM 設定ダイアログの
  チェックボックス/注記表示・テーマ（dark/light）での見え方は次回確認が必要。
- RunPod のコールドスタートが 90 秒を超える環境では引き続きタイムアウトし得る
  （再クリックで再試行。`model_list_timeout` の設定 UI 化が将来の改善候補）。
- ファイル検出注記はダイアログを開いた時点の状態を表示（開いたまま md を置いても
  注記は更新されない。実行時の読込自体は常に最新）。
- md ファイルが存在する間、設定欄の編集は実行に反映されない（注記で明示済み）。
  ファイルを削除/リネームすれば設定欄へ戻る。
- モデル取得の非同期化は LLM 設定ダイアログのみ。OCR ダイアログ側の接続テスト
  （LM Studio / Ollama・ローカル 10 秒）は従来どおり同期実行。
- main へのマージ・タグ・GitHub Release・PyInstaller リビルドは未実施（次セッション）。

## 実行推奨コマンド

```
ruff check . && ruff format .
pytest
```
