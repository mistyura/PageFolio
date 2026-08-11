<!-- generated-by: gsd-doc-writer -->
# PageFolio への貢献ガイドライン

PageFolio への貢献を歓迎します。このドキュメントでは、開発環境のセットアップ、コーディング規約、プルリクエストの出し方、Issue の報告方法をまとめています。

---

## 開発環境のセットアップ

前提条件と初回起動までの手順は [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) を、ビルドコマンド・コードスタイル・ブランチ運用の詳細は [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) を参照してください。

最短の手順は以下のとおりです（Python 3.8 以上が必要）。

```bash
git clone https://github.com/mistyura/PageFolio.git
cd PageFolio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python pagefolio.py
```

---

## コーディング規約

PageFolio は [Ruff](https://docs.astral.sh/ruff/)（バージョン `0.15.20`）でリント・フォーマットを統一しています。設定は `pyproject.toml`（行長 88 文字、`E`/`F`/`W`/`I`/`S`/`B` ルールを適用）です。

コードを変更したら必ず以下を実行し、通ることを確認してください。

```bash
ruff check . && ruff format .
```

- CI ワークフロー（`.github/workflows/`）は現時点で構成されていません。リント・テストはローカルで実行し、結果を PR に記載してください。
- 裸の `except:` 句は禁止。必ず `except Exception as e:` の形式を使うこと
- `# type: ignore` は事前承認なしに使用しないこと
- テーマカラーはハードコードせず `C["KEY"]` テーマ辞書経由で参照すること
- フォントサイズはハードコードせず `self._font(delta)` ヘルパーを使うこと
- `pyproject.toml` の編集は禁止

詳細な規約は [CLAUDE.md](CLAUDE.md) も参照してください。

---

## プルリクエストのガイドライン

ブランチ運用・コミット規約の詳細は [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) の「ブランチ運用」「PR プロセス」節を単一の情報源としています。以下はその要約です。

### ブランチ命名

統合ブランチは `main` です。**`main` へ直接コミットせず**、`main` から機能ブランチを作成して作業してください。

- 機能ブランチはバージョン単位で `feature/v<バージョン>`（例: `feature/v1.9.0`、`feature/v1.10.0`）
- マイルストーンに紐づかない単発作業は `feat/<短い説明>`（例: `feat/password-unlock`）でも構いません
- PR は `main` を対象に作成し、タイトル・説明文は日本語で記述してください

### コミットメッセージ

Conventional Commits 準拠の**日本語**で記述してください。形式は `type(scope): 日本語の説明`（`scope` は省略可）で、`type` は `feat` / `fix` / `docs` / `test` / `refactor` / `chore` / `build` を使います。

```
feat(ocr): OCR ダイアログに進捗キャンセルボタンを追加
fix(viewer): ページ回転後にサムネイルが更新されないバグを修正
docs: CONTRIBUTING.md のブランチ命名規則を更新
```

### PR 提出前のチェックリスト

- [ ] `ruff check . && ruff format .` でリント・フォーマットが通ること
- [ ] `pytest` でテストがすべて通ること
- [ ] 新機能・バグ修正に対応するテストを追加または更新したこと
- [ ] `開発履歴.md` に変更内容を追記したこと
- [ ] バージョン変更が必要な場合は `pagefolio/constants.py` の `APP_VERSION`・`開発履歴.md`・`README.md` のバッジを同期したこと

### レビュープロセス

1. `main` から機能ブランチ（例: `feature/v1.10.0`）を切り、変更をコミットする
2. GitHub で `main` を対象に PR を作成し、変更の目的と動作確認方法を日本語で説明する
3. ローカルで `ruff check . && ruff format .` がパスすることを確認する
4. `pytest` の結果を PR にコメントまたはログで共有する
5. レビュワーのフィードバックに対応してから `main` へマージする

---

## Issue の報告

バグ報告・機能提案は [GitHub Issues](https://github.com/mistyura/PageFolio/issues) から行ってください。専用の Issue テンプレートは現時点で用意されていないため、以下の内容を記載してください。

### バグ報告の記載内容

- **再現手順**: バグを再現するための最小手順を箇条書きで記載する
- **期待する動作**: 本来どうなるべきか
- **実際の動作**: 実際に起きていること（エラーメッセージがある場合は原文ママで記載）
- **環境情報**: OS バージョン・Python バージョン・PageFolio バージョン（`pagefolio/constants.py` の `APP_VERSION`）

### 機能提案の記載内容

- **目的**: 何を解決したいか
- **提案する機能**: 具体的な動作の説明
- **代替案**: 検討した別のアプローチがあれば記載する

---

## ライセンス

このリポジトリに貢献することで、あなたの変更が [MIT License](LICENSE) のもとで公開されることに同意したものとみなします。
