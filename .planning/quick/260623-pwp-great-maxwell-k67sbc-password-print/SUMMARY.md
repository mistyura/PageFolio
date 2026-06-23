---
quick_id: 260623-pwp
slug: great-maxwell-k67sbc-password-print
date: 2026-06-23
status: complete
---

# Summary: PDF パスワード対応（付与/解除）・印刷機能の追加（v1.6.1）

ブランチ: `claude/great-maxwell-k67sbc`
品質確認: `ruff check` クリーン / `pytest` 611 件パス
（※実行環境に tkinter 3.11 が無く、`python3.12` で pytest を実行）

「今後の追加予定機能」だった 2 機能を v1.6.1 として実装した。

## 実施内容

### 1. PDF パスワード対応（付与/解除）

- **暗号化 PDF を開く**: `_open_path_as_pdf` で `doc.needs_pass` を検出すると
  `_authenticate_doc`（`simpledialog`）でパスワード入力を求め、`doc.authenticate()` で
  認証してから開く。誤入力は再入力を促し、キャンセルは `PDFPasswordError` で安全に中断。
  単一/結合/挿入のいずれの経路でも認証が働く。現在開いているファイルは認証成功まで
  閉じない（取り違え防止）。
- **付与**: `SetPasswordDialog`（新規 `pagefolio/dialogs/password.py`）でパスワード＋確認
  ＋表示トグルを受け取り、AES-256（`fitz.PDF_ENCRYPT_AES_256`・owner/user 同一）で別名保存。
  元ファイルへ上書き指定時はハンドル解放→置換後に同パスワードで再認証して継続利用可。
- **解除**: 元々保護されていた PDF（`pdf_has_password`）に限り、暗号化なし
  （`fitz.PDF_ENCRYPT_NONE`）で別名保存。未保護ファイルには情報表示のみ。
- 純ヘルパー `save_with_password` / `save_without_password`（`file_ops.py`）で Tk 非依存化。

### 2. 印刷機能（Ctrl+P）

- `PrintOpsMixin`（新規 `pagefolio/print_ops.py`）。現在の `fitz.Document` を一時 PDF へ
  書き出し（回転/トリミング/挿入などの編集結果を反映）、OS の既定 PDF ハンドラの印刷動詞へ
  渡す（Windows: `os.startfile(path, "print")`）。追加 pip 依存ゼロ。
- 純ヘルパー `write_print_tempfile` でテスト可能化。Windows 以外は情報通知に留める。
- `Ctrl+P` バインド・右パネル「🖨 印刷」セクションを新設（閲覧モードでも使用可）。

### 3. 付随変更

- `app.py`: `PrintOpsMixin` 統合（7 Mixin 構成）・`pdf_has_password` 初期化・`Ctrl+P`。
- `ui_builder.py`: 「🔒 パスワード」「🖨 印刷」セクション追加（needs_doc・閲覧モード可）。
- `lang.py`: パスワード/印刷の ja/en 文言を同一キーで追加（lang parity 維持）。
- ドキュメント: CLAUDE.md（予定機能を完了化・モジュール表/制限事項更新）・開発履歴.md・README.md。

## 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `pagefolio/dialogs/password.py` | （新規）`SetPasswordDialog` |
| `pagefolio/print_ops.py` | （新規）`PrintOpsMixin` / `write_print_tempfile` |
| `pagefolio/file_ops.py` | 認証・暗号化保存ヘルパー・`_set_password`/`_remove_password`・`PDFPasswordError` |
| `pagefolio/app.py` | `PrintOpsMixin` 統合・`pdf_has_password`・`Ctrl+P` |
| `pagefolio/ui_builder.py` | パスワード/印刷セクション |
| `pagefolio/dialogs/__init__.py` | `SetPasswordDialog` 再エクスポート |
| `pagefolio/lang.py` | パスワード/印刷 文言（ja/en） |
| `tests/test_password.py` / `tests/test_print.py` | （新規）テスト |
| CLAUDE.md / 開発履歴.md / README.md | ドキュメント更新 |

## テスト

- 新規: `tests/test_password.py`（11 件）・`tests/test_print.py`（5 件）。
- 合計 611 件パス（v1.6.1 時点 595 → +16）。

## 注意点・潜在リスク

- **印刷は Windows 限定**: `os.startfile` の print 動詞を使用。OS の既定 PDF アプリの
  挙動に依存し、印刷ダイアログ表示有無はアプリ依存。Windows 以外は情報通知のみ。
- **印刷一時ファイル**: 印刷ジョブは非同期のため一時 PDF は即時削除しない（OS の一時
  ディレクトリに残置）。長期運用での蓄積が気になる場合はクリーンアップ方針の検討余地。
- **認証ダイアログの実機目視は未実施**（Tk・GUI のため自動テスト外）。認証ロジック・
  暗号化保存・印刷一時ファイル生成はコード/単体テストで検証済み。
- パスワード設定で「元ファイルへ上書き」を選ぶと一度ハンドルを閉じて再認証する経路を通る。
  別名保存（既定の `_protected` サフィックス）を推奨。

## 実行推奨コマンド

```
ruff check . && pytest
```
