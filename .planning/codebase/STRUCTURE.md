# Codebase Structure

**Analysis Date:** 2026-06-01

## Directory Layout

```
PageFolio/
├── pagefolio.py               # スクリプトエントリーポイント（python pagefolio.py）
├── pagefolio/                 # メインパッケージ
│   ├── __init__.py            # 後方互換の公開API（全クラス・関数をre-export）
│   ├── __main__.py            # モジュールエントリーポイント（python -m pagefolio）
│   ├── app.py                 # PDFEditorApp 本体（Mixin統合・状態管理・キーバインド）
│   ├── constants.py           # THEMES, C, APP_VERSION, LANG, SUPPORTED_EXTENSIONS
│   ├── settings.py            # 設定ファイルI/O・テーマ適用・フォントヘルパー
│   ├── plugins.py             # PDFEditorPlugin基底クラス・PluginManager
│   ├── ui_builder.py          # UIBuilderMixin（スタイル・レイアウト構築）
│   ├── file_ops.py            # FileOpsMixin（open/save/undo/redo）
│   ├── page_ops.py            # PageOpsMixin（回転/削除/トリミング/挿入/結合/分割）
│   ├── viewer.py              # ViewerMixin（プレビュー/ズーム/サムネイル/ポップアップ）
│   ├── dnd.py                 # DnDMixin（サムネイルD&D並び替え）
│   ├── ocr.py                 # OCRMixin + LM Studio APIクライアント関数
│   ├── ocr_dialog.py          # OCRDialog（OCR結果表示・エクスポート）
│   ├── dialogs.py             # About/Settings/Plugin/MergeOrder/MergeResizeDialog
│   └── file_drop.py           # tkinterdnd2 ファイルD&D連携
├── plugins/                   # プラグインディレクトリ（起動時に自動スキャン）
│   └── page_info.py           # サンプルプラグイン
├── tests/                     # pytestテストスイート
│   ├── conftest.py            # 共通フィクスチャ
│   ├── test_utils.py          # ユーティリティ関数テスト
│   ├── test_pdf_ops.py        # PDF操作テスト
│   └── test_plugins.py        # PluginManagerテスト
├── docs/                      # スクリーンショット画像
├── pagefolio.ico              # アプリアイコン
├── CLAUDE.md                  # AI向け開発指示書
├── README.md                  # エンドユーザー向けドキュメント
├── 開発履歴.md                # 機能追加・変更履歴
├── LICENSE                    # MITライセンス
└── pyproject.toml             # Ruff・pytest設定

（実行時に自動生成）
└── pagefolio_settings.json    # ユーザー設定JSON
```

## Package Structure

### `pagefolio/__init__.py` (42 lines)
後方互換の公開API。パッケージ内の全クラス・関数をre-exportする。`from pagefolio import PDFEditorApp` が可能。

### `pagefolio/__main__.py` (30 lines)
`python -m pagefolio` のエントリーポイント。`tk.Tk()` を生成し `PDFEditorApp` を初期化してメインループを起動。

### `pagefolio/app.py` (376 lines)
**PDFEditorApp** — アプリケーションのルートクラス。6つのMixinを多重継承で統合。

責務:
- `__init__`: 全状態の初期化・設定読み込み・テーマ適用・PluginManager初期化・UI構築・キーバインド設定
- `_update_doc_buttons_state()`: ファイル開閉に応じたボタン活性/非活性
- `_check_doc()`: 操作前のdoc存在確認
- `_get_targets()`: 選択ページまたは現在ページを返す
- D&Dファイルオープンハンドラ (`_on_dnd_enter`, `_on_dnd_leave`, `_on_drop`)
- `_toggle_edit_mode()`, `_font()`, `_t()`, `_set_status()`, `_refresh_all()`, `_quit()`

### `pagefolio/constants.py` (711 lines)
- `THEMES`: `dict` — "dark" / "light" テーマカラー定義
- `C`: `dict` — 実行時テーマ辞書（`_apply_theme()` で更新）
- `APP_VERSION`: `str` — バージョン文字列（例: `"v1.2.2"`）
- `LANG`: `dict` — UI文言の日本語/英語辞書
- `SUPPORTED_EXTENSIONS`: ファイルダイアログ用拡張子定義
- `PLUGINS_DIR`: プラグインディレクトリ名定数

### `pagefolio/settings.py` (107 lines)
純粋関数群（状態なし）:
- `_get_settings_path()`: `pagefolio_settings.json` のフルパスを返す
- `_load_settings()`: JSON読み込み（ファイルなければデフォルト値）
- `_save_settings(settings)`: JSON書き込み
- `_apply_theme(theme_name)`: `C` 辞書をin-place更新
- `_resolve_theme(settings)`: "system" テーマを実テーマ名に解決
- `_detect_system_theme()`: OS設定から "dark"/"light" を判定
- `_make_font(size, style)`: `(font_family, size, style)` タプルを返す

