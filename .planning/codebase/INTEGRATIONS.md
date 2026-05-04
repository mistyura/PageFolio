# 外部統合

**分析日:** 2026-05-04

## PDF ライブラリ統合

**PyMuPDF (fitz):**
- 用途: PDF の読み込み・ページ操作・レンダリング・保存のすべて
- SDK/クライアント: `import fitz`
- 使用箇所:
  - `pagefolio/viewer.py` — `fitz.Matrix`, `page.get_pixmap()` でプレビュー・サムネイル生成
  - `pagefolio/file_ops.py` — `fitz.open()`, `doc.tobytes()`, `doc.save()` でファイル読み書き・Undo バッファ
  - `pagefolio/page_ops.py` — `page.set_rotation()`, `page.set_cropbox()`, `doc.delete_page()`, `doc.insert_pdf()` でページ操作
  - `pagefolio/dialogs.py` — `fitz.open()` でファイルページ数取得
- 認証: なし（ローカルライブラリ）
- 注意: 暗号化 PDF は開けない場合がある

## 画像処理統合

**Pillow (PIL):**
- 用途: PyMuPDF ピクセルマップ → Tkinter PhotoImage への変換
- SDK/クライアント: `from PIL import Image, ImageTk`
- 使用箇所: `pagefolio/viewer.py`
  ```python
  img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
  photo = ImageTk.PhotoImage(img)
  ```
- 認証: なし

## UI フレームワーク統合

**Tkinter（標準ライブラリ）:**
- 用途: メイン GUI（ウィンドウ・ウィジェット・イベントループ）
- インポート:
  - `import tkinter as tk`
  - `from tkinter import ttk, messagebox, filedialog, simpledialog`
- 使用箇所: 全モジュール
- スタイルエンジン: `ttk.Style` + `clam` テーマ（`pagefolio/ui_builder.py`）
- フォント: `Segoe UI`（Windows 向け固定）

## ファイルシステム操作

**OS ファイルダイアログ:**
- 使用ライブラリ: `tkinter.filedialog`
- 使用箇所: `pagefolio/file_ops.py`, `pagefolio/page_ops.py`
- 操作一覧:
  - `filedialog.askopenfilename()` — PDF 単一ファイル選択
  - `filedialog.askopenfilenames()` — PDF 複数ファイル選択（挿入・結合）
  - `filedialog.asksaveasfilename()` — 保存先ファイル名選択
  - `filedialog.askdirectory()` — 分割保存先フォルダ選択

**設定ファイル入出力:**
- 形式: JSON（UTF-8）
- パス解決: `pagefolio/settings.py` の `_get_settings_path()`
  - 通常実行: プロジェクトルート `pagefolio_settings.json`
  - PyInstaller exe: `os.path.dirname(sys.executable)` 以下に配置
- 読み書き: `json.load()`, `json.dump()`（`ensure_ascii=False, indent=2`）

**プラグインディレクトリ:**
- パス: `plugins/`（プロジェクトルート相対）
- パス解決: `pagefolio/plugins.py` の `_get_plugins_dir()`（`sys.frozen` 対応）
- 操作: `os.listdir()` でファイル列挙

## ファイル D&D 統合（オプション）

**tkinterdnd2:**
- 用途: プレビューキャンバスへの PDF ファイルのドラッグ＆ドロップ
- SDK/クライアント: `from tkinterdnd2 import TkinterDnD, DND_FILES`
- 使用箇所:
  - `pagefolio/__main__.py` — `TkinterDnD.Tk()` で D&D 対応 root ウィンドウ生成
  - `pagefolio/file_drop.py` — `canvas.drop_target_register(DND_FILES)` で登録
  - `pagefolio/app.py` — `_on_dnd_enter`, `_on_dnd_leave`, `_on_dnd_drop` ハンドラ
- フォールバック: `ImportError` 時は `tk.Tk()` を使用し、D&D なしで動作継続
  ```python
  try:
      from tkinterdnd2 import TkinterDnD
      _HAS_TKDND = True
  except ImportError:
      _HAS_TKDND = False
  ```
- 認証: なし

## OS 統合（Windows 固有）

**システムテーマ検出:**
- 使用ライブラリ: `winreg`（Python 標準ライブラリ、Windows 限定）
- 使用箇所: `pagefolio/settings.py` — `_detect_system_theme()`
- レジストリキー: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`
- 値: `AppsUseLightTheme` (1 = ライト, 0 = ダーク)
- フォールバック: 検出失敗時は `"dark"` を返す

**PyInstaller exe 動作:**
- `sys.frozen` フラグで通常実行 / exe 実行を判定
- 判定箇所: `pagefolio/settings.py`, `pagefolio/plugins.py`
- exe 時のベースパス: `os.path.dirname(sys.executable)`

## プラグインシステム統合

**アーキテクチャ:**
- 基底クラス: `PDFEditorPlugin`（`pagefolio/plugins.py`）
- マネージャー: `PluginManager`（`pagefolio/plugins.py`）
- プラグイン格納: `plugins/` ディレクトリの `.py` ファイル

**動的ロード:**
- 使用ライブラリ: `importlib.util`
  ```python
  spec = importlib.util.spec_from_file_location(f"pagefolio_plugin_{plugin_id}", filepath)
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  ```
- `PDFEditorPlugin` サブクラスを自動検出してインスタンス化

**イベントフック:**
| イベント名 | 発火タイミング |
|-----------|--------------|
| `on_load` | プラグイン有効化時 |
| `on_unload` | プラグイン無効化時 |
| `on_file_open` | PDF ファイルを開いた後 |
| `on_file_save` | PDF ファイルを保存した後 |
| `on_page_rotate` | ページ回転後 |
| `on_page_delete` | ページ削除後 |
| `on_page_crop` | ページトリミング後 |
| `on_page_change` | 表示ページ変更時 |
| `on_insert` | ページ挿入後 |
| `on_merge` | PDF 結合後 |
| `build_ui` | プラグイン UI 構築時 |

**プラグイン設定永続化:**
- 無効化リストを `pagefolio_settings.json` の `disabled_plugins` キーに保存

**サンプルプラグイン:**
- `plugins/page_info.py` — ページ情報表示プラグイン

## ロギング統合

**フレームワーク:** Python 標準 `logging`
- 設定箇所: `pagefolio/app.py` の `PDFEditorApp.__init__()`
  ```python
  logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")
  ```
- 各モジュールで `logger = logging.getLogger(__name__)` を使用
- 本番レベル: `WARNING`（デバッグ情報は `logger.debug()` に限定）

## CI/CD・配布

**ビルドツール:**
- PyInstaller `6.19.0` — Windows exe 生成
- アイコン: `pagefolio.ico`

**CI パイプライン:**
- 検出なし（GitHub Actions 等の設定ファイルは存在しない）

**リポジトリ:**
- GitHub: `https://github.com/mistyura/PageFolio`（README.md に記載）
- ライセンス: MIT

## 環境設定

**必須環境変数:**
- なし（環境変数への依存なし）

**設定ファイルのみで動作:**
- `pagefolio_settings.json` — ユーザー設定（自動生成）
- `.env` ファイルは使用しない

**シークレット:**
- なし（外部サービス接続なし）

---

*統合監査: 2026-05-04*
