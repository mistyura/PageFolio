<!-- generated-by: gsd-doc-writer -->
# はじめに — PageFolio セットアップガイド

このガイドでは PageFolio を開発環境で動かすまでの手順を説明します。
エンドユーザー向けの利用方法は [README.md](../README.md) を参照してください。

---

## 前提条件

開発・実行に必要なツールとバージョンを確認してください。

| ツール | 必要バージョン | 確認コマンド |
|--------|--------------|-------------|
| Python | `>= 3.8` | `python --version` |
| pip | 最新推奨 | `pip --version` |
| Git | 任意 | `git --version` |

> **対応 OS:** Windows 11  
> Python 3.8 以降が必要です。[python.org](https://www.python.org/downloads/) からインストールしてください。

---

## インストール手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/mistyura/PageFolio.git
cd PageFolio
```

### 2. 仮想環境を作成・有効化

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> PowerShell で実行ポリシーエラーが出る場合は以下を実行してください:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

インストールされる主なパッケージ:

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| PyMuPDF | 1.27.2.2 | PDF 読み書き・レンダリング |
| Pillow | 12.2.0 | 画像変換・プレビュー表示 |
| tkinterdnd2 | 0.4.3 | ファイルのドラッグ＆ドロップ対応 |
| pytest | 9.0.2 | テストランナー |
| ruff | 0.15.7 | リント・フォーマット |

---

## 初回起動

インストール完了後、以下のいずれかのコマンドでアプリを起動できます。

```bash
# エントリーポイントスクリプトから起動
python pagefolio.py

# モジュールとして起動
python -m pagefolio
```

起動するとダークテーマの PDF 編集 GUI が表示されます。

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

> `tkinterdnd2` がインストールされていない場合でも、ファイルの D&D 機能が無効になるだけでアプリ自体は起動します。

---

### 問題 2: `PyMuPDF` のインポートエラー

**症状:** `ImportError: No module named 'fitz'` が表示される。

**対処:**
```bash
pip install pymupdf==1.27.2.2
```

---

### 問題 3: PowerShell のスクリプト実行ポリシーエラー

**症状:** `.\venv\Scripts\Activate.ps1` 実行時に「スクリプトの実行が無効になっているため〜」というエラー。

**対処:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 問題 4: Python バージョンが古い

**症状:** `SyntaxError` や `TypeError` が頻発する。

**対処:** `python --version` で Python のバージョンを確認し、3.8 以上でなければ [python.org](https://www.python.org/downloads/) から最新版をインストールしてください。

---

## OCR プロバイダのセットアップ（任意）

OCR 機能を使用する場合のみ追加設定が必要です。

### Tesseract OCR（ローカル・無料）

1. [UB Mannheim ビルド](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラをダウンロード
2. インストール時に `jpn`（日本語）言語パックを追加
3. PATH に Tesseract の実行ファイルパスを追加（例: `C:\Program Files\Tesseract-OCR`）

```powershell
# インストール確認
tesseract --version
tesseract --list-langs
```

### クラウド OCR（Claude / Gemini）

API キーを環境変数に設定してください（設定ファイルには保存されません）。

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # Claude
$env:GEMINI_API_KEY    = "AIza..."      # Gemini
```

詳細は [docs/CONFIGURATION.md](CONFIGURATION.md) の「機密情報の取り扱い」セクションを参照してください。

---

## 次のステップ

セットアップが完了したら、以下のドキュメントも参照してください。

- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** — コンポーネント構成とデータフローの解説
- **[docs/CONFIGURATION.md](CONFIGURATION.md)** — 設定ファイルと環境変数のリファレンス
- **[CLAUDE.md](../CLAUDE.md)** — 開発規約・コーディング規則（コントリビュータ向け）
- **[開発履歴.md](../開発履歴.md)** — バージョン別の変更ログ
