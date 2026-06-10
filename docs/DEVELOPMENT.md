<!-- generated-by: gsd-doc-writer -->
# 開発ガイド

PageFolio の開発環境セットアップ、ビルドコマンド、コードスタイル、ブランチ運用、PR プロセスについて説明します。

## ローカル開発セットアップ

### 前提条件

- Python 3.8 以上（Windows 11 推奨）
- pip（標準付属）
- Git

### 手順

```bash
# 1. リポジトリをクローン
git clone https://github.com/mistyura/PageFolio.git
cd PageFolio

# 2. 仮想環境を作成・有効化
python -m venv venv
venv\Scripts\activate

# 3. 依存パッケージをインストール
pip install -r requirements.txt

# 4. 動作確認（アプリを起動）
python pagefolio.py
```

`python -m pagefolio` でも起動できます。

### 設定ファイルについて

初回起動時に `pagefolio_settings.json` がプロジェクトルートに自動生成されます。このファイルはユーザー設定（テーマ、フォントサイズ、ウィンドウ位置等）を保持します。API キーはセキュリティ上の理由からこのファイルには保存されません（`_SENSITIVE_KEYS` ガードにより除外）。

---

## ビルドコマンド

| コマンド | 説明 |
|---------|------|
| `python pagefolio.py` | アプリを起動（開発時） |
| `python -m pagefolio` | モジュールとして起動 |
| `pytest` | テストスイートを実行 |
| `pytest --cov=pagefolio` | カバレッジ付きでテストを実行 |
| `ruff check .` | リントチェック |
| `ruff format .` | コードフォーマット |
| `ruff check . && ruff format .` | リント + フォーマットを一括実行 |
| `pyinstaller PageFolio.spec` | Windows 向け実行ファイルをビルド（onedir 形式） |

### PyInstaller ビルドについて

`PageFolio.spec` を使用した onedir 形式のビルドを行います。生成物は `dist/PageFolio/` ディレクトリに配置されます。ビルド前に `venv` が有効化されていることを確認してください。

---

## コードスタイル

### リント・フォーマットツール

**Ruff** を使用します（バージョン `0.15.7`、設定は `pyproject.toml`）。

```toml
# pyproject.toml より
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "S", "B"]
fixable = ["ALL"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101"]  # テストファイルでは assert を許可
```

- 行長制限: **88 文字**
- 有効ルール: E（エラー）/ F（未使用 import 等）/ W（警告）/ I（import 順序）/ S（セキュリティ）/ B（バグリスク）
- テストファイル（`tests/**/*.py`）では `S101`（assert 使用）を除外

### コーディング規約（必須）

- 裸の `except:` 禁止 — 必ず `except Exception as e:` の形で記述する
- `# type: ignore` の無断使用禁止
- テーマカラーはハードコード禁止 — `C["BG_DARK"]` 等のテーマ辞書を使う
- フォントサイズはハードコード禁止 — `self._font(delta)` ヘルパーを使う

### ファイル編集後のチェック

py ファイルを編集したら必ず以下を確認してください。

```bash
ruff check . && ruff format .
pytest
```

---

## ブランチ運用

`.github/PULL_REQUEST_TEMPLATE.md` は現時点では存在しません。詳細な貢献ガイドラインは [CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。以下は CLAUDE.md に記載された開発フローをもとにした運用方針です。

- メインブランチ: `main`
- コミットメッセージは**日本語**で記述する（例: `ページ回転機能のバグを修正`）
- 機能修正・バグ修正ともに `main` ブランチへのコミットを基本とする（単独開発）
- 1 タスクずつ完了させてから次のタスクへ進む

### コミットメッセージ例

```
fix: トリミング後にプレビューが更新されないバグを修正
feat: PDF パスワード解除機能を追加
refactor: OCR プロバイダの抽象インターフェースを整理
docs: DEVELOPMENT.md を追加
```

---

## PR プロセス

現時点では PR テンプレートは設定されていません。将来チーム開発に移行する場合は `.github/PULL_REQUEST_TEMPLATE.md` を追加することを推奨します。

コード変更を送る際の推奨チェックリスト:

- `ruff check . && ruff format .` でリント・フォーマット確認
- `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
- `pytest` でテスト通過確認
- `開発履歴.md` に変更内容を追記
- バージョン変更時は `pagefolio/constants.py` の `APP_VERSION`・`開発履歴.md`・`README.md` バッジを同期

---

## テスト

テストの詳細は [TESTING.md](TESTING.md) を参照してください（未生成の場合は `tests/` ディレクトリを直接参照）。

テストファイル一覧:

| ファイル | 内容 |
|---------|------|
| `tests/conftest.py` | 共通フィクスチャ |
| `tests/test_imports.py` | パッケージ import / 後方互換テスト |
| `tests/test_utils.py` | ユーティリティ関数テスト |
| `tests/test_pdf_ops.py` | PDF 操作テスト |
| `tests/test_plugins.py` | PluginManager テスト |
| `tests/test_viewer.py` | プレビュー / サムネイル描画テスト |
| `tests/test_settings_keyguard.py` | API キー非保存ガードテスト |
| `tests/test_ocr.py` | OCR ヘルパー / 並列実行テスト |
| `tests/test_ocr_providers.py` | OCR プロバイダ単体テスト |
| `tests/test_provider_ui.py` | プロバイダ UI（ダイアログ連携）テスト |

---

## 関連ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) — システム構成とコンポーネント図
- [CONFIGURATION.md](CONFIGURATION.md) — 設定ファイルと環境変数の詳細
- [../README.md](../README.md) — エンドユーザー向け使用概要
- [../CLAUDE.md](../CLAUDE.md) — AI 向け開発指示書（詳細なコーディング規約含む）
