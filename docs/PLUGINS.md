<!-- generated-by: gsd-doc-writer -->
# プラグイン開発ガイド

## 概要

PageFolio はプラグインシステムを備えており、`plugins/` ディレクトリに Python ファイルを配置するだけで機能を追加できます。プラグインはアプリ本体のライフサイクルイベントを受け取り、独自の UI を右ツールパネルに追加したり、OCR プロバイダを登録したりできます。

---

## プラグインの基本構造

プラグインは `pagefolio.plugins.PDFEditorPlugin` を継承したクラスを 1 つ持つ Python ファイルです。

```python
from pagefolio.plugins import PDFEditorPlugin

class MyPlugin(PDFEditorPlugin):
    name        = "プラグイン名"
    version     = "1.0.0"
    description = "プラグインの説明"
    author      = "作者名"
```

### クラス属性

| 属性 | 型 | 説明 |
|------|----|------|
| `name` | `str` | プラグイン管理画面に表示される名前 |
| `version` | `str` | バージョン文字列（例: `"1.0.0"`） |
| `description` | `str` | プラグインの説明 |
| `author` | `str` | 作者名 |

---

## ライフサイクルフック

`PDFEditorPlugin` が提供するフックを必要なものだけオーバーライドします。未オーバーライドのフックは何もせずに返ります。

### `on_load(self, app)`

プラグインがロードまたは有効化されたときに呼ばれます。初期化処理（リソース確保、状態変数の準備）をここで行います。

```python
def on_load(self, app):
    self._cache = {}
```

### `on_unload(self, app)`

プラグインがアンロードまたは無効化されたときに呼ばれます。確保したリソースを解放します。

```python
def on_unload(self, app):
    self._cache.clear()
```

### `on_file_open(self, app, path)`

PDF ファイルが開かれた後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `path` | 開いたファイルのパス（`str`） |

### `on_file_save(self, app, path)`

ファイルが保存された後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `path` | 保存先パス（`str`） |

### `on_page_rotate(self, app, pages, degrees)`

ページが回転された後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `pages` | 回転されたページインデックスのコレクション |
| `degrees` | 回転角度（`int`） |

### `on_page_delete(self, app, pages)`

ページが削除された後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `pages` | 削除されたページインデックスのコレクション |

### `on_page_crop(self, app, page_index)`

ページがトリミングされた後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `page_index` | トリミングされたページの 0 始まりインデックス（`int`） |

### `on_page_change(self, app, page_index)`

プレビューで表示するページが切り替わったときに呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `page_index` | 新しい表示ページの 0 始まりインデックス（`int`） |

### `on_insert(self, app, paths, insert_at)`

ページが挿入された後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `paths` | 挿入元ファイルパスのリスト |
| `insert_at` | 挿入先ページインデックス（`int`） |

### `on_merge(self, app, paths)`

PDF が結合された後に呼ばれます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `paths` | 結合したファイルパスのリスト |

### `build_ui(self, app, parent)`

右ツールパネルにプラグイン独自の UI を構築します。`parent` に Tkinter ウィジェットを追加すると、右パネルのプラグインセクションに表示されます。

| 引数 | 説明 |
|------|------|
| `app` | `PDFEditorApp` インスタンス |
| `parent` | UI を追加する `tk.Frame` |

```python
def build_ui(self, app, parent):
    import tkinter as tk
    from pagefolio.constants import C

    label = tk.Label(
        parent,
        text="Hello from MyPlugin",
        bg=C["BG_CARD"],
        fg=C["TEXT_MAIN"],
        font=app._font(-1),
    )
    label.pack(fill="x", padx=8, pady=4)
```

---

## OCR プロバイダの登録

`register_ocr_provider` フックを使うと、プラグインが独自の OCR バックエンドを追加できます。登録したプロバイダは、アプリの OCR プロバイダ選択画面に表示されます。

### 手順

1. `pagefolio.ocr_providers.OCRProvider` を継承したプロバイダクラスを実装します。
2. `on_load` 内で `app.plugin_manager.register_ocr_provider(name, cls)` を呼び出します。

```python
from pagefolio.ocr_providers import OCRProvider
from pagefolio.plugins import PDFEditorPlugin


class MyOCRProvider(OCRProvider):
    default_concurrency = 1
    max_concurrency = 4

    def ocr_image(self, b64_png, prompt, **kwargs):
        # b64_png: PNG 画像の base64 文字列
        # 実装例: 独自 API へリクエストを送り OCR テキストを返す
        raise NotImplementedError

    def list_models(self):
        return ["my-model-v1"]


class MyOCRPlugin(PDFEditorPlugin):
    name    = "MyOCR プロバイダ"
    version = "1.0.0"

    def on_load(self, app):
        app.plugin_manager.register_ocr_provider("my_ocr", MyOCRProvider)
```

### `register_ocr_provider(name, cls)` の仕様

