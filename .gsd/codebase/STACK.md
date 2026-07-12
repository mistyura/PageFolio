---
last_mapped_commit: fb41c422035fa9d4fac753920909da56e068555c
---

# PageFolio — 技術スタック (Technology Stack)

## 言語 & ランタイム (Language & Runtime)
- **Python**: 3.8+ (型ヒントは 3.8 互換)
- **仮想環境**: `venv/` (Windows 開発環境向け)
- **パッケージマネージャー**: `pip` (依存関係は `requirements.txt` で管理)

## 主要フレームワーク & 外部ライブラリ (Core Frameworks & Libraries)
このプロジェクトは標準の GUI ライブラリである Tkinter と、PDF 処理用の PyMuPDF を核とした軽量デスクトップアプリケーションです。

| ライブラリ名 | バージョン | 用途 | 主な使用パターン |
| :--- | :--- | :--- | :--- |
| **Tkinter** | 標準付属 | GUI フレームワーク | `tk.Tk`, `ttk.Button`, `tk.Canvas` によるウィジェット構築 |
| **PyMuPDF (fitz)** | `1.28.0` | PDF 読み書き・レンダリング | `fitz.open()`, `page.get_pixmap()`, `doc.save()`, 矩形編集等 |
| **Pillow (PIL)** | `12.3.0` | 画像変換・表示用 | `Image`, `ImageTk.PhotoImage` によるプレビュー・サムネイル描画 |
| **tkinterdnd2** | `0.6.2` | ファイルおよびサムネイル D&D | `TkinterDnD.Tk`, `DND_FILES`, `drop_target_register()` |

## ビルド & 開発ツール (Build & Tooling)

| ツール名 | バージョン | 用途 | 設定箇所 |
| :--- | :--- | :--- | :--- |
| **Ruff** | `0.15.20` | 静的解析・自動フォーマッタ | `pyproject.toml` |
| **PyInstaller** | `6.21.0` | Windows 実行ファイル化 | `PageFolio.spec` (onedir 形式) |
| **pytest** | `9.1.1` | テストランナー | `pyproject.toml` |
| **pytest-cov** | `7.1.0` | カバレッジ計測ツール | `pyproject.toml` |

## Python 標準ライブラリの利用状況 (Standard Library Usage)
- **GUI & ダイアログ**: `tkinter`, `tkinter.ttk`, `tkinter.filedialog`, `messagebox`, `simpledialog`
- **非同期/並列処理**: `threading` (OCR 進捗ダイアログ・非同期モデル取得), `concurrent.futures.ThreadPoolExecutor` (OCR 並列処理)
- **ネットワーク & 通信**: `urllib.request` (LM Studio などの API 呼び出し), `socket`, `base64`, `json`
- **ファイル & ディレクトリ操作**: `os` (パス処理・一時ディレクトリ監視), `shutil` (フォルダ一括削除), `tempfile` (印刷一時ファイルおよび Undo 用 Blob の退避)
- **フック & ライフサイクル**: `atexit` (アプリ終了時の Undo 一時ディレクトリ削除), `importlib`, `importlib.util` (プラグインの動的検出・ロード)
- **ログ**: `logging`

## プラットフォーム制約 (Platform Constraints)
- **対象 OS**: Windows 11 推奨 (印刷機能などの一部 OS 依存処理あり)
- **印刷方式**: Windows の `os.startfile(path, "print")` を前提としており、他の OS では非サポート。
