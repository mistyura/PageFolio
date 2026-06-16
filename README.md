# PageFolio

**PDF ページ整理ツール — Python + Tkinter 製 GUI アプリ**

![Version](https://img.shields.io/badge/version-v1.5.0-blue)
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
| 🖼 画像変換 | ページを画像ファイルに変換（1ページ1ファイル・PNG/JPEG・長辺ピクセル指定）。AI（LLM）にテキストを読み取らせる用途に最適 |
| 🗜 縮小保存 | garbage収集 + 圧縮でファイルサイズを最適化して保存（元ファイルへの上書きにも対応） |
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

v1.4.0 より複数の OCR プロバイダに対応しました。設定ダイアログでプロバイダを選択してください。

PageFolio supports multiple OCR providers since v1.4.0. Select a provider in the settings dialog.

### OCR プロバイダ一覧 / OCR Providers

| プロバイダ | 必要な設定 | 特徴 |
|-----------|-----------|------|
| **LM Studio** | ローカルサーバ起動 | ローカル・無料・GPU 推奨・高精度 |
| **Claude** | `ANTHROPIC_API_KEY` 環境変数 | 高精度・有料（従量課金） |
| **Gemini** | `GEMINI_API_KEY` または `GOOGLE_API_KEY` | 高精度・有料（無料枠あり） |
| **Tesseract** | Tesseract OCR を別途インストール | ローカル・無料・オフライン対応・精度は LLM より劣る |

| Provider | Required Setup | Notes |
|----------|---------------|-------|
| **LM Studio** | Local server running | Local / Free / GPU recommended |
| **Claude** | `ANTHROPIC_API_KEY` env var | High accuracy / Paid |
| **Gemini** | `GEMINI_API_KEY` or `GOOGLE_API_KEY` | High accuracy / Paid (free tier) |
| **Tesseract** | Install Tesseract OCR separately | Local / Free / Offline / Lower accuracy than LLMs |

> **Gemini プロバイダのモデル選択**: 安定性重視なら `gemini-2.5-flash` / `gemini-2.5-pro` を推奨します。
> Gemma 4 系（`gemma-4-26b-a4b-it` / `gemma-4-31b-it`）も動作実績があり、無料枠を活かしやすい選択肢です。
> ただしサーバ側要因で HTTP 500 が頻発する時期があるため、解像度は 1.5 程度に抑え、
> 中断した場合は「⏯ 続きから再実行」で残りページを再開してください。
>
> **Model selection for the Gemini provider**: For stability, `gemini-2.5-flash` / `gemini-2.5-pro` are recommended.
> Gemma 4 models (`gemma-4-26b-a4b-it` / `gemma-4-31b-it`) are also verified to work and make good use of the free tier.
> However, server-side HTTP 500 errors can spike at times — keep the resolution around 1.5 and
> use "⏯ Resume" to continue with the remaining pages if a run is interrupted.

### 環境変数の設定 / Setting Environment Variables

クラウドプロバイダを使用する場合は以下の環境変数を設定してください（設定ダイアログの入力欄でも一時設定可能）。

```
set ANTHROPIC_API_KEY=your_key_here
set GEMINI_API_KEY=your_key_here
```

### Tesseract のインストール / Installing Tesseract

Tesseract プロバイダを使用するには Tesseract OCR を別途インストールし、PATH を通す必要があります。

To use the Tesseract provider, install Tesseract OCR separately and add it to your PATH.

**Windows:**

1. [UB Mannheim ビルド](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラをダウンロード
2. インストール時に日本語認識用の `jpn` 言語パックを追加
3. インストール後、PATH に Tesseract の実行ファイルパスを追加（例: `C:\Program Files\Tesseract-OCR`）

```
# インストール確認 / Verify installation
tesseract --version
tesseract --list-langs
```

### 埋め込みテキストのスキップ / Embedded-Text Skip

テキスト埋め込み済みのページは既定で OCR をスキップし、埋め込みテキストをそのまま抽出します。
スキャナ付属 OCR などで埋め込みテキストの品質が悪い場合は、OCR ダイアログの
「埋め込みテキストを無視して OCR を実行」をオンにすると全ページを Vision OCR で読み直せます
（クラウドプロバイダではスキップされていたページも課金対象になる点に注意）。

Pages that already contain embedded text are skipped by default and their text is extracted as-is.
If the embedded text quality is poor (e.g., scanner-generated OCR layers), enable
"Ignore embedded text and always run OCR" in the OCR dialog to re-read all pages with Vision OCR
(note: with cloud providers, previously skipped pages will also incur charges).

### 推奨 Vision モデル（LM Studio）/ Recommended Vision Models

小型モデル（5B 未満）は表組み・数値・固有名詞でハルシネーション（架空の文字列の生成）が起きやすいため、**7B 以上のモデルを推奨**します。

Small models (<5B) tend to hallucinate especially on tables, numbers, and proper nouns. **7B+ models are recommended.**

動作確認済みモデル（量子化はいずれも 4bit / GGUF）:

| モデル / Model | 配布元 | サイズ | 量子化 | ファイルサイズ | 備考 |
|----------------|--------|--------|--------|----------------|------|
| **MiniCPM-V 4.5** | openbmb | 8.2B | Q4_K_S | 5.49 GB | OCR タスクに最適化・多言語対応。第一推奨 |
| **InternVL3.5 8B** | lmstudio-community | 8B | Q4_K_M | 5.31 GB | 詳細な画像理解・OCR 両立 |
| **Qwen3 VL 8B** | qwen | 8B | Q4_K_M | 5.76 GB | 日本語 OCR・表組み認識に強い |
| **Qwen3.5 9B** | qwen | 9B | Q4_K_M | 6.10 GB | Vision 対応の汎用モデル |
| Gemma 4 E4B / E4B Instruct QAT | google / lmstudio-community | 7.5B | Q4_K_M / Q4_0 | 5.72〜5.89 GB | 軽量・Vision 対応 |
| Gemma 4 E2B / E2B Instruct QAT | google / lmstudio-community | 4.6B | Q4_K_M / Q4_0 | 4.04〜4.11 GB | 最軽量だが OCR 用途には精度不足の可能性 |

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
