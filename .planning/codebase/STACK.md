# 技術スタック

**分析日:** 2026-05-04

## プログラミング言語

**主言語:**
- Python 3.8+ — アプリケーション全体 (`pagefolio/` パッケージ)

**セカンダリ:**
- なし（単一言語プロジェクト）

## ランタイム

**環境:**
- CPython 3.8 以上（Windows 11 向け）
- PyInstaller ビルド時は `sys.frozen == True` で動作パスを分岐（`pagefolio/settings.py`, `pagefolio/plugins.py`）

**パッケージマネージャー:**
- pip
- ロックファイル: `requirements.txt`（バージョン固定済み）

## フレームワーク

**UI:**
- Tkinter（Python 標準ライブラリ）— メイン GUI フレームワーク
  - `ttk.Style` + `clam` テーマを使用（`pagefolio/ui_builder.py`）
  - `tk.PanedWindow`, `ttk.Button`, `ttk.Label`, `tk.Canvas` 等を直接操作

**テスト:**
- pytest `9.0.2` — テストランナー（`tests/` ディレクトリ）
- pytest-cov `7.1.0` — カバレッジ計測

**ビルド:**
- PyInstaller `6.19.0` — Windows exe 化

**リント / フォーマット:**
- Ruff `0.15.7` — リント + フォーマット（`pyproject.toml` で設定）
  - ルールセット: E, F, W, I, S, B
  - 行長: 88文字

## 主要依存ライブラリ

**PDF 処理（コア）:**
- `PyMuPDF (fitz)` `1.27.2.2` — PDF 読み込み・ページ操作・レンダリング
  - `fitz.Document`, `fitz.Matrix`, `page.get_pixmap()` を全操作で使用
  - 使用箇所: `pagefolio/viewer.py`, `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/dialogs.py`

**画像処理:**
- `Pillow (PIL)` `12.2.0` — PyMuPDF ピクセルマップ → Tkinter 表示用変換
  - `Image.frombytes()`, `ImageTk.PhotoImage()` でプレビュー・サムネイル描画
  - 使用箇所: `pagefolio/viewer.py`

**ファイル D&D（オプション）:**
- `tkinterdnd2` `0.4.3` — ファイルのドラッグ＆ドロップ受け取り
  - `TkinterDnD.Tk()` で root ウィンドウを生成
  - 未インストール時は通常の `tk.Tk()` にフォールバック（`pagefolio/__main__.py`）

**PDF 拡張操作（インストール済み・現状未使用の候補）:**
- `pikepdf` `10.5.0` — 高度な PDF 編集
- `pypdf` `6.9.0` — PDF 操作代替ライブラリ
- `pdf2image` `1.17.0` — PDF→画像変換

**画像/OCR（インストール済み・現状参照のみ）:**
- `opencv-python` `4.13.0.92` — 画像処理
- `pytesseract` `0.3.13` — OCR
- `numpy` `2.4.4` — 数値計算

**ビルド補助:**
- `pyinstaller-hooks-contrib` `2026.3` — PyInstaller フック
- `pywin32-ctypes` `0.2.3` — Windows API アクセス
- `altgraph` `0.17.4` — PyInstaller 依存
- `pefile` `2024.8.26` — PyInstaller 依存
- `setuptools` `82.0.1` — パッケージングユーティリティ

**その他:**
- `colorama` `0.4.6` — ターミナルカラー出力
- `coverage` `7.13.5` — テストカバレッジ
- `defusedxml` `0.7.1` — 安全なXML解析
- `Deprecated` `1.3.1` — 非推奨デコレータ
- `Pygments` `2.19.2` — シンタックスハイライト
- `lxml` `6.0.2` — XML/HTML処理
- `wrapt` `2.1.2` — デコレータユーティリティ
- `iniconfig` `2.3.0` — pytest 依存
- `packaging` `26.0` — バージョン解析
- `pluggy` `1.6.0` — pytest プラグインエンジン
- `git-filter-repo` `2.47.0` — 開発ツール（git 履歴操作）

## 設定ファイル

**ビルド / リント:**
- `pyproject.toml` — Ruff 設定（行長88、ルールセット）、pytest 設定（testpaths, pythonpath）

**ランタイム設定:**
- `pagefolio_settings.json` — 実行時に自動生成（テーマ・フォントサイズ・言語・ウィンドウ位置等）
  - デフォルト: `{"theme": "dark", "font_size": 12, "lang": "ja"}`

**依存管理:**
- `requirements.txt` — 全依存パッケージのバージョン固定リスト

## コマンド早見表

```bash
# 起動
python pagefolio.py
python -m pagefolio

# テスト
pytest

# リント・フォーマット
ruff check . && ruff format .
```

## プラットフォーム要件

**開発環境:**
- Windows 11（推奨・主対象）
- Python 3.8+
- pip で `requirements.txt` をインストール

**本番（配布）:**
- PyInstaller で生成した Windows exe（`sys.frozen` 判定で動作）
- アイコン: `pagefolio.ico`

---

*スタック分析: 2026-05-04*