| 引数 | 型 | 説明 |
|------|----|------|
| `name` | `str` | プロバイダ識別名（例: `"my_ocr"`）。`build_provider` から参照される。 |
| `cls` | `type` | `OCRProvider` のサブクラス（インスタンスではなくクラスを渡すこと） |

`cls` が `OCRProvider` のサブクラスでない場合は `TypeError` が送出されます。

### `OCRProvider` の実装要件

| メソッド | 戻り値 | 説明 |
|----------|--------|------|
| `ocr_image(self, b64_png, prompt, **kwargs)` | `str` | PNG の base64 を受け取り OCR テキストを返す |
| `list_models(self)` | `list[str]` | 利用可能なモデル ID の一覧を返す（取得不能時は空リスト） |

送出しうる例外: `ConnectionError`、`TimeoutError`、`OCRAPIKeyError`、`RuntimeError`

---

## プラグインの配置方法

プラグインファイルは **プロジェクトルートの `plugins/` ディレクトリ** に配置します。

```
PageFolio/
└── plugins/
    ├── page_info.py     ← サンプルプラグイン（同梱済み）
    └── my_plugin.py     ← 自作プラグインをここに追加
```

### 命名規則

- ファイル名は `snake_case.py` とします（例: `my_plugin.py`）。
- `_` で始まるファイル（例: `__init__.py`）は自動検出の対象外です。
- 1 ファイルに `PDFEditorPlugin` のサブクラスを **1 つだけ** 定義します（複数あると最初に見つかったものだけ読み込まれます）。

### 読み込みタイミング

アプリ起動時に `PluginManager.load_all()` が呼ばれ、`plugins/` 内の全 `.py` ファイルが検出・ロードされます。アプリ起動後にファイルを追加した場合は、アプリを再起動するか、プラグイン管理画面から手動でリロードしてください。

### 有効・無効の切り替え

メニューの「プラグイン」から管理画面を開き、各プラグインの有効・無効を切り替えられます。無効状態のプラグインは `fire_event` によるイベント通知を受け取りません。設定は `pagefolio_settings.json` に保存されます。

---

## サンプルプラグイン：`plugins/page_info.py`

同梱の `page_info.py` は最も基本的なプラグインの実装例です。現在のページのサイズ・回転角度・CropBox 情報を右ツールパネルに表示します。

### 実装のポイント

**テーマ色の参照**

`build_ui` 内では `from pagefolio.constants import C` でテーマ辞書を参照します。ハードコードした色文字列は使いません。

```python
from pagefolio.constants import C

self._label = tk.Label(parent, bg=C["BG_CARD"], fg=C["TEXT_SUB"])
```

**フォントサイズの参照**

`app._font(delta)` ヘルパーでベースフォントサイズからの相対指定を使います。

```python
font=app._font(-2)  # ベースより 2pt 小さいフォント
```

**ラベルの更新パターン**

`build_ui` で `self._label` を保持しておき、各イベントフックから `_update_info(app)` を呼び出してラベルを更新します。

```python
def on_page_change(self, app, page_index):
    self._update_info(app)

def _update_info(self, app):
    if not self._label:
        return
    # app.doc, app.current_page を参照してテキストを構築
    page = app.doc[app.current_page]
    self._label.configure(text=f"ページ {app.current_page + 1} / {len(app.doc)}")
```

**`app.doc` の存在確認**

`on_file_open` 以外のフックが呼ばれた時点では `app.doc` が `None` の場合があります。必ず `if not app.doc:` で確認してから参照します。

---

## よく使う `app` の属性

プラグインのフック内で参照できる主要な属性を示します。

| 属性 | 型 | 説明 |
|------|----|------|
| `app.doc` | `fitz.Document \| None` | 現在開いている PDF ドキュメント |
| `app.current_page` | `int` | 現在表示中のページ（0 始まり） |
| `app.selected_pages` | `set[int]` | 複数選択中のページインデックス集合 |
| `app.filepath` | `str \| None` | 現在開いているファイルのパス |
| `app.plugin_manager` | `PluginManager` | プラグインマネージャー本体 |
| `app._font(delta)` | `tuple` | フォント指定ヘルパー（`delta` はベースからの相対 pt） |

---

## 注意事項

- フック内で例外が発生しても、アプリ本体はクラッシュしません。例外は `logger.exception` で記録され、他のプラグインへのイベント通知は継続されます。
- `build_ui` は起動時だけでなく、テーマ・フォント・言語変更時の `_rebuild_ui` や、プラグイン管理画面からの `_reload_plugins` でも再呼び出しされます。ウィジェットを生成する際は既存ウィジェットを破棄してから再生成するか、冪等に動作するよう実装してください。テーマ色は `build_ui` 内で `C` 辞書を直接参照することで最新の値を取得できます。
- `fitz.Document` はスレッド間で共有しないでください。バックグラウンドスレッドから `app.doc` を直接操作すると競合が発生します。
- プラグインが追加する UI は右ツールパネルの Canvas 上に配置されます。高さが大きい UI を追加する場合はスクロールが必要になることがあります。
