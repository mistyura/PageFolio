# INTEGRATIONS.md
_Generated: 2026-05-23_
_Focus: tech_

## External Integrations

**Analysis Date:** 2026-05-23

## APIs & External Services

**外部ネットワーク API: なし**
- PageFolio はオフラインスタンドアロンアプリケーション
- クラウド・Web API への接続は一切行わない

## PDF 処理ライブラリ（PyMuPDF / fitz）

**ライブラリ:** `PyMuPDF==1.27.2.2`（import: `fitz`）

**統合パターン:**
- ファイル読み込み: `fitz.open(path)` または `fitz.open(stream=bytes, filetype="pdf")`
- 画像→PDF変換: `fitz.open(image_path).convert_to_pdf()`（`pagefolio/file_ops.py`）
- ページレンダリング: `page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))`（`pagefolio/viewer.py`）
- サムネイル生成: `fitz.Matrix(0.22, 0.22)` スケール（`pagefolio/viewer.py`）
- ページ操作: `doc.delete_page()`, `doc.move_page()`, `doc.insert_pdf()`, `doc.select()`
- 回転: `page.set_rotation((page.rotation + deg) % 360)` （`pagefolio/page_ops.py`）
- トリミング: `page.set_cropbox(fitz.Rect(x0, y0, x1, y1))`（MediaBox 内にクランプ必須）
- 保存オプション:
  - 通常保存: `doc.save(path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)`
  - 縮小保存: `doc.save(path, garbage=4, deflate=1, clean=1)` （`pagefolio/file_ops.py`）
  - フォールバック: incremental save 失敗時は `.tmp` ファイル経由で `os.replace()`
- Undo/Redo 用バイト列化: `doc.tobytes()`, `fitz.open(stream=bytes, filetype="pdf")`

## 画像表示ライブラリ（Pillow）

**ライブラリ:** `Pillow==12.2.0`（import: `PIL.Image`, `PIL.ImageTk`）

**統合パターン:**
- fitz Pixmap → PIL Image 変換: `Image.frombytes("RGB", [w, h], samples)` （`pagefolio/viewer.py`）
- PIL Image → Tkinter 表示: `ImageTk.PhotoImage(pil_image)`
- 参照保持: `self.preview_image`（ガベージコレクション防止のため明示的に保持）

## ファイルD&D（tkinterdnd2）

**ライブラリ:** `tkinterdnd2==0.4.3`

**統合パターン:**
- ルートウィンドウ生成: `TkinterDnD.Tk()` の代わりに `tk.Tk()` を選択（`pagefolio/__main__.py`）
- プレビューキャンバスへの登録:
  ```python
  canvas.drop_target_register(DND_FILES)
  canvas.dnd_bind("<<DropEnter>>", app._on_dnd_enter)
  canvas.dnd_bind("<<DropLeave>>", app._on_dnd_leave)
  canvas.dnd_bind("<<Drop>>", app._on_dnd_drop)
  ```
  実装: `pagefolio/file_drop.py`
- **フェイルセーフ設計**: `ImportError` 時は `_HAS_TKDND = False` となり、ファイルD&Dなしで起動
- サムネイルパネル内の並び替えD&Dは tkinterdnd2 ではなく独自マウスイベントで実装（`pagefolio/dnd.py`）

## ファイルシステム連携

**PDFファイル読み書き:**
- 読み込み: `tkinter.filedialog.askopenfilenames()` でユーザーが選択
- 対応形式: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.tif`（`pagefolio/constants.py` の `SUPPORTED_EXTENSIONS`）
- 保存: `tkinter.filedialog.asksaveasfilename()` または上書き確認ダイアログ
- 分割保存: `tkinter.filedialog.askdirectory()` でフォルダ選択

**設定ファイル（`pagefolio_settings.json`）:**
- パス: 実行ファイルと同じディレクトリ（`pagefolio/settings.py` の `_get_settings_path()`）
- 形式: JSON（UTF-8、インデント2）
- 読み書き: `pagefolio/settings.py` の `_load_settings()` / `_save_settings()`
- デフォルト値: `{"theme": "dark", "font_size": 12, "lang": "ja"}`
- 保存タイミング: 設定変更・ウィンドウ終了時（`pagefolio/app.py` の `_on_close()`）

**プラグインディレクトリ（`plugins/`）:**
- パス: 実行ファイルと同じディレクトリの `plugins/` サブフォルダ
- 検出: `os.listdir()` で `.py` ファイルを走査（`pagefolio/plugins.py`）
- `_` 始まりファイルはスキップ

## プラグインシステム統合

**基底クラス:** `pagefolio/plugins.py` の `PDFEditorPlugin`

**プラグイン実装パターン:**
```python
from pagefolio.plugins import PDFEditorPlugin

