<!-- generated-by: gsd-doc-writer -->
# PageFolio への貢献ガイドライン

PageFolio への貢献を歓迎します。このドキュメントでは、バグ報告・機能提案・コード貢献の方法を説明します。

---

## 開発環境のセットアップ

セットアップ手順とはじめて実行するための手順については [README.md](README.md) を参照してください。
ローカル開発環境の詳細については [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照してください。

### 簡易セットアップ手順

```bash
git clone https://github.com/mistyura/PageFolio.git
cd PageFolio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python pagefolio.py
```

Python 3.8 以上が必要です。

---

## コーディング規約

PageFolio は [Ruff](https://docs.astral.sh/ruff/) でリント・フォーマットを統一しています。

- **ライン長**: 88 文字
- **適用ルール**: `E`, `F`, `W`, `I`, `S`, `B`
- **設定ファイル**: `pyproject.toml`

コードを変更したら必ず以下を実行してください。

```bash
ruff check . && ruff format .
```

### 遵守事項

- 裸の `except:` 句は禁止。必ず `except Exception as e:` の形式を使うこと
- `# type: ignore` は事前承認なしに使用しないこと
- テーマカラーはハードコードせず `C["KEY"]` テーマ辞書経由で参照すること
- フォントサイズはハードコードせず `self._font(delta)` ヘルパーを使うこと
- CI ワークフローは未構成です。PR 提出前にローカルで `ruff check . && ruff format .` と `pytest` を実行して確認してください

---

## プルリクエストのガイドライン

### ブランチ命名

- バグ修正: `fix/短い説明`（例: `fix/thumbnail-dnd-drop`）
- 機能追加: `feat/短い説明`（例: `feat/password-unlock`）
- ドキュメント: `docs/短い説明`（例: `docs/update-architecture`）
- リファクタリング: `refactor/短い説明`

メインブランチは `main` です。`main` から派生してブランチを作成してください。

### PR 提出前のチェックリスト

- [ ] `ruff check . && ruff format .` でリント・フォーマットが通ること
- [ ] `pytest` でテストがすべて通ること
- [ ] 新機能・バグ修正に対応するテストを追加または更新したこと
- [ ] `開発履歴.md` に変更内容を追記したこと
- [ ] バージョン変更が必要な場合は `pagefolio/constants.py` の `APP_VERSION`・`開発履歴.md`・`README.md` のバッジを同期したこと

### コミットメッセージ

日本語でわかりやすく記述してください。

```
ページ回転後にサムネイルが更新されないバグを修正
OCR ダイアログに進捗キャンセルボタンを追加
```

### レビュープロセス

1. `main` からブランチを切り、変更をコミットする
2. GitHub で PR を作成し、変更の目的と動作確認方法を説明する
3. ローカルで `ruff check . && ruff format .` がパスすることを確認する
4. `pytest` の結果をコメントまたはログで共有する
5. レビュワーのフィードバックに対応してから `main` へマージする

---

## Issue の報告

バグ報告・機能提案は [GitHub Issues](https://github.com/mistyura/PageFolio/issues) から行ってください。

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
