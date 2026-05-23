# STRUCTURE.md
_Generated: 2026-05-23_
_Focus: arch_

**Analysis Date:** 2026-05-23

---

## ディレクトリレイアウト

```
PageFolio/
├── pagefolio.py               # エントリーポイント（python pagefolio.py で起動）
├── pagefolio/                 # メインパッケージ
│   ├── __init__.py            # 後方互換の公開 API（全主要クラスを re-export）
│   ├── __main__.py            # python -m pagefolio エントリーポイント
│   ├── constants.py           # THEMES / C / APP_VERSION / LANG / ファイル定数
│   ├── settings.py            # 設定読み書き・テーマ適用ユーティリティ
│   ├── plugins.py             # PDFEditorPlugin 基底クラス + PluginManager
│   ├── app.py                 # PDFEditorApp 本体（Mixin 統合 + 状態管理）
│   ├── ui_builder.py          # UIBuilderMixin（スタイル・レイアウト）
│   ├── file_ops.py            # FileOpsMixin（open/save/undo/redo）
│   ├── page_ops.py            # PageOpsMixin（回転/削除/トリミング/挿入/結合/分割）
│   ├── viewer.py              # ViewerMixin（プレビュー/ズーム/サムネイル/ポップアップ）
│   ├── dnd.py                 # DnDMixin（サムネイル D&D 並び替え）
│   ├── dialogs.py             # ダイアログ群（About/Settings/Plugin/MergeOrder/MergeResize）
│   └── file_drop.py           # tkinterdnd2 によるファイルドロップ登録
├── plugins/                   # プラグインディレクトリ（ユーザー拡張用）
│   └── page_info.py           # サンプルプラグイン（ページ情報表示）
├── tests/                     # テストスイート（pytest）
│   ├── __init__.py
│   ├── conftest.py            # 共通フィクスチャ（sample_pdf, tmp_settings 等）
│   ├── test_utils.py          # ユーティリティ関数テスト（35件）
│   ├── test_pdf_ops.py        # PDF 操作テスト（34件）
│   └── test_plugins.py        # PluginManager テスト（17件）
├── docs/                      # スクリーンショット画像
├── pagefolio.ico              # アプリアイコン
├── README.md                  # エンドユーザー向け使用概要
├── CLAUDE.md                  # AI 向け開発指示書
├── 開発履歴.md                # 機能追加・変更履歴
├── LICENSE                    # MIT ライセンス
├── pyproject.toml             # Ruff + pytest 設定
└── pagefolio_settings.json    # ユーザー設定（実行時自動生成・gitignore 対象）
```

---

## ディレクトリ目的

### `pagefolio/` — メインパッケージ

アプリケーション本体のすべてのコードを含む Python パッケージ。機能ごとにモジュール分割されており、`PDFEditorApp` は Mixin 多重継承で統合される。

**ファイル一覧と役割:**

| ファイル | クラス/関数 | 役割 |
|---------|-----------|------|
| `app.py` | `PDFEditorApp` | 状態管理・キーバインド・初期化・ユーティリティ |
| `ui_builder.py` | `UIBuilderMixin` | スタイル定義・3ペインレイアウト |
| `file_ops.py` | `FileOpsMixin` | ファイル開閉・保存・Undo/Redo |
| `page_ops.py` | `PageOpsMixin` | ページ編集操作全般 |
| `viewer.py` | `ViewerMixin` | プレビュー・サムネイル・ナビゲーション |
| `dnd.py` | `DnDMixin` | サムネイル D&D |
| `dialogs.py` | 5ダイアログクラス | モーダルダイアログ群 |
| `plugins.py` | `PDFEditorPlugin`, `PluginManager` | プラグインシステム |
| `constants.py` | `THEMES`, `C`, `LANG`, 定数 | テーマ・言語・設定定数 |
| `settings.py` | 各種関数 | 設定ファイルの読み書き・テーマ適用 |
| `file_drop.py` | `_setup_file_drop()` | ファイル D&D 登録 |
| `__init__.py` | — | 後方互換の公開 API |
| `__main__.py` | `main()` | `python -m pagefolio` エントリーポイント |

### `plugins/` — ユーザープラグイン

`PDFEditorPlugin` を継承した `.py` ファイルを置くディレクトリ。アプリ起動時に自動検出される。`page_info.py` はサンプルプラグイン。

### `tests/` — テストスイート

pytest で実行するテストファイル群。Tkinter を直接使用しないビジネスロジックのみをテストする。

