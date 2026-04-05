# PageFolio

## What It Is

Windows 向け PDF ページ編集アプリケーション。Python + Tkinter によるデスクトップアプリ。PDF のページ操作（回転・削除・トリミング・並び替え・結合・分割・挿入）をビジュアル UI で提供する。

## Current State

- **バージョン**: v0.9.6
- **成熟度**: プレリリース段階。主要機能は実装済み、PyInstaller での exe ビルドも対応済み
- **コード規模**: `pagefolio/` パッケージ（13ファイル, 約3,265行）+ テスト（約989行, 78件）
- **テスト**: pytest によるユーティリティ・PDF操作・プラグインのテスト整備済み
- **リント**: Ruff 導入済み（`pyproject.toml` に設定）

## Tech Stack

| レイヤー | 技術 |
|---------|------|
| 言語 | Python 3.8+ |
| UI | Tkinter (ttk) |
| PDF | pymupdf (fitz) |
| 画像 | Pillow (PIL) |
| リント | Ruff |
| テスト | pytest |
| ビルド | PyInstaller |
| 対象 OS | Windows 11 |

## Architecture

`pagefolio/` パッケージに Mixin パターンで分割:

- **`PDFEditorApp`** (`app.py`, 265行) — メインクラス。5つの Mixin を統合し、`__init__`・キーバインド・ユーティリティメソッドを持つ
- **`UIBuilderMixin`** (`ui_builder.py`, 480行) — スタイル定義・レイアウト構築
- **`FileOpsMixin`** (`file_ops.py`, 194行) — ファイル操作・Undo/Redo
- **`PageOpsMixin`** (`page_ops.py`, 423行) — ページ回転・削除・トリミング・挿入・結合・分割
- **`ViewerMixin`** (`viewer.py`, 379行) — プレビュー・ズーム・サムネイル・ポップアップ
- **`DnDMixin`** (`dnd.py`, 114行) — サムネイル D&D 並び替え
- **`constants.py`** (439行) — テーマカラー(THEMES/C)、バージョン、言語辞書(LANG)
- **`settings.py`** (90行) — 設定ファイル読み書き・テーマ解決・フォント生成
- **`plugins.py`** (203行) — プラグインシステム（PDFEditorPlugin基底 + PluginManager）
- **`dialogs.py`** (595行) — About/Settings/Plugin/MergeOrder の4ダイアログ
- **`file_drop.py`** (22行) — tkinterdnd2 連携

テーマは `THEMES` 辞書で定義し、`C` グローバル辞書経由で参照。設定は `pagefolio_settings.json` に JSON 永続化。

## Key Constraints

- `pagefolio/` パッケージの Mixin パターンを維持すること
- `pyproject.toml` / `ruff.toml` は編集禁止
- すべての応答・コミットメッセージ・ドキュメントは日本語
- ソースコード中の変数名・関数名・クラス名は英語
