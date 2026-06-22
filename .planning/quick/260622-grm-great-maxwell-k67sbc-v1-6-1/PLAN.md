---
quick_id: 260622-grm
slug: great-maxwell-k67sbc-v1-6-1
date: 2026-06-22
type: quick
mode: quick
---

# Plan: OCR テキスト抽出画面のタイムアウト上限を 900 秒へ拡大（v1.6.1）

## 背景

OCR テキスト抽出画面（`OCRDialog`）のタイムアウト設定は上限 600 秒でクランプされていた。
大きな Vision モデルや多ページ処理では 1 ページあたりの応答に時間がかかり、600 秒では
途中で `TimeoutError` になるケースがあるため、上限を **900 秒** へ拡大する。

タイムアウト値（`ocr_timeout`）は OCR 抽出画面と「LLM 設定」ダイアログ
（`LLMConfigDialog`）の両方が同じ設定キーを共有する。抽出画面だけ拡げても設定ダイアログ側で
600 にキャップされ整合が崩れるため、両画面の Spinbox 上限とクランプを同時に引き上げる。

## 変更箇所（上限 600 → 900）

| ファイル | 箇所 |
|----------|------|
| `pagefolio/ocr_dialog.py` | タイムアウト Spinbox `to=900` / 実行時クランプ `min(900, ...)` |
| `pagefolio/dialogs/llm_config.py` | タイムアウト Spinbox `to=900` / 保存時クランプ `min(900, ...)` |

## タスク

### Task 1: タイムアウト上限の引き上げ
- **files**: `pagefolio/ocr_dialog.py`, `pagefolio/dialogs/llm_config.py`
- **action**: Spinbox の `to=600`、および `max(10, min(600, ...))` クランプ計 4 箇所を `900` 化。
  下限（10 秒）・既定（120 秒）・刻み（10 秒）は不変。
- **verify**: `ruff check .` クリーン / `pytest` 全パス
- **done**: 600 が 4 箇所すべて 900 に更新

### Task 2: バージョン同期とドキュメント更新
- **files**: `pagefolio/constants.py`, `README.md`, `開発履歴.md`
- **action**: `APP_VERSION` を `v1.6.1` に更新（CLAUDE.md 規約）、README バッジ・開発履歴.md の
  索引行/詳細/最終更新ヘッダを同期。`pyproject.toml` は編集しない。
- **verify**: 3 ファイルのバージョン表記が v1.6.1 で一致
- **done**: v1.6.1 として記録が揃う

## must_haves

- truths: タイムアウト上限が抽出画面・設定ダイアログ双方で 900 秒／ruff・pytest グリーン
- artifacts: コミット（OCR タイムアウト拡大）・本 quick 文書・STATE.md の Quick Tasks 行
- key_links: pagefolio/ocr_dialog.py, pagefolio/dialogs/llm_config.py, pagefolio/constants.py
