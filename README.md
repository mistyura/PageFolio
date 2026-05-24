# PageFolio

**PDF ページ整理ツール — Python + Tkinter 製 GUI アプリ**

![Version](https://img.shields.io/badge/version-v1.1.2-blue)
![Stable](https://img.shields.io/badge/status-stable-green)

A PDF page organizer built with Python + Tkinter.
Windows 11 で動作します / Runs on Windows 11.

> 📝 このプロジェクトは [Claude Code](https://claude.ai/code)（Anthropic）を活用して開発されています。
> AI との協調開発のユースケースとして公開しており、開発指示書（`CLAUDE.md`）と開発履歴（`開発履歴.md`）も併せて公開しています。
>
> This project is developed with [Claude Code](https://claude.ai/code) by Anthropic,
> and published as a use case of AI-assisted development.

---

## 概要 / Overview

PageFolio は PDF のページを整理・編集するための GUI ツールです。
テキスト編集や注釈追加は行いません。**ページ単位の操作に特化しています。**

PageFolio is a GUI tool for organizing and editing PDF pages.
It does **not** edit text or add annotations — it focuses on **page-level operations**.

---

## 機能 / Features

| 機能 | 説明 |
|------|------|
| 📂 ファイルを開く | PDF・PNG・JPG・BMP・TIFF を読み込み（複数選択時は結合） |
| 💾 保存 | 上書き保存 / 名前を付けて保存 |
| 🔄 ページ回転 | 90° / 180° / 270°、複数ページ一括対応 |
| 🗑 ページ削除 | 選択ページをまとめて削除 |
| ✂ トリミング | プレビュー上のドラッグで余白をカット（複数選択ページ一括適用） |
| 📋 ページ複製 | 現在のページを直後に複製して挿入 |
| 📎 挿入・結合 | 別 PDF からページを挿入 / 末尾に結合 |
| 📐 ページ結合・リサイズ | 選択した複数ページを横並び/縦並びで1枚に結合（例: 2× A4 → 1× A3） |
| ✂ 分割 | ページ範囲指定で分割 / 1ページずつ個別PDFに分割（縮小オプション付き） |
| 🗜 縮小保存 | garbage収集 + 圧縮でファイルサイズを最適化して保存 |
| 🔀 D&D 並び替え | サムネイルをドラッグ＆ドロップでページ順を変更（複数ページ一括移動対応） |
| 📕 ファイルを閉じる | アプリを終了せず現在のファイルだけを閉じる |
| ↩ Undo / Redo | 最大20回の取り消し・やり直し（Ctrl+Z / Ctrl+Y） |
| 🔍 プレビュー | ズーム・スクロール対応、ページ拡大表示 |
| 👁 閲覧/編集モード | ヘッダーボタン（F5）でモード切替。閲覧モードは編集ボタンが非活性 |
| ⚙ テーマ・フォント | ダーク / ライト / システム連動、フォントサイズ変更 |
| 🪟 ウィンドウ状態引き継ぎ | 前回終了時のウィンドウ位置・サイズを次回起動時に復元 |

---

## ダウンロード / Download

[Releases](https://github.com/mistyura/PageFolio/releases) から最新の `PageFolio.exe` をダウンロードしてください。
Python のインストールは不要です。ダブルクリックで起動できます。

Download the latest `PageFolio.exe` from [Releases](https://github.com/mistyura/PageFolio/releases).
No Python installation required — just double-click to run.

---

## 画面構成 / Screenshots

![ダークテーマ（日本語）](docs/メイン（ダーク）-日本語.png)
![ダークテーマ（複数選択）](docs/メイン（ダーク）-日本語-2.png)
![ライトテーマ（日本語）](docs/メイン（ライト）-日本語.png)
![ライトテーマ（英語）](docs/メイン（ライト）-英語.png)
![読み込み画面](docs/メイン（ダーク）-読込.png)
![PDF結合画面](docs/メイン（ダーク）-結合.png)

---

## 注意事項 / Notes

- トリミング・回転・削除は **選択中のページ** が対象です（未選択の場合は現在ページ）
- 保存前にアプリを閉じると編集内容は失われます
- 暗号化・パスワード保護された PDF は開けない場合があります

---

## 🐛 バグ報告・フィードバック / Bug Reports

不具合・要望は [Issues](https://github.com/mistyura/PageFolio/issues) からお知らせください。
Please report bugs or feature requests via [Issues](https://github.com/mistyura/PageFolio/issues).

---

## 開発者向け / For Developers

### Python から実行 / Run from Python

```bash
pip install pymupdf pillow
python pagefolio.py
```

Python 3.8 以上が必要です / Requires Python 3.8+

### EXE ビルド / Build EXE

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=pagefolio.ico --name=PageFolio pagefolio.py
```

`dist/PageFolio.exe` が単体実行可能ファイルとして生成されます。

### 開発ツール / Development Tools

| ツール | 用途 |
|--------|------|
| [Ruff](https://docs.astral.sh/ruff/) | リント・フォーマット |
| [pytest](https://docs.pytest.org/) | テスト |
| [PyInstaller](https://pyinstaller.org/) | EXE ビルド |

```bash
ruff check . && ruff format .   # リント・フォーマット
pytest                           # テスト実行
```

テストは GUI (Tkinter) を起動せずにヘッドレスで実行可能です。
All tests run headless without launching the Tkinter GUI.

### AI 協調開発 / AI-assisted Development

機能追加・バグ修正・UI改善のほぼすべてを Claude Code との対話で実装しています。
詳細は以下を参照してください。

- **[CLAUDE.md](CLAUDE.md)** — Claude に渡す構造化された開発指示書（モジュール構成・コーディング規約）
- **[開発履歴.md](開発履歴.md)** — 各バージョンの変更ログ

---

## ライセンス / License

MIT License — see [LICENSE](LICENSE)
