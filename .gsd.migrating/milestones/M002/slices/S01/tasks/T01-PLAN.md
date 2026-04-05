---
estimated_steps: 1
estimated_files: 14
skills_used: []
---

# T01: pagefolio/ パッケージ作成 + コード分割

pagefolio.py を pagefolio/ パッケージに分割する。\n1. pagefolio/ ディレクトリ作成\n2. constants.py — THEMES, C, APP_VERSION, LANG\n3. settings.py — 設定ユーティリティ関数\n4. plugins.py — PDFEditorPlugin, PluginManager\n5. dialogs.py — AboutDialog, SettingsDialog, PluginDialog, MergeOrderDialog\n6. file_drop.py — _setup_file_drop\n7. Mixin モジュール群: ui_builder.py, file_ops.py, page_ops.py, viewer.py, dnd.py\n8. app.py — PDFEditorApp 本体（Mixin 統合）\n9. __init__.py — 後方互換の公開API\n10. __main__.py — エントリーポイント\n11. トップレベル pagefolio.py を薄いランチャーに置換

## Inputs

- `pagefolio.py (旧単一ファイル)`

## Expected Output

- `pagefolio/ パッケージ (13ファイル)`
- `pagefolio.py (薄いランチャー)`

## Verification

python -c "import pagefolio; print(pagefolio.APP_VERSION)" && ruff check . && ruff format --check . && pytest tests/ -v
