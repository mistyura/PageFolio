---
quick_id: 260623-pwp
slug: great-maxwell-k67sbc-password-print
date: 2026-06-23
type: quick
mode: quick
---

# Plan: PDF パスワード対応（付与/解除）・印刷機能の追加（v1.6.1）

## 背景

CLAUDE.md「今後の追加予定機能」に残っていた **PDF パスワード対応** と **印刷機能** を
v1.6.1（既に APP_VERSION = v1.6.1）に追加する。追加 pip 依存を増やさず、PyMuPDF と
OS の既定 PDF ハンドラのみで実現する。

## タスク

### Task 1: パスワード対応
- **files**: `pagefolio/file_ops.py`, `pagefolio/dialogs/password.py`,
  `pagefolio/dialogs/__init__.py`, `pagefolio/ui_builder.py`, `pagefolio/lang.py`
- **action**: 暗号化 PDF の認証（`_authenticate_doc`）、付与（AES-256）/解除
  （ENCRYPT_NONE）の別名保存、`SetPasswordDialog`、純ヘルパー
  `save_with_password`/`save_without_password`、UI セクション・文言追加。
- **verify**: `tests/test_password.py` グリーン・`ruff check`
- **done**: 開く/付与/解除が動作しテスト追加

### Task 2: 印刷機能
- **files**: `pagefolio/print_ops.py`, `pagefolio/app.py`, `pagefolio/ui_builder.py`,
  `pagefolio/lang.py`
- **action**: `PrintOpsMixin`・`write_print_tempfile`、`Ctrl+P` バインド、UI セクション。
  Windows は `os.startfile(path,"print")`、他 OS は情報通知。
- **verify**: `tests/test_print.py` グリーン・`ruff check`
- **done**: 印刷導線とテスト追加

### Task 3: ドキュメント
- **files**: CLAUDE.md, 開発履歴.md, README.md, 本 quick 文書
- **action**: 予定機能を完了化・モジュール表/制限/機能表/履歴を更新。
- **verify**: lang parity・全テストグリーン
- **done**: v1.6.1 として記録が揃う

## must_haves

- truths: 暗号化 PDF を認証して開ける／付与・解除の別名保存／印刷導線が動作・ruff/pytest グリーン
- artifacts: 新規 `password.py`/`print_ops.py`・テスト 2 本・コミット・本 quick 文書
- key_links: pagefolio/file_ops.py, pagefolio/print_ops.py, pagefolio/dialogs/password.py
