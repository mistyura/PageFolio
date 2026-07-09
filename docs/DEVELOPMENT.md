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

初回起動時に `pagefolio_settings.json` がプロジェクトルートに自動生成されます。このファイルはユーザー設定（テーマ、フォントサイズ、ウィンドウ位置等）を保持します。API キーはセキュリティ上の理由からこのファイルには保存されません（`_SENSITIVE_KEYS` ガードにより除外）。詳細は [CONFIGURATION.md](CONFIGURATION.md) を参照してください。

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
| `pyinstaller --onedir --noconsole --icon=pagefolio.ico --name=PageFolio pagefolio.py` | Windows 向け実行ファイルをビルド（onedir 形式） |

### PyInstaller ビルドについて

`PageFolio.spec` は `.gitignore` 対象（`*.spec`）のためリポジトリには基本存在しません。ビルドは以下のコマンドをそのまま実行してください（実行すると `PageFolio.spec` が自動生成されます）。

```bash
pyinstaller --onedir --noconsole --icon=pagefolio.ico --name=PageFolio pagefolio.py
```

| オプション | 意味 |
|-----------|------|
| `--onedir` | ディレクトリ配布形式（`dist/PageFolio/` に exe + 依存ファイル一式を出力） |
| `--noconsole` | 起動時にコンソールウィンドウを表示しない（GUI アプリ用） |
| `--icon=pagefolio.ico` | アプリアイコンを指定 |
| `--name=PageFolio` | 出力名（`dist/PageFolio/PageFolio.exe`） |

- 生成物は `dist/PageFolio/` ディレクトリに配置されます。`dist/PageFolio/` はリビルドのたびにコミットして追跡する運用です。
- 2 回目以降は自動生成された `PageFolio.spec` を使って `pyinstaller PageFolio.spec` でも同じ構成でリビルドできます（spec を手元で編集した場合はこちら）。
- ビルド前に `venv` が有効化されていることを確認してください。

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
- `pyproject.toml` の編集は禁止

### ファイル編集後のチェック

py ファイルを編集したら必ず以下を確認してください。

```bash
ruff check . && ruff format .
pytest
```

---

## ブランチ運用

このリポジトリに `.github/PULL_REQUEST_TEMPLATE.md` および CI ワークフロー（`.github/workflows/`）は現時点で存在しません。詳細な貢献ガイドラインは [../CONTRIBUTING.md](../CONTRIBUTING.md) を参照してください。以下はそのブランチ命名規則です。

- メインブランチ: `main`
- バグ修正: `fix/短い説明`（例: `fix/thumbnail-dnd-drop`）
- 機能追加: `feat/短い説明`（例: `feat/password-unlock`）
- ドキュメント: `docs/短い説明`（例: `docs/update-architecture`）
- リファクタリング: `refactor/短い説明`
- コミットメッセージは**日本語**で記述する（例: `ページ回転機能のバグを修正`）
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

CI ワークフローは未構成のため、PR 提出前にローカルで以下を確認してください。

- [ ] `ruff check . && ruff format .` でリント・フォーマットが通ること
- [ ] `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
- [ ] `pytest` でテストがすべて通ること
- [ ] 新機能・バグ修正に対応するテストを追加または更新したこと
- [ ] `開発履歴.md` に変更内容を追記したこと
- [ ] バージョン変更が必要な場合は `pagefolio/constants.py` の `APP_VERSION`・`開発履歴.md`・`README.md` のバッジを同期したこと

### レビュープロセス

1. `main` からブランチを切り、変更をコミットする
2. GitHub で PR を作成し、変更の目的と動作確認方法を説明する
3. ローカルで `ruff check . && ruff format .` がパスすることを確認する
4. `pytest` の結果をコメントまたはログで共有する
5. レビュワーのフィードバックに対応してから `main` へマージする

---

## テスト

テストの詳細は [TESTING.md](TESTING.md) を参照してください。

テストファイル一覧（`tests/`）:

| ファイル | 内容 |
|---------|------|
| `conftest.py` | テスト用共通フィクスチャ |
| `test_imports.py` | パッケージ import / 後方互換テスト |
| `test_utils.py` | ユーティリティ関数テスト |
| `test_pdf_ops.py` | PDF 操作テスト |
| `test_plugins.py` | PluginManager テスト |
| `test_viewer.py` | プレビュー / サムネイル描画テスト |
| `test_settings_keyguard.py` | API キー非保存ガードテスト |
| `test_ocr.py` | OCR ヘルパー / 並列実行テスト |
| `test_ocr_providers.py` | OCR プロバイダ単体テスト |
| `test_provider_ui.py` | プロバイダ UI（ダイアログ連携）/ resolve_ocr_prompt テスト |
| `test_pagination.py` | ページネーション純ロジック（窓計算 / local↔global / 境界値）テスト |
| `test_md_render.py` | parse_markdown 純関数（行種別 / インライン span）テスト |
| `test_export_images.py` | ページ→画像変換（範囲パース / スケール計算 / 出力）テスト |
| `test_save_overwrite.py` | 縮小して保存（上書き）ヘルパーのテスト |
| `test_password.py` | PDF パスワード付与/解除・暗号化保存ヘルパーのテスト |
| `test_print.py` | 印刷一時ファイル生成 / OS 分岐のテスト |
| `test_undo_stress.py` | 120 ページ PDF の Undo/Redo 連続ストレス（メモリ・Blob 不変条件・eviction） |
| `test_lang_parity.py` | ja/en LANG キー一致 / プレースホルダ整合の回帰テスト |
| `test_source_keyguard.py` | pagefolio/ ソースの実 API キーパターン不在スキャン |

---

## 関連ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) — システム構成とコンポーネント図
- [CONFIGURATION.md](CONFIGURATION.md) — 設定ファイルと環境変数の詳細
- [TESTING.md](TESTING.md) — テストフレームワークと実行方法の詳細
- [../README.md](../README.md) — エンドユーザー向け使用概要
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — 貢献ガイドライン
- [../CLAUDE.md](../CLAUDE.md) — AI 向け開発指示書（詳細なコーディング規約含む）
</content>
</invoke>
