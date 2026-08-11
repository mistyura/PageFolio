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

`python -m pagefolio` でも起動できます（`pagefolio/__main__.py` がエントリーポイント）。

### 依存パッケージ（`requirements.txt`）

| パッケージ | バージョン | 区分 |
|-----------|-----------|------|
| `PyMuPDF` | `1.28.0` | 実行依存（PDF 操作、`fitz` として import） |
| `Pillow` | `12.3.0` | 実行依存（画像処理） |
| `tkinterdnd2` | `0.6.2` | 実行依存（D&D 対応） |
| `pyinstaller` | `6.21.0` | 実行依存（配布ビルド用。開発環境にも同梱） |
| `pytest` | `9.1.1` | 開発依存（テスト） |
| `pytest-cov` | `7.1.0` | 開発依存（カバレッジ） |
| `ruff` | `0.15.20` | 開発依存（リント・フォーマット） |

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

`PageFolio.spec` は `.gitignore` 対象（`*.spec`）のためリポジトリには基本存在しません。初回ビルドは以下のコマンドをそのまま実行してください（実行すると `PageFolio.spec` が自動生成されます）。

```bash
pyinstaller --onedir --noconsole --icon=pagefolio.ico --name=PageFolio pagefolio.py
```

| オプション | 意味 |
|-----------|------|
| `--onedir` | ディレクトリ配布形式（`dist/PageFolio/` に exe + 依存ファイル一式を出力） |
| `--noconsole` | 起動時にコンソールウィンドウを表示しない（GUI アプリ用） |
| `--icon=pagefolio.ico` | アプリアイコンを指定 |
| `--name=PageFolio` | 出力名（`dist/PageFolio/PageFolio.exe`） |

- 生成物は `dist/PageFolio/` ディレクトリに配置されます。`dist/PageFolio/` はリビルドのたびにコミットして追跡する運用です（`.gitignore` は `dist/*` を除外しつつ `!dist/PageFolio` / `!dist/PageFolio/**` で例外的に再許可している）。
- 2 回目以降は自動生成された `PageFolio.spec` を使って `pyinstaller PageFolio.spec` でも同じ構成でリビルドできます（spec を手元で編集した場合はこちら）。
- 確認プロンプトをスキップして再実行する場合は `--noconfirm` を付与します（`pyinstaller PageFolio.spec --noconfirm --clean` など）。この場合は下記「サンプルプロンプトファイルの退避」に必ず対応してください。
- ビルド前に `venv` が有効化されていることを確認してください。

#### サンプルプロンプトファイルの退避（重要）

`dist/PageFolio/ocr_custom_prompt_sample.md` と `dist/PageFolio/ocr_summary_prompt_sample.md` は **`dist/PageFolio/` 直下にのみ Git 管理されており、ソースツリー側に原本が存在しません**。PyInstaller を `--noconfirm` 付きで実行すると `dist/PageFolio/` が丸ごと再作成されるため、この 2 ファイルは毎回消失します。リビルド時は以下の手順で退避 → 復元してください。

```bash
# 1. ビルド前に退避
cp dist/PageFolio/ocr_custom_prompt_sample.md  /tmp/ocr_custom_prompt_sample.md
cp dist/PageFolio/ocr_summary_prompt_sample.md /tmp/ocr_summary_prompt_sample.md

# 2. ビルド実行（--noconfirm で dist/PageFolio が再生成される）
pyinstaller PageFolio.spec --noconfirm --clean

# 3. ビルド後に復元
cp /tmp/ocr_custom_prompt_sample.md  dist/PageFolio/ocr_custom_prompt_sample.md
cp /tmp/ocr_summary_prompt_sample.md dist/PageFolio/ocr_summary_prompt_sample.md
```

- 復元後は `git diff` で退避前の内容と完全一致することを確認してからコミットしてください（サンプルの内容が意図せず変わっていないかのチェックも兼ねます）。
- これは既知の恒久課題です（`.planning/codebase/CONCERNS.md` 参照）。根本解決には、サンプルをソースツリー（例: `pagefolio/samples/`）へ移設し、ビルド後コピーまたは PyInstaller の `--add-data` で `dist/PageFolio/` へ配置する仕組みが必要です。

---

## コードスタイル

### リント・フォーマットツール

**Ruff** を使用します（バージョン `0.15.20`、設定は `pyproject.toml`）。

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
- フォントサイズはハードコード禁止 — `self._font(delta)` ヘルパーを使う（`tests/test_font_hardcode_guard.py` でソーススキャンにより検出）
- `pyproject.toml` の編集は禁止

### ファイル編集後のチェック

py ファイルを編集したら必ず以下を確認してください。

```bash
ruff check . && ruff format .
pytest
```

---

## ブランチ運用

姉妹プロジェクト（loto / numbers）と同一の運用規約を採用します。

- **デフォルト（統合）ブランチは `main`**。開発は機能ブランチ上で行い、**`main` へ直接コミットしない**
- **機能ブランチはバージョン単位で `feature/v<バージョン>` と命名する**（例: `feature/v1.9.0`、`feature/v1.10.0`）。マイルストーンに紐づかない単発作業は `feat/<短い説明>` を使ってもよい（例: `feat/password-unlock`）
- **PR は `main` を対象に作成する**。PR タイトル・説明文も**日本語**で記述する
- **コミットメッセージは Conventional Commits 準拠の日本語**。形式は `type(scope): 日本語の説明`（`scope` は省略可）。`type` は `feat` / `fix` / `docs` / `test` / `refactor` / `chore` / `build` を使う
- 1 タスクずつ完了させてから次のタスクへ進む

### コミットメッセージ例