### `docs/` — ドキュメント

スクリーンショット等の静的アセット。README.md から参照される。

---

## エントリーポイント

### `pagefolio.py` (プロジェクトルート)

```python
# pagefolio.py
from pagefolio.__main__ import main
if __name__ == "__main__":
    main()
```

`python pagefolio.py` で起動する薄いラッパー。実処理は `pagefolio/__main__.py` に委譲する。

### `pagefolio/__main__.py`

```python
def main():
    if _HAS_TKDND:
        root = TkinterDnD.Tk()   # tkinterdnd2 利用可能時
    else:
        root = tk.Tk()
    app = PDFEditorApp(root)
    _setup_file_drop(app)
    root.mainloop()
```

`python -m pagefolio` でも起動可能。tkinterdnd2 の有無を判定し、適切な root を生成する。

---

## モジュール間 import 関係

```
pagefolio.py
    └── pagefolio/__main__.py
            ├── pagefolio/app.py (PDFEditorApp)
            │       ├── pagefolio/constants.py (LANG, SUPPORTED_EXTENSIONS, C)
            │       ├── pagefolio/dialogs.py (PluginDialog, SettingsDialog)
            │       ├── pagefolio/dnd.py (DnDMixin)
            │       ├── pagefolio/file_drop.py (_setup_file_drop)
            │       ├── pagefolio/file_ops.py (FileOpsMixin)
            │       ├── pagefolio/page_ops.py (PageOpsMixin)
            │       ├── pagefolio/plugins.py (PluginManager)
            │       ├── pagefolio/settings.py (_apply_theme, _load_settings, _save_settings)
            │       ├── pagefolio/ui_builder.py (UIBuilderMixin)
            │       └── pagefolio/viewer.py (ViewerMixin)
            └── pagefolio/file_drop.py (_setup_file_drop)

pagefolio/dialogs.py
    ├── pagefolio/constants.py (APP_VERSION, LANG, PLUGINS_DIR, C)
    ├── pagefolio/plugins.py (_get_plugins_dir)
    └── pagefolio/settings.py (_current_font_size)

pagefolio/plugins.py
    └── pagefolio/constants.py (PLUGINS_DIR)

pagefolio/settings.py
    └── pagefolio/constants.py (SETTINGS_FILE, THEMES, C)

pagefolio/ui_builder.py
    └── pagefolio/constants.py (C)

pagefolio/viewer.py
    └── pagefolio/constants.py (C)

pagefolio/dnd.py
    └── pagefolio/constants.py (C)

pagefolio/file_ops.py
    └── pagefolio/constants.py (IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS)

pagefolio/page_ops.py
    └── pagefolio/constants.py (IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS, C)
```

**循環インポート回避:** `app.py` の Mixin は `dialogs.py` を遅延インポートする（メソッド内部で `from pagefolio.dialogs import XxxDialog`）。

---

## 設定ファイル

### `pyproject.toml`

```toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "S", "B"]
fixable = ["ALL"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # assert 文の許可

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**編集禁止ファイル:** `pyproject.toml` と `ruff.toml` は変更しない（CLAUDE.md 規約）。

### `pagefolio_settings.json` (実行時生成)

ユーザー設定を JSON で永続化する。プロジェクトルートに生成され、git 管理外とする。

```json
{
  "theme": "dark",
  "font_size": 12,
  "lang": "ja",
  "edit_mode": false,
  "window_geometry": "1200x780+100+50",
  "sash_left": 180,
  "sash_right": 900,
  "disabled_plugins": []
}
```

---

## 命名規則

### ファイル名

- パッケージモジュール: `snake_case.py`（例: `ui_builder.py`, `file_ops.py`）
- テストファイル: `test_*.py`（例: `test_pdf_ops.py`）

### クラス名

- アプリクラス: `PascalCase`（例: `PDFEditorApp`）
- Mixin クラス: `PascalCase + Mixin`（例: `UIBuilderMixin`, `FileOpsMixin`）
- ダイアログクラス: `PascalCase + Dialog`（例: `AboutDialog`, `MergeOrderDialog`）
- プラグイン基底: `PDFEditorPlugin`

### メソッド名

- 内部メソッド: `_` プレフィックス（例: `_open_file`, `_refresh_all`）
- Tkinter コールバック: `_on_xxx` 形式（例: `_on_dnd_drop`, `_on_dnd_enter`）
- ビルダーメソッド: `_build_xxx` 形式（例: `_build_ui`, `_build_thumbnails`）

### 変数名

- インスタンス属性: `snake_case`（例: `self.current_page`, `self.thumb_cache`）
- 定数: `UPPER_SNAKE_CASE`（例: `APP_VERSION`, `SETTINGS_FILE`）

---

## テスト構造

```
tests/
├── __init__.py
├── conftest.py          # pytest フィクスチャ
├── test_utils.py        # 設定・ユーティリティ関数テスト（35件）
├── test_pdf_ops.py      # PDF 操作テスト（34件）
└── test_plugins.py      # PluginManager テスト（17件）
```

### フィクスチャ (`conftest.py`)

| フィクスチャ | 返り値 | 用途 |
|------------|--------|-----|
| `tmp_settings(tmp_path)` | `(settings_path, write_fn)` | 一時設定ファイルの作成・管理 |
| `sample_pdf(tmp_path)` | `str` (PDF パス) | 3ページの A4 PDF をファイルとして生成 |
| `sample_pdf_doc()` | `fitz.Document` | 3ページの A4 PDF をメモリ上で生成（yield/close） |
| `multi_pdf_files(tmp_path)` | `list[str]` | 結合・挿入テスト用の複数 PDF（1/2/3 ページ）|

### テスト対象の範囲

Tkinter ウィジェットを必要とする UI コードはテスト対象外。テストは以下のビジネスロジックに集中する:
- `pagefolio/settings.py` の設定読み書き・テーマ解決
- `fitz.Document` を使った PDF 操作ロジック
- `PluginManager` の検出・読込・有効/無効・イベント発火

---

## 新規コードの追加場所

### 新しいページ操作を追加する

1. 実装: `pagefolio/page_ops.py` の `PageOpsMixin` にメソッドを追加
2. ボタン: `pagefolio/ui_builder.py` の `_build_tools()` にボタンを追加
   - `edit_only=True` を指定（編集モードのみ有効）
   - `needs_doc=True` を指定（ファイル必須）
3. プラグインフック: 必要であれば `plugin_manager.fire_event("on_new_op", ...)` を追加
4. テスト: `tests/test_pdf_ops.py` にテストを追加

### 新しいダイアログを追加する

1. `pagefolio/dialogs.py` に `tk.Toplevel` を継承したクラスを追加
2. 呼び出し元 Mixin 内で遅延インポート: `from pagefolio.dialogs import NewDialog`
3. `pagefolio/__init__.py` に re-export を追加（後方互換性のため）

### 新しいプラグインを追加する

1. `plugins/` ディレクトリに `.py` ファイルを作成
2. `PDFEditorPlugin` を継承してフックメソッドを実装
3. アプリ起動時に自動検出される（手動再検出は「プラグイン管理」ダイアログの「再検出」ボタン）

### 新しい設定項目を追加する

1. `pagefolio/settings.py` の `_load_settings()` の `defaults` 辞書にデフォルト値を追加
2. `PDFEditorApp.__init__` でインスタンス属性として読み込む
3. `_save_window_state()` または `_apply_settings()` に保存処理を追加

### 新しい定数・テーマ色を追加する

- テーマ色: `pagefolio/constants.py` の `THEMES["dark"]` と `THEMES["light"]` の両方に追加
- 文字列定数: `pagefolio/constants.py` に追加
- UI テキスト（多言語対応）: `LANG["ja"]` と `LANG["en"]` の両方に同じキーで追加

### 新しいユーティリティ関数を追加する

- PDF 非依存のユーティリティ: `pagefolio/settings.py`
- アプリ共通メソッド: `pagefolio/app.py` の `PDFEditorApp` に直接追加

---

## 特殊ファイル・ディレクトリ

### `pagefolio/__init__.py`

後方互換のための公開 API。主要クラスと関数をすべて re-export する。外部からのインポートはこのファイル経由で行うことができる。

```python
from pagefolio import PDFEditorApp, PDFEditorPlugin, PluginManager
```

### `plugins/` ディレクトリ

- 目的: ユーザー提供のプラグインを配置
- 生成: リポジトリに含まれる（`page_info.py` サンプルあり）
- コミット: サンプルプラグインのみコミット対象。ユーザー独自プラグインは各自管理

### `pagefolio_settings.json`

- 目的: ユーザー設定の永続化
- 生成: 実行時に自動生成
- コミット: しない（ユーザー固有のデータ）

---

*Structure analysis: 2026-05-23*
