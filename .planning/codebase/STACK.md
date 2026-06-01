# Technology Stack

**Analysis Date:** 2026-06-01

## Runtime & Language

**Primary:**
- Python 3.8+ — アプリケーション全体（型ヒントは 3.8 互換）
- 仮想環境: `venv/` (Windows 向け)

**Package Manager:**
- pip（`requirements.txt` で依存管理）
- Lockfile: `requirements.txt`（バージョン固定）

## Core Frameworks & Libraries

| Name | Version | Purpose | Key usage patterns |
|------|---------|---------|-------------------|
| Tkinter | 標準ライブラリ | GUI フレームワーク | `tk.Tk`, `ttk.Button`, `tk.Canvas` でウィジェット構築 |
| PyMuPDF (fitz) | 1.27.2.2 | PDF 読み書き・レンダリング | `fitz.open()`, `page.get_pixmap()`, `doc.save()` |
| Pillow (PIL) | 12.2.0 | 画像変換・表示 | `Image`, `ImageTk.PhotoImage` でプレビュー描画 |
| tkinterdnd2 | 0.4.3 | ファイル D&D サポート | `TkinterDnD.Tk`, `DND_FILES`, `drop_target_register()` |

## Build & Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| Ruff | 0.15.7 | リント・フォーマット（E/F/W/I/S/B ルール） |
| PyInstaller | 6.19.0 | Windows 実行ファイルのビルド（`.exe` 生成） |

**Ruff 設定 (`pyproject.toml`):**
- `line-length = 88`
- `select = ["E", "F", "W", "I", "S", "B"]`
- `tests/**/*.py` で `S101` (assert) を除外

## Development Dependencies

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 9.0.2 | テストランナー |
| pytest-cov | 7.1.0 | カバレッジ計測 |

## Standard Library Usage

アプリ内で使用される主要な標準ライブラリ：

- `tkinter` / `tkinter.ttk` — GUI 全般（`pagefolio/ui_builder.py`, `pagefolio/dialogs.py` など）
- `tkinter.filedialog`, `messagebox`, `simpledialog` — ダイアログ操作
- `json` — 設定ファイル読み書き（`pagefolio/settings.py`）
- `os` — パス操作・ファイル検索
- `logging` — ログ出力（全モジュール）
- `threading` — バックグラウンド処理（`pagefolio/viewer.py`, `pagefolio/ocr_dialog.py`）
- `concurrent.futures.ThreadPoolExecutor` — OCR 並列処理（`pagefolio/ocr.py`）
- `urllib.request` — HTTP 通信（LM Studio API 呼び出し）（`pagefolio/ocr.py`）
- `base64`, `json`, `socket` — OCR リクエスト組み立て（`pagefolio/ocr.py`）
- `importlib`, `importlib.util` — プラグイン動的読み込み（`pagefolio/plugins.py`）

## Infrastructure & Platform

**Target OS:** Windows 11

**Entry Points:**
- `pagefolio.py` — `python pagefolio.py` 起動
- `pagefolio/__main__.py` — `python -m pagefolio` 起動

**Distribution:**
- PyInstaller で単一 `.exe` としてビルド
- アイコン: `pagefolio.ico`

**Python Path:**
- `pyproject.toml` で `pythonpath = ["src"]` を指定（pytest 用）

---

*Stack analysis: 2026-06-01*