### `pagefolio/plugins.py` (200 lines)
- `PDFEditorPlugin`: プラグイン基底クラス。クラス変数 `name`, `version`, `description`, `author` と11のライフサイクルフックメソッドを定義
- `PluginManager`: プラグインの検出・動的読み込み（`importlib.util`）・有効/無効管理・イベント発火

### `pagefolio/ui_builder.py` (559 lines)
**UIBuilderMixin** — スタイルとレイアウト構築:
- `_build_styles()`: ttk スタイル定義（TButton, Accent.TButton, Danger.TButton, CropOn.TButton 等）
- `_build_ui()`: メインレイアウト（ヘッダー・PanedWindow・左サムネイルパネル・プレビューキャンバス・右ツールパネル）
- `_build_tools_scrollable()`: 右ペインのスクロール可能Canvas構成
- `_update_mode_button()`: モード切替ボタンの表示更新

### `pagefolio/file_ops.py` (340 lines)
**FileOpsMixin** — ファイル操作とUndo/Redo:
- `_open_file(path=None)`: ファイルダイアログまたはパス指定でPDF開く
- `_save_file()`, `_save_as()`: 上書き/名前を付けて保存
- `_undo()`, `_redo()`: バイトスナップショット復元
- `_push_undo()`: スタックに現在のdocをpush（MAX_UNDO=20で古いものを廃棄）
- `_close_file()`: docクローズと状態リセット

### `pagefolio/page_ops.py` (604 lines)
**PageOpsMixin** — ページ操作:
- `_rotate_page(degrees)`: 選択ページを回転
- `_delete_selected()`: 選択ページを削除
- `_start_crop_mode()`, `_apply_crop()`: トリミングモード管理とCropBox適用
- `_insert_pages(paths, insert_at)`: 他PDFからページ挿入
- `_merge_pdfs(paths)`: 複数PDFを結合
- `_split_pdf()`: PDFを個別ページに分割

### `pagefolio/viewer.py` (446 lines)
**ViewerMixin** — 表示と描画:
- `_show_page(idx)`: プレビューキャンバスにページをレンダリング（背景スレッド）
- `_rebuild_thumbs()`: 全サムネイルを再生成（背景スレッド、キャッシュ利用）
- `_refresh_all()`: サムネイルとプレビューを両方更新
- `_zoom_in()`, `_zoom_out()`: ズーム操作
- `_show_popup_preview(page_idx)`: サムネイルホバー時ポップアップ

### `pagefolio/dnd.py` (135 lines)
**DnDMixin** — サムネイルD&D並び替え:
- `_on_thumb_drag_start()`, `_on_thumb_drag_motion()`, `_on_thumb_drag_end()`: ドラッグ開始・移動・終了
- 複数選択ページをまとめて移動対応
- ゴーストウィジェットとドロップ位置インジケーター

### `pagefolio/ocr.py` (320 lines)
**OCRMixin** + スタンドアロン関数群:
- `page_to_png_b64(page, scale)`: fitz.Page → PNG → base64変換
- `fetch_lm_studio_models(url)`: 利用可能モデル一覧取得
- `call_lm_studio(url, model, b64_image, prompt, ...)`: Vision API呼び出し
- `build_chat_payload(...)`: OpenAI互換リクエストボディ構築
- `OCRMixin._ocr_pages()`: 選択ページに対してThreadPoolExecutorで並列OCR実行

### `pagefolio/ocr_dialog.py` (654 lines)
**OCRDialog** — OCR結果表示用ダイアログ:
- モデル選択・プロンプト選択（text/table/markdown）
- ページ選択・並列度・スケール・タイムアウト・最大トークン設定
- 結果テキストの表示・クリップボードコピー・ファイルエクスポート

### `pagefolio/dialogs.py` (1191 lines)
各種ダイアログクラス:
- `AboutDialog`: バージョン情報・ライセンス表示
- `SettingsDialog`: テーマ・フォントサイズ・言語・LM Studio URL設定
- `PluginDialog`: プラグイン一覧・有効/無効切替
- `MergeOrderDialog`: 結合するPDFファイルの順序指定
- `MergeResizeDialog`: ページサイズ統一オプション選択

### `pagefolio/file_drop.py` (22 lines)
tkinterdnd2 を使ったファイルドロップ設定。`_setup_file_drop(app)` 一関数のみ。

## Entry Points

**スクリプト起動:**
```
pagefolio.py  →  from pagefolio.app import PDFEditorApp
               →  tk.Tk() → PDFEditorApp(root) → root.mainloop()
```

**モジュール起動:**
```
pagefolio/__main__.py  →  同上
```

