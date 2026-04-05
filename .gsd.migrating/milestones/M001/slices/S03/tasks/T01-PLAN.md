---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T01: PluginManager テストの作成

PluginManager の discover_plugins, load_plugin, enable_plugin, disable_plugin, fire_event のテスト。tmp_path にダミープラグイン .py を生成して検出・読込を検証。

## Inputs

- `pagefolio.py`
- `tests/conftest.py`

## Expected Output

- `tests/test_plugins.py`

## Verification

pytest tests/test_plugins.py -v
