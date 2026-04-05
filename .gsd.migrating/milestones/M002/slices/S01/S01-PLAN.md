# S01: パッケージ構造作成 + コード分割

**Goal:** pagefolio.py を pagefolio/ パッケージに分割し、全モジュールが import 可能な状態にする
**Demo:** After this: pagefolio/ パッケージが存在し、python -c 'import pagefolio' が成功する

## Tasks
- [x] **T01: pagefolio.py を13モジュールのパッケージに分割、78テスト全パス** — pagefolio.py を pagefolio/ パッケージに分割する。\n1. pagefolio/ ディレクトリ作成\n2. constants.py — THEMES, C, APP_VERSION, LANG\n3. settings.py — 設定ユーティリティ関数\n4. plugins.py — PDFEditorPlugin, PluginManager\n5. dialogs.py — AboutDialog, SettingsDialog, PluginDialog, MergeOrderDialog\n6. file_drop.py — _setup_file_drop\n7. Mixin モジュール群: ui_builder.py, file_ops.py, page_ops.py, viewer.py, dnd.py\n8. app.py — PDFEditorApp 本体（Mixin 統合）\n9. __init__.py — 後方互換の公開API\n10. __main__.py — エントリーポイント\n11. トップレベル pagefolio.py を薄いランチャーに置換
  - Estimate: 45min
  - Files: pagefolio/__init__.py, pagefolio/__main__.py, pagefolio/constants.py, pagefolio/settings.py, pagefolio/plugins.py, pagefolio/app.py, pagefolio/ui_builder.py, pagefolio/file_ops.py, pagefolio/page_ops.py, pagefolio/viewer.py, pagefolio/dnd.py, pagefolio/dialogs.py, pagefolio/file_drop.py, pagefolio.py
  - Verify: python -c "import pagefolio; print(pagefolio.APP_VERSION)" && ruff check . && ruff format --check . && pytest tests/ -v