**起動シーケンス:**
1. `_load_settings()` — `pagefolio_settings.json` 読み込み
2. `_apply_theme()` — `C` 辞書更新
3. `PluginManager.load_all()` — `plugins/*.py` スキャン・ロード
4. `_build_styles()` — ttk スタイル登録
5. `_build_ui()` — ウィジェット構築
6. `root.mainloop()` — イベントループ開始

## Key Files

| File | Purpose | Lines | Notes |
|------|---------|-------|-------|
| `pagefolio/app.py` | アプリルートクラス・Mixin統合 | 376 | 新機能追加時の起点 |
| `pagefolio/constants.py` | テーマ・バージョン・LANG辞書 | 711 | `APP_VERSION` の唯一の真の情報源 |
| `pagefolio/dialogs.py` | 全ダイアログ定義 | 1191 | 最大ファイル |
| `pagefolio/ocr_dialog.py` | OCR UIダイアログ | 654 | OCR機能の全UI |
| `pagefolio/ui_builder.py` | メインUI構築 | 559 | ttk スタイルもここで定義 |
| `pagefolio/page_ops.py` | ページ操作ロジック | 604 | トリミング・結合・分割 |
| `pagefolio/viewer.py` | プレビュー・サムネイル描画 | 446 | 背景スレッド描画 |
| `pagefolio/file_ops.py` | ファイルI/O・Undo/Redo | 340 | スナップショット方式 |
| `pagefolio/ocr.py` | OCR Mixin・LM Studio クライアント | 320 | スタンドアロン関数も含む |
| `pagefolio/plugins.py` | プラグインシステム | 200 | 拡張ポイント |
| `pagefolio/settings.py` | 設定ユーティリティ | 107 | 純粋関数のみ |
| `pagefolio/dnd.py` | サムネイルD&D | 135 | |
| `pagefolio/__init__.py` | 公開APIのre-export | 42 | 後方互換用 |
| `pagefolio/file_drop.py` | ファイルD&D（tkinterdnd2） | 22 | 単一関数 |
| `pagefolio.py` | スクリプトエントリーポイント | 14 | 本体はパッケージ側 |

## Naming Conventions

**Files:**
- Mixin実装: `snake_case.py` (例: `ui_builder.py`, `file_ops.py`, `page_ops.py`)
- 機能単位: `snake_case.py` (例: `ocr_dialog.py`, `file_drop.py`)

**Classes:**
- メインクラス: `PascalCase` (例: `PDFEditorApp`, `PluginManager`)
- Mixin: `PascalCaseMixin` (例: `UIBuilderMixin`, `FileOpsMixin`)
- Dialog: `PascalCaseDialog` (例: `AboutDialog`, `SettingsDialog`)
- Plugin基底: `PDFEditorPlugin`

**Methods:**
- 内部/プライベート: `_prefix` (例: `_open_file`, `_build_ui`)
- 外部API（Mixin間共有も含む）: `_prefix` 統一（全てプライベート扱い）

## Where to Add New Code

**新しいページ操作機能:**
- 実装: `pagefolio/page_ops.py` の `PageOpsMixin` にメソッド追加
- UIボタン: `pagefolio/ui_builder.py` の `_build_tools_scrollable()` に追加
- プラグインフック: `pagefolio/plugins.py` の `PDFEditorPlugin` に新フックを追加し、操作後 `self.plugin_manager.fire_event(...)` を呼ぶ

**新しいダイアログ:**
- 実装: `pagefolio/dialogs.py` に新クラス追加
- `pagefolio/__init__.py` にre-exportを追加

**新しい設定項目:**
- デフォルト値: `pagefolio/settings.py` の `_load_settings()` に追加
- UI: `pagefolio/dialogs.py` の `SettingsDialog` に追加

**新しい定数・文言:**
- 色: `pagefolio/constants.py` の `THEMES` 各テーマに追加
- UI文言: `pagefolio/constants.py` の `LANG` に日本語/英語ペアで追加

**新しいプラグイン:**
- `plugins/myplugin.py` を作成し `PDFEditorPlugin` を継承
- 起動時に自動検出されるためコアコードへの変更不要

**新しいテスト:**
- 場所: `tests/test_<module>.py`
- フィクスチャ: `tests/conftest.py` に共通フィクスチャを追加

## Special Directories

**`plugins/`:**
- Purpose: ユーザー拡張プラグイン置き場
- Generated: No（手動作成）
- Committed: Yes（サンプルプラグイン `page_info.py` 含む）
- Scanned at startup by `PluginManager.discover_plugins()`

**`tests/`:**
- Purpose: pytest テストスイート
- Generated: No
- Committed: Yes

**`docs/`:**
- Purpose: README用スクリーンショット
- Generated: No
- Committed: Yes

**`.planning/`:**
- Purpose: GSD コードベース分析ドキュメント
- Generated: Yes（GSD マッパーが生成）
- Committed: Optional

---

*Structure analysis: 2026-06-01*
