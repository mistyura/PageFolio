# PageFolio

**PDF ページ整理ツール — Python + Tkinter 製 GUI アプリ**

![Version](https://img.shields.io/badge/version-v1.2.3-blue)
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

[Releases](https://github.com/mistyura/PageFolio/releases) から最新の `PageFolio-vX.X.X-onedir.zip` をダウンロードし、任意のフォルダに展開して `PageFolio.exe` を実行してください。
Python のインストールは不要です。

Download the latest `PageFolio-vX.X.X-onedir.zip` from [Releases](https://github.com/mistyura/PageFolio/releases), extract it to any folder, and run `PageFolio.exe`.
No Python installation required.

> v1.1.2-4 以降は `--onedir` 形式で配布しています。zip 内の `PageFolio.exe` と `_internal/` フォルダは同じディレクトリに置いたままご利用ください。
>
> Starting with v1.1.2-4, releases are distributed in `--onedir` format. Keep `PageFolio.exe` and the `_internal/` folder together in the same directory.

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

## 🔍 OCR テキスト抽出 / OCR Text Extraction

ローカル動作の [LM Studio](https://lmstudio.ai/)（OpenAI 互換 API）を経由して、PDF ページから文字を抽出できます（v1.2.0〜）。

PageFolio extracts text from PDF pages via local [LM Studio](https://lmstudio.ai/) (OpenAI-compatible API) since v1.2.0.

### 推奨 Vision モデル / Recommended Vision Models

小型モデル（4B 未満）は表組み・数値・固有名詞でハルシネーション（架空の文字列の生成）が起きやすいため、**7B 以上のモデルを推奨**します。

Small models (<4B) tend to hallucinate especially on tables, numbers, and proper nouns. **7B+ models are recommended.**

| モデル / Model | サイズ | 備考 |
|----------------|--------|------|
| **Qwen2-VL-7B-Instruct** | 7B | 日本語 OCR・表組み認識ともに高精度。第一推奨 |
| **MiniCPM-V 2.6** | 8B | OCR タスクに最適化。多言語対応 |
| **InternVL2-8B** | 8B | 詳細な画像理解・OCR 両立 |
| Gemma 3 / 4 (4B) | 4B | 軽量だが OCR 用途には精度不足 |

### ハルシネーション対策 / Reducing Hallucinations

OCR ダイアログ右上の「詳細設定」で次のパラメータを調整できます:

- **解像度** (1.0〜4.0): 高いほど認識精度向上（推奨 3.0〜4.0）
- **最大トークン** (-1: 無制限): 出力途中切れの解消
- **温度** (0.0〜2.0): **0.0〜0.2 推奨**。ランダム性を抑え架空文字を抑制
- **タイムアウト** (10〜600 秒): 高解像度時は 240+ 秒推奨

LM Studio 側の **Context Length** も明細書・長い文書の場合は 8192 以上に増やしてください。

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
pyinstaller --onedir --noconsole --icon=pagefolio.ico --name=PageFolio pagefolio.py
```

`dist/PageFolio/` フォルダに `PageFolio.exe` と `_internal/` 一式が生成されます。配布時は `dist/PageFolio/` をフォルダごと zip 化してください。

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
