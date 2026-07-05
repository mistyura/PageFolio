<!-- generated-by: gsd-doc-writer -->
# はじめに — PageFolio セットアップガイド

このガイドでは PageFolio を開発環境で動かすまでの手順を説明します。
エンドユーザー向けの利用方法（実行ファイル配布版の使い方など）は [README.md](../README.md) を参照してください。

---

## 前提条件

開発・実行に必要なツールとバージョンを確認してください。

| ツール | 必要バージョン | 確認コマンド |
|--------|--------------|-------------|
| Python | `>= 3.8` | `python --version` |
| pip | 最新推奨 | `pip --version` |
| Git | 任意（ソース取得に使用） | `git --version` |

> **対応 OS:** Windows 11（`os.startfile` を用いた印刷機能など一部機能は Windows 専用）
> Python 3.8 以降が必要です。未インストールの場合は [python.org](https://www.python.org/downloads/) から入手してください。

---

## インストール手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/mistyura/PageFolio.git
cd PageFolio
```

### 2. 仮想環境を作成・有効化（推奨）

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> PowerShell で実行ポリシーエラーが出る場合は以下を実行してください。
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

`requirements.txt` にバージョン固定されている主なパッケージ:

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| PyMuPDF | 1.27.2.2 | PDF 読み書き・レンダリング（`import fitz`） |
| Pillow | 12.2.0 | 画像変換・プレビュー表示 |
| tkinterdnd2 | 0.4.3 | ファイルのドラッグ＆ドロップ対応 |
| pyinstaller | 6.19.0 | Windows 実行ファイルのビルド（配布用、通常実行には不要） |
| pytest | 9.0.2 | テストランナー（開発用） |
| pytest-cov | 7.1.0 | カバレッジ計測（開発用） |
| ruff | 0.15.7 | リント・フォーマット（開発用） |

`tkinter` は Python 標準ライブラリのため別途インストール不要ですが、環境によっては OS 側の Python パッケージ（例: `python3-tk`）が必要な場合があります。

---

## 初回起動

インストール完了後、以下のいずれかのコマンドでアプリを起動できます。

```bash
# エントリーポイントスクリプトから起動
python pagefolio.py

# モジュールとして起動（pagefolio/__main__.py 経由）
python -m pagefolio
```

起動するとダークテーマの PDF ページ整理 GUI が表示されます。ウィンドウに PDF・PNG・JPG・BMP・TIFF ファイルをドラッグ＆ドロップするか、「ファイルを開く」から選択すると編集を開始できます。

初回起動時、設定ファイル `pagefolio_settings.json` はまだ存在しません（設定を変更するかアプリを終了すると自動生成されます）。詳細は [docs/CONFIGURATION.md](CONFIGURATION.md) を参照してください。

---

## よくあるセットアップの問題

### 問題 1: `tkinterdnd2` のインポートエラー

**症状:** 起動時に `ImportError: No module named 'tkinterdnd2'` が表示される。

**原因:** `requirements.txt` のインストールが不完全、または仮想環境が有効化されていない。

**対処:**
```bash
# 仮想環境が有効化されているか確認
.\venv\Scripts\Activate.ps1

# 再インストール
pip install tkinterdnd2==0.4.3
```

> `tkinterdnd2` が読み込めない場合でも、ファイルの D&D 機能が無効になるだけでアプリ自体は起動します。

---

### 問題 2: `PyMuPDF` のインポートエラー

**症状:** `ImportError: No module named 'fitz'` が表示される。

**対処:**
```bash
pip install pymupdf==1.27.2.2
```

---

### 問題 3: PowerShell のスクリプト実行ポリシーエラー

**症状:** `.\venv\Scripts\Activate.ps1` 実行時に「このシステムではスクリプトの実行が無効になっているため〜」というエラー。

**対処:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 問題 4: Python バージョンが古い

**症状:** 起動時に `SyntaxError` や型ヒント関連の `TypeError` が発生する。

**対処:** `python --version` で Python のバージョンを確認し、3.8 未満であれば [python.org](https://www.python.org/downloads/) から最新版をインストールしてください。

---

## OCR プロバイダのセットアップ（任意）

OCR 機能（`🔍 OCR テキスト抽出`）を使う場合のみ、プロバイダに応じた追加設定が必要です。既定は `off`（無効）です。プロバイダは `pagefolio_settings.json` の `ocr_provider` キー、またはアプリ内の「🔍 LLM 設定…」ダイアログから切り替えます。

| プロバイダ | 設定値 | 認証 | セットアップ |
|-----------|--------|------|-------------|
| LM Studio | `lmstudio` | 不要 | ローカルでサーバを起動するのみ（既定 URL: `http://localhost:1234`） |
| Ollama | `ollama` | 不要 | ローカルでサーバを起動するのみ（既定 URL: `http://localhost:11434`） |
| RunPod Serverless | `runpod` | `RUNPOD_API_KEY` | エンドポイント URL を設定し、API キーを環境変数で指定 |
| Claude（Anthropic） | `claude` | `ANTHROPIC_API_KEY` | API キーを環境変数で指定 |
| Gemini（Google AI） | `gemini` | `GEMINI_API_KEY`（未設定時 `GOOGLE_API_KEY`） | API キーを環境変数で指定 |
| Tesseract | `tesseract` | 不要 | 別途インストールが必要（下記参照） |

### Tesseract OCR（ローカル・無料）

1. [UB Mannheim ビルド](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラをダウンロード
2. インストール時に `jpn`（日本語）言語パックを追加
3. PATH に Tesseract の実行ファイルパスを追加（例: `C:\Program Files\Tesseract-OCR`）

```powershell
# インストール確認
tesseract --version
tesseract --list-langs
```

`jpn` 言語パックが検出できない場合、設定保存時に自動的に `eng` にフォールバックします。

### クラウド OCR（Claude / Gemini / RunPod）

API キーは `pagefolio_settings.json` には保存されません。環境変数、またはアプリ内 OCR ダイアログのキー入力欄（セッション中のみ保持）で指定してください。

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # Claude
$env:GEMINI_API_KEY    = "AIza..."      # Gemini（未設定時は GOOGLE_API_KEY にフォールバック）
$env:RUNPOD_API_KEY    = "rpa_..."      # RunPod
```

クラウド OCR（Claude / Gemini / RunPod）はページ画像を base64 で外部 API へ HTTPS 送信します。LM Studio / Ollama / Tesseract はローカル完結で外部通信を行いません。

API キーの解決順序や機密情報の取り扱いの詳細は [docs/CONFIGURATION.md](CONFIGURATION.md) の「機密情報の取り扱い（セキュリティ）」セクションを参照してください。

---

## 動作確認（テスト実行）

セットアップが正しく完了しているかは、テストスイートで確認できます。GUI (Tkinter) を実際に起動せずヘッドレスで実行可能です。

```bash
pytest
```

詳細は [docs/TESTING.md](TESTING.md) を参照してください。

---

## 次のステップ

セットアップが完了したら、以下のドキュメントも参照してください。

- **[docs/DEVELOPMENT.md](DEVELOPMENT.md)** — ビルドコマンド・コードスタイル・ブランチ運用・PR プロセス
- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** — コンポーネント構成とデータフローの解説
- **[docs/TESTING.md](TESTING.md)** — テストフレームワークと実行方法
- **[docs/CONFIGURATION.md](CONFIGURATION.md)** — 設定ファイルと環境変数のリファレンス
- **[CLAUDE.md](../CLAUDE.md)** — 開発規約・コーディング規則（コントリビュータ向け）
- **[開発履歴.md](../開発履歴.md)** — バージョン別の変更ログ
