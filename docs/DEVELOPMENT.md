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
| `.venv/Scripts/python.exe tools/build_release.py --output-root <出力先>` | Windows 向け配布フォルダーをビルド（onedir・サンプル同梱・照合。詳細は下記「配布ビルド」） |

### 配布ビルド（専用CLI）

配布用の EXE は、専用 CLI の **1 コマンド**で作ります。初回ビルドも再ビルドも同じコマンドで、手動の `pyinstaller` 実行や、サンプルの退避・復元は不要です。

```bash
.venv/Scripts/python.exe tools/build_release.py --output-root <出力先フォルダー>
```

| オプション | 意味 |
|-----------|------|
| `--output-root` | 出力先フォルダー（既定は `dist`）。この直下に `PageFolio-<APP_VERSION>` が作られる |

- 版番号は `pagefolio/constants.py` の `APP_VERSION` から導きます。CLI・文書に別の版定数を持たないでください（フォルダー名は `PageFolio-<APP_VERSION>`）。
- 実行順は、preflight（出力先の安全確認）→ EXE ビルド（所有 run 内の私有領域）→ サンプルとガイド（`はじめに.md`・`docs/CONFIGURATION.md`）の同梱 → SHA-256 照合 → 公開、です。サンプルの正本は `distribution/samples/`（出力先の外）にあり、`dist` 配下を原本にしません。
- 画面には短い成否と出力先だけを表示します。詳細は同梱の `release-report.json`（版・同梱ファイル・SHA-256 照合結果）と、出力先の `.release-work/<run-id>/`（`report.json`・`build.log`）に残ります。
- 成功後も生成した EXE は自動起動しない仕様です。配布元を直接起動せず、完全な複製を別の場所へ作り、その複製上で手動起動して実機受入を行ってください。ビルド照合の成功は実機受入や出荷承認ではなく、生成物は `release_allowed=false` のままです。

#### 出力先に利用者ファイルがある場合

preflight が、削除・置換・ビルド開始より前に停止します。`pagefolio_settings.json`・`ocr_custom_prompt.md`・`ocr_summary_prompt.md`（大文字小文字を区別しない同名のフォルダー・リンクを含む）、未知のファイル、リンク、前回の検証済み一覧と一致しない配布がある場合は、ファイルの存在を示して別の空フォルダーを指定するよう案内します。出力先を直接編集せず、別の空フォルダーでビルドしてください。

#### 再ビルド

前回の検証済み一覧と完全に一致する管理済み配布だけが再ビルド対象です。旧い成果物は削除せず `.release-history/<run-id>/` へ保持され、公開や復帰に失敗しても旧配布は残ります。利用者の設定や実利用プロンプトは、配布先へ置かない前提です（置いてあれば上記のとおり停止します）。

#### 失敗した場合

失敗した成果物は `.release-work/<run-id>/` に `INCOMPLETE` の印・`build.log`・`report.json` とともに残ります。配布用の成功物とは区別され、未検証の生成物を成功扱いしません。原因を確認してから別の run を実行してください。

#### 古い lock の回復

同じ最終先に `.PageFolio-<APP_VERSION>.lock` が残っていると、CLI は所有者を確認できるまで奪いません。回復は、lock に記録された PID と生成時刻の所有者が終了済みであると確認できた場合だけです。その場合に限り、lock の内容と確認結果を別保存してから、該当 lock を手動で解除します。所有者を確認できない場合は解除しないでください。

#### 履歴と作業領域の容量

`.release-history/` と `.release-work/` は自動では削除されません。使用容量と run一覧を確認し、必要な証拠（`report.json`・`build.log`・`release-report.json`）と旧成功先を別保存して SHA-256 を照合した上で、不要と明示的に選んだ自分の run だけを手動で回収します。実行中・失敗調査中の run と旧dist（追跡済みの `dist/PageFolio`）は保持します。

#### Git の扱い

- 版付きの生成物（`PageFolio-<APP_VERSION>` や `.release-*`）は、既存の `dist/*` の ignore のままローカルの release 候補として保持します。巨大な成果物を stage せず、Release の公開もこの手順には含みません。
- 旧追跡の `dist/PageFolio` は保持します（削除・書き換えは行いません）。stage するのは正本・ガイド・コード・小さい証拠ファイルだけで、全ファイルの一括 add は行わず、個別に指定します。

#### 利用者向けの更新

更新手順（別フォルダーへ展開し、旧フォルダーを残して設定・実利用プロンプトだけをコピー、同名があれば止めて選ぶ）は同梱の `はじめに.md` と [README.md](../README.md) にあります。plugins は自動では移行しない対象です。旧フォルダーを保持したまま、[PLUGINS.md](PLUGINS.md) の導入手順で入れ直します。

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