```
feat(ocr): OpenAI プロバイダを追加
fix(page_ops): トリミング後にプレビューが更新されないバグを修正
refactor(ocr_providers): 抽象インターフェースを整理
docs(quick-260812-9ev): ブランチ運用ルールを loto/numbers と統一
build: v1.9.0 の PyInstaller ビルドを反映
```

明文化された命名規則はこれ以上ありません。既存の git 履歴のパターンに合わせてください。

<!-- VERIFY: PageFolio には CI ワークフロー（.github/workflows/）・branch protection 設定・PR テンプレート・Issue テンプレートがいずれも存在しない。numbers の .github/branch-protection.yaml に相当する宣言的設定は、必須ステータスチェック（CI）が前提のため PageFolio では未整備。CI 構築後に追加を検討する -->

---

## PR プロセス

loto / numbers は CI（GitHub Actions）の green をマージ条件にしていますが、**PageFolio には CI ワークフローが存在しない**ため、その項目はローカルのリリースゲートに読み替えて運用します。

1. `main` から機能ブランチを作成する（例: `feature/v1.10.0`）
2. 変更を実装し、**ローカルで `ruff check . && ruff format .` と `pytest` を通す**
3. コミットメッセージは**日本語**で、Conventional Commits 形式を用いる
4. `main` を対象に PR を作成する。PR タイトル・説明文も**日本語**で記述する
5. `pytest` の結果を PR にコメントまたはログで共有する（CI がないため、ローカル実行結果がレビューの根拠になる）
6. レビュワーのフィードバックに対応してから `main` へマージする

### PR 提出前チェックリスト

- [ ] `ruff check . && ruff format .` でリント・フォーマットが通ること
- [ ] `python -c "import ast; ast.parse(open('pagefolio.py', encoding='utf-8').read())"` で構文確認
- [ ] `pytest` でテストがすべて通ること（合格条件の詳細は [../CLAUDE.md](../CLAUDE.md) の「リリースゲート」節を参照）
- [ ] 新機能・バグ修正に対応するテストを追加または更新したこと
- [ ] `開発履歴.md` に変更内容を追記したこと
- [ ] バージョン変更が必要な場合は `pagefolio/constants.py` の `APP_VERSION`・`開発履歴.md`・`README.md` のバッジを同期したこと

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
| `test_ocr_engine.py` | `OCRRunEngine`（producer/consumer）ユニットテスト |
| `test_ocr_pipeline.py` | `ocr_pipeline`（`PipelineState` 等）のユニットテスト |
| `test_ocr_fallback.py` | OCR フォールバックオーケストレーション（`ocr_fallback` / `OCRDialog`）のユニットテスト |
| `test_ocr_providers.py` | OCR プロバイダ単体テスト |
| `test_ocr_dialog_center.py` | `OCRDialog._center()` の画面高クランプ回帰テスト |
| `test_provider_ui.py` | プロバイダ UI（ダイアログ連携）/ resolve_ocr_prompt テスト |
| `test_prompt_templates.py` | プロンプトテンプレート CRUD（save/get/list/delete/rename/exists）と `load_custom_prompt`/`load_summary_prompt` の3段解決（外部ファイル > アクティブテンプレート > 設定欄）のテスト |
| `test_batch_ocr_state.py` | `batch_ocr_state`（Tk/fitz 非依存の純ロジック層）ユニットテスト |
| `test_batch_ocr_dialog.py` | `BatchOCRDialog` の E2E モックテスト（失敗分離・階層キャンセル） |
| `test_pagination.py` | ページネーション純ロジック（窓計算 / local↔global / 境界値）テスト |
| `test_md_render.py` | `parse_markdown` 純関数（行種別 / インライン span）テスト |
| `test_export_images.py` | ページ→画像変換（範囲パース / スケール計算 / 出力）テスト |
| `test_save_overwrite.py` | 縮小して保存（上書き）ヘルパーのテスト |
| `test_password.py` | PDF パスワード付与/解除・暗号化保存ヘルパーのテスト |
| `test_print.py` | 印刷一時ファイル生成 / OS 分岐のテスト |
| `test_undo_stress.py` | 120 ページ PDF の Undo/Redo 連続ストレス（メモリ・Blob 不変条件・eviction） |
| `test_thumb_cache.py` | `LruCache`（サムネイルキャッシュ）のユニットテスト |
| `test_selection_invariant.py` | `selected_pages` 全ページインデックス不変条件のプロパティ風テスト |
| `test_toast.py` | `ToastManager` の単体テスト |
| `test_shortcuts_dialog.py` | `ShortcutsDialog` のキャプチャ表示残留回帰テスト |
| `test_plugin_dialog_wheel.py` | `PluginDialog` のマウスホイール束縛回帰テスト |
| `test_page_polish.py` | ページ操作磨き込み機能（画像透かし等）+ v1.5.0 回帰テスト |
| `test_v150_regression.py` | v1.5.0 新機能の回帰テスト（D&D 挿入位置・ショートカットマージ・TOC 保持） |
| `test_font_hardcode_guard.py` | フォントサイズ数値ハードコード検出（ソーススキャン） |
| `test_lang_parity.py` | ja/en LANG キー一致 / プレースホルダ整合の回帰テスト |
| `test_source_keyguard.py` | `pagefolio/` ソースの実 API キーパターン不在スキャン |

---

## 関連ドキュメント

- [ARCHITECTURE.md](ARCHITECTURE.md) — システム構成とコンポーネント図
- [CONFIGURATION.md](CONFIGURATION.md) — 設定ファイルと環境変数の詳細
- [TESTING.md](TESTING.md) — テストフレームワークと実行方法の詳細
- [../README.md](../README.md) — エンドユーザー向け使用概要
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — 貢献ガイドライン
- [../CLAUDE.md](../CLAUDE.md) — AI 向け開発指示書（詳細なコーディング規約含む）
