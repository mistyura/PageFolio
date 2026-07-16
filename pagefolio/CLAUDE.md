# pagefolio/ モジュール構成

ルートの [CLAUDE.md](../CLAUDE.md) の補足。`pagefolio/` パッケージ配下で作業する際に参照する。

### `pagefolio/constants.py`

バージョン（`APP_VERSION`）・ファイル名・対応拡張子の定数を定義。
`themes.py` の `THEMES` / `C`、`lang.py` の `LANG` を再エクスポートし後方互換 import 表面を維持。
OCR プロンプトの外部ファイル名 `CUSTOM_PROMPT_FILE`（`ocr_custom_prompt.md`）/ `SUMMARY_PROMPT_FILE`（`ocr_summary_prompt.md`）も定義する。

### `pagefolio/themes.py` / `pagefolio/lang.py`

`themes.py` はカラーテーマ（`THEMES`）と実行時テーマ辞書（`C`）、`lang.py` は言語辞書（`LANG`、ja / en）を定義。
LANG の新規キーは **ja / en 両方に同一キーで追加**しキー数の左右一致を維持すること。

### `pagefolio/settings.py`

設定ファイルの読み書き・テーマ解決・フォント生成のユーティリティ関数群。
API キーは `_SENSITIVE_KEYS` ガードにより `pagefolio_settings.json` へ保存されない。
OCR のカスタム/サマリプロンプトの外部 md ファイル読込・書き戻し（`load_prompt_file` / `save_prompt_file` / `prompt_file_exists` / `load_custom_prompt` / `load_summary_prompt`）と配置基準ディレクトリの一元化（`_get_base_dir`・frozen 時は exe ディレクトリ / 開発時はプロジェクトルート）も提供する。

### `pagefolio/plugins.py`

`PDFEditorPlugin` 基底クラスと `PluginManager` クラス。プラグインの検出・読込・有効/無効管理。
`register_ocr_provider` フックによる OCR プロバイダ登録に対応。

### `pagefolio/app.py`

`PDFEditorApp` メインクラス。8つの Mixin を統合し、`__init__`・キーバインド・ユーティリティメソッドを持つ。

### Mixin モジュール群

| モジュール | Mixin クラス | 責務 |
|-----------|-------------|------|
| `ui_builder.py` | `UIBuilderMixin` | スタイル定義・レイアウト構築 |
| `file_ops.py` | `FileOpsMixin` | ファイル操作・Undo/Redo・パスワード付与/解除 |
| `page_ops.py` | `PageOpsMixin` | ページ回転・削除・トリミング・挿入・結合・分割 |
| `redact_ops.py` | `RedactOpsMixin` | ページ編集（黒塗り redaction・モザイク）。矩形選択はトリミングと共用・undo は `page_edit` op（適用前ページ bytes） |
| `viewer.py` | `ViewerMixin` | プレビュー・ズーム・サムネイル・ポップアップ |
| `dnd.py` | `DnDMixin` | サムネイル D&D 並び替え |
| `ocr.py` | `OCRMixin` | OCR 起動・プロバイダ生成（`build_provider`）・ボタン状態管理 |
| `print_ops.py` | `PrintOpsMixin` | 印刷（既定 PDF ハンドラへ送信・`write_print_tempfile`） |

### OCR モジュール群

| モジュール | 主要クラス / 関数 | 責務 |
|-----------|------------------|------|
| `ocr.py` | `OCRMixin`, `build_provider`, `run_parallel`, `clamp_retry_after`, `interruptible_sleep`, `PROVIDER_OCR_PROMPTS`, `resolve_ocr_prompt`, `PROVIDER_SUMMARY_PROMPTS`, `resolve_summary_prompt` | プロバイダ生成・並列 OCR 実行・リトライ/キャンセル制御・プロバイダ別プロンプト解決（custom>provider別>汎用）・サマリプロンプト解決 |
| `ocr_pipeline.py` | `PipelineState`, `consume_one`, `try_enqueue`, `send_sentinels` | 複数ページ画像 OCR 実行パイプラインの producer-consumer 純ロジック層（Tk/fitz 非依存）。共有カウンタ/fatal 判定/サーキットブレーカーは `PipelineState`、1 アイテム消費（リトライ/バックオフ/fatal 判定）は `consume_one`、非ブロッキング enqueue/sentinel 送出は `try_enqueue`/`send_sentinels` に集約（D-01/D-02・L-1 一本化） |
| `ocr_providers.py` | `OCRProvider`(ABC), `LMStudioProvider`, `ClaudeProvider`, `GeminiProvider`, `TesseractProvider`, `OllamaProvider`, `RunPodProvider` | 各バックエンドへの OCR リクエスト実装（`ocr_image_ex` で stop_reason/finishReason 途切れ検出・`complete_text_ex`/`supports_text_prompt` で text-only 補完＝全ページ統合サマリ生成。Tesseract は非対応）。`list_models` のモデル一覧取得タイムアウトはクラス属性 `model_list_timeout`（基底 10 / Claude・Gemini 30 / RunPod 90 秒＝Serverless コールドスタート対応） |
| `md_render.py` | `parse_markdown`, `_split_inline` | OCR 結果 Markdown を (行種別, インライン span) へ変換する純関数（Tk/fitz 非依存・`ocr_dialog.py` の整形描画が消費） |
| `ocr_dialog.py` | `OCRDialog` | 複数ページ OCR の実行 UI・進捗・結果表示/エクスポート（`_run_gen` 世代ガード）・`preset=="markdown"` 整形描画（`_insert_markdown`）・コピー/保存は raw 維持・「📊 サマリ作成」による全ページ統合サマリ生成（`_on_summary`/`_summary_worker`・サマリ専用キャンセルフラグ）。`_render_next_page`/`_worker` は `ocr_pipeline` の関数/`PipelineState` を呼ぶ薄いラッパー（D-01・fitz/Tk 依存部分のみ保持）。OCR プリセット横の注記（`_update_preset_note`: カスタムプロンプト使用中はプリセットが表示形式にのみ適用される旨）・右ペイン（「▶ 実行」「📋 結果」セクション）は Canvas+Scrollbar の縦スクロール対応で「✕ 閉じる」はスクロール領域外に常時可視 |

### ページネーション

`pagination.py` はサムネイル一覧の窓表示（既定 20・範囲 10〜100）の純ロジック層。窓計算・件数クランプ・ローカル位置 ↔ 全ページインデックス変換（`to_global` 等）を Tk/fitz 非依存の純関数群として集約する。`selected_pages` は全ページインデックスのまま保持し、描画・D&D・選択照合の側で窓変換する（散在による窓またぎバグを構造的に防止）。

### `pagefolio/dialogs/`（パッケージ）

`about.py`（`AboutDialog`）・`settings.py`（`SettingsDialog`）・`plugin.py`（`PluginDialog`）・
`merge.py`（`MergeOrderDialog` / `MergeResizeDialog`）・`llm_config/`（サブパッケージ。`LLMConfigDialog` は `__init__.py` で Mixin 合成。クラウドモデル取得の非同期化 `_fetch_models_async` は `model_fetch.py`、外部プロンプトファイル連動注記 `_add_prompt_file_notice` は `dialog.py`、セクション構築は `sections.py` が担う）に分割。
`__init__.py` が re-export するため `from pagefolio.dialogs import SettingsDialog` 等の既存 import は維持される。
