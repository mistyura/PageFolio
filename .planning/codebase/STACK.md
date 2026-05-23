# STACK.md
_Generated: 2026-05-23_
_Focus: tech_

## Technology Stack

**Analysis Date:** 2026-05-23

## Languages

**Primary:**
- Python 3.8+ — アプリケーション全体（GUI、PDF処理、プラグイン）

**Secondary:**
- なし（単一言語プロジェクト）

## Runtime

**Environment:**
- CPython 3.8 以上（Windows 11 を主要ターゲット）
- `sys.frozen` フラグで PyInstaller ビルド環境を検出（`pagefolio/settings.py`、`pagefolio/plugins.py`）

**Package Manager:**
- pip（ロックファイル: `requirements.txt`）
- Lockfile: `requirements.txt` に固定バージョン記載

## Frameworks

**Core:**
- Tkinter（Python 標準ライブラリ） — メインウィンドウ・ウィジェット・ダイアログ
- ttk（tkinter.ttk） — スタイル付きウィジェット（`TButton`, `TLabel`, `TFrame` 等）
  - テーマエンジン: `ttk.Style().theme_use("clam")`（`pagefolio/ui_builder.py`）

**Testing:**
- pytest 9.0.2 — テストランナー（`tests/` 配下）
- pytest-cov 7.1.0 — カバレッジ計測

**Build/Dev:**
- ruff 0.15.7 — リント＋フォーマット（`pyproject.toml` で設定）
- PyInstaller 6.19.0 — Windows 向け exe ビルド（`PageFolio.spec`）

## Key Dependencies

**Critical:**
- `PyMuPDF==1.27.2.2`（import名: `fitz`） — PDF の読み書き・ページ操作・レンダリング・画像→PDF変換
  - 使用箇所: `pagefolio/file_ops.py`, `pagefolio/page_ops.py`, `pagefolio/viewer.py`, `pagefolio/dialogs.py`
- `Pillow==12.2.0`（import名: `PIL`） — PDF レンダリング結果を Tkinter 表示可能な `ImageTk.PhotoImage` に変換
  - 使用箇所: `pagefolio/viewer.py`
- `tkinterdnd2==0.4.3` — プレビューキャンバスへのファイルドロップ（`DND_FILES`）
  - 使用箇所: `pagefolio/file_drop.py`, `pagefolio/__main__.py`
  - **オプション依存**: `ImportError` 時はファイルD&D機能を無効化してアプリは起動継続

**Infrastructure:**
- `pyinstaller==6.19.0` — 単一 exe ビルド（UPX 圧縮有効、コンソール非表示）
- `pytest==9.0.2` / `pytest-cov==7.1.0` — テスト・カバレッジ
- `ruff==0.15.7` — リント（E, F, W, I, S, B ルールセット）＋フォーマット（行長 88）

## Configuration

**Environment:**
- 環境変数は使用しない
- ユーザー設定は `pagefolio_settings.json`（JSON）に永続化
  - 設定項目: `theme`（dark/light/system）, `font_size`（8〜16）, `lang`（ja/en）, `edit_mode`（bool）, `window_geometry`（str）, `disabled_plugins`（リスト）
  - パス解決: `pagefolio/settings.py` の `_get_settings_path()`（実行ファイルと同じディレクトリ）

**Build:**
- `pyproject.toml` — ruff 設定（lint ルール・行長・テストパス）
- `PageFolio.spec` — PyInstaller ビルド設定（UPX 圧縮、アイコン: `pagefolio.ico`、コンソール非表示）
- ビルドコマンド: `pyinstaller PageFolio.spec`

## Platform Requirements

**Development:**
- Python 3.8 以上
- Windows 11（システムテーマ検出に `winreg` を使用: `pagefolio/settings.py`）
- 依存インストール: `pip install -r requirements.txt`

**Production:**
- Windows 11（主要ターゲット）
- PyInstaller による単一 exe 配布（`dist/PageFolio.exe`）
- exe と同じディレクトリに `plugins/` フォルダおよび `pagefolio_settings.json` を配置

## Standard Library Usage

| モジュール | 用途 |
|------------|------|
| `tkinter`, `tkinter.ttk` | UI全体 |
| `tkinter.filedialog`, `messagebox`, `simpledialog` | ダイアログ |
| `json` | 設定ファイル読み書き |
| `os`, `os.path` | ファイル・パス操作 |
| `logging` | デバッグログ（WARNING レベル以上を出力） |
| `importlib`, `importlib.util` | プラグインの動的読み込み |
| `threading` | サムネイル・プレビューの非同期レンダリング |
| `winreg` | Windows システムテーマ検出 |
| `sys` | PyInstaller 実行判定 |

---

*Stack analysis: 2026-05-23*
