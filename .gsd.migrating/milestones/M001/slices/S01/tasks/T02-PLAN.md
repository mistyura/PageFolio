---
estimated_steps: 1
estimated_files: 1
skills_used: []
---

# T02: 設定・テーマ・フォント関数のテスト作成

_load_settings, _save_settings, _get_settings_path のテスト。デフォルト値、ファイルなし、不正JSON、読み書き往復。_resolve_theme, _apply_theme のテスト。dark/light/system/不正値。_make_font のテスト。delta・最小値・ weight 。

## Inputs

- `pagefolio.py`
- `tests/conftest.py`

## Expected Output

- `tests/test_utils.py`

## Verification

pytest tests/test_utils.py -v
