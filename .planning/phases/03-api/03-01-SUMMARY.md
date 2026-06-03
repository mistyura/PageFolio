---
phase: 03-api
plan: "01"
subsystem: settings
tags: [refactoring, api, settings, font-size]
dependency_graph:
  requires: []
  provides: [set_current_font_size, get_current_font_size]
  affects: [pagefolio/settings.py, pagefolio/__init__.py, pagefolio/app.py, pagefolio/dialogs/merge.py, pagefolio/dialogs/llm_config.py]
tech_stack:
  added: []
  patterns: [module-level setter/getter with global declaration, public API re-export via __init__.py]
key_files:
  created: []
  modified:
    - pagefolio/settings.py
    - pagefolio/__init__.py
    - pagefolio/app.py
    - pagefolio/dialogs/merge.py
    - pagefolio/dialogs/llm_config.py
decisions:
  - "D-04: set_current_font_size はクランプ・バリデーションなし単純代入のみ（挙動変更禁止）"
  - "D-05: __init__.py で setter/getter を再エクスポートし公開 API の一貫性を維持"
metrics:
  duration: "約 5 分"
  completed: "2026-06-03T06:20:50Z"
---

# Phase 03 Plan 01: settings.py 公開 setter/getter 追加 (REFAC-04) Summary

**One-liner:** `set_current_font_size` / `get_current_font_size` 公開 API を settings.py に追加し、app.py・merge.py・llm_config.py の `_current_font_size` 直接アクセスをすべて API 経由に置換（DEBT-04 解消 / D-02 stale binding 修正）。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | settings.py に setter/getter 追加・__init__.py 再エクスポート | 7506fc3 | pagefolio/settings.py, pagefolio/__init__.py |
| 2 | write 側（app.py）と read 側（merge.py / llm_config.py）を公開 API 経由に切り替え | d402cfb | pagefolio/app.py, pagefolio/dialogs/merge.py, pagefolio/dialogs/llm_config.py |

## Changes Summary

### pagefolio/settings.py

`_current_font_size = 12` の直後に公開 API を追加:

- `set_current_font_size(size: int) -> None` — 関数内 `global _current_font_size` 宣言付きの単純代入（D-04 準拠）
- `get_current_font_size() -> int` — `_current_font_size` を返すのみ

### pagefolio/__init__.py

settings 再エクスポートブロックに `get_current_font_size` / `set_current_font_size` を追記（D-05 推奨）。

### pagefolio/app.py

- ファイル先頭 import ブロックに `set_current_font_size` を追加
- `__init__` 内（行 49–51）: ローカル `import pagefolio.settings as _settings_mod` + `_settings_mod._current_font_size = self.font_size` → `set_current_font_size(self.font_size)` に置換
- `_apply_settings` 内（行 346–348）: 同上の置換

### pagefolio/dialogs/merge.py

- `from pagefolio.settings import _current_font_size` → `from pagefolio.settings import get_current_font_size`
- `MergeOrderDialog.__init__` の `self._font_size = _current_font_size` → `self._font_size = get_current_font_size()`
- `MergeResizeDialog.__init__` の同箇所も同様に置換（計 2 箇所）

### pagefolio/dialogs/llm_config.py

- `from pagefolio.settings import _current_font_size` → `from pagefolio.settings import get_current_font_size`
- フォールバック内 `fs = _current_font_size` → `fs = get_current_font_size()`（計 1 箇所）

## Verification Results

- `python -c "from pagefolio.settings import set_current_font_size, get_current_font_size; set_current_font_size(14); assert get_current_font_size()==14; ..."` → OK
- `python -c "import pagefolio.app, pagefolio.dialogs.merge, pagefolio.dialogs.llm_config; print('import OK')"` → OK
- `ruff check . && ruff format .` → All checks passed / 31 files left unchanged
- `pytest tests/` → 165 passed

## Deviations from Plan

None - プランどおりに実行。

## Known Stubs

None.

## Threat Flags

None - 新規の外部入力・ネットワーク・ファイル I/O・認証経路を追加していない。

## Self-Check: PASSED

- [x] pagefolio/settings.py に `def set_current_font_size(` と `def get_current_font_size(` が存在する
- [x] `set_current_font_size` 関数本体に `global _current_font_size` が含まれる
- [x] `__init__.py` に `set_current_font_size` と `get_current_font_size` が再エクスポートされている
- [x] app.py に `_settings_mod._current_font_size =` が 0 件
- [x] app.py に `import pagefolio.settings as _settings_mod` が 0 件
- [x] merge.py に `get_current_font_size()` が 2 箇所
- [x] llm_config.py に `get_current_font_size()` が 1 箇所
- [x] コミット 7506fc3 と d402cfb が git log に存在する
- [x] pytest 165 tests passed
