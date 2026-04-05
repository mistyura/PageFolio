# S03: プラグインシステムテスト + 最終検証

**Goal:** PluginManager の検出・読込・有効/無効切替のテストを作成し、全テストスイートの最終検証と開発履歴の更新を行う
**Demo:** After this: pytest tests/ -v が全テストパス。ruff もクリーン

## Tasks
- [x] **T01: PluginManagerテスト17件を作成し、全78テスト＋ruffグリーンを確認。開発履歴を更新** — PluginManager の discover_plugins, load_plugin, enable_plugin, disable_plugin, fire_event のテスト。tmp_path にダミープラグイン .py を生成して検出・読込を検証。
  - Estimate: 20min
  - Files: tests/test_plugins.py
  - Verify: pytest tests/test_plugins.py -v
- [x] **T02: 最終検証: 78テスト全パス + ruff グリーン確認** — 開発履歴.md にテスト基盤整備のエントリを追加。全テスト + ruff で最終確認。
  - Estimate: 10min
  - Files: 開発履歴.md
  - Verify: ruff check . && ruff format --check . && pytest tests/ -v