class MyPlugin(PDFEditorPlugin):
    name = "プラグイン名"
    version = "1.0.0"
    description = "説明"
    author = "作者名"

    def build_ui(self, app, parent):
        # parent (tk.Frame) にウィジェットを配置
        pass

    def on_file_open(self, app, path): ...
    def on_page_change(self, app, page_index): ...
```

**イベントフック一覧（`PDFEditorPlugin` メソッド）:**

| メソッド | 発火タイミング |
|----------|----------------|
| `on_load(app)` | プラグイン有効化時 |
| `on_unload(app)` | プラグイン無効化時 |
| `on_file_open(app, path)` | ファイルオープン後 |
| `on_file_save(app, path)` | ファイル保存後 |
| `on_page_rotate(app, pages, degrees)` | ページ回転後 |
| `on_page_delete(app, pages)` | ページ削除後 |
| `on_page_crop(app, page_index)` | ページトリミング後 |
| `on_page_change(app, page_index)` | 表示ページ変更時 |
| `on_insert(app, paths, insert_at)` | ページ挿入後 |
| `on_merge(app, paths)` | PDF結合後 |
| `build_ui(app, parent)` | プラグインUIパネル構築時 |

**イベント発火:** `PluginManager.fire_event(event_name, *args, **kwargs)` — 有効プラグインのみに通知、例外は `logger.exception()` で吸収

**動的読み込み:**
- `importlib.util.spec_from_file_location()` でファイルパスから直接読み込み
- `PDFEditorPlugin` のサブクラスを `dir(module)` で自動検出
- モジュール名: `pagefolio_plugin_{plugin_id}`

**サンプルプラグイン:** `plugins/page_info.py`（`PageInfoPlugin` — ページサイズ・回転・CropBox 表示）

## Windows システム統合

**システムテーマ検出:**
- `winreg` でレジストリキー `Software\Microsoft\Windows\CurrentVersion\Themes\Personalize` の `AppsUseLightTheme` を読み取り
- 実装: `pagefolio/settings.py` の `_detect_system_theme()`
- テーマ設定 `"system"` 時に呼び出される

**フォント:**
- フォントファミリー: `"Segoe UI"`（Windows システムフォント固定）
- `pagefolio/settings.py` の `_make_font(delta, weight, base_size)` ヘルパーで生成

## 非同期処理

**サムネイル・プレビュー生成:**
- `threading.Thread` を使用してバックグラウンドレンダリング（`pagefolio/viewer.py`）
- 世代カウンタ（`self._preview_gen`, `self._thumb_gen`）で古いスレッドの結果を破棄
- Tkinter への反映は `canvas.after(0, callback)` 経由でメインスレッドに委譲

## 将来的な統合候補

**PDF パスワード解除対応:**
- 現在: 暗号化 PDF は `fitz.open()` が失敗する場合がある
- 対応案: `fitz.Document.authenticate()` の組み込み

**印刷機能:**
- 現在: 未実装
- 対応案: `subprocess` で OS の印刷コマンド（`win32print` 等）を呼び出し

**他プラットフォーム対応:**
- 現在: Windows 11 専用（`winreg`、`Segoe UI` フォント依存）
- 対応案: `winreg` 読み込みの try/except による macOS/Linux フォールバック（既に try/except 済み）、フォントのクロスプラットフォーム化

---

*Integration audit: 2026-05-23*
