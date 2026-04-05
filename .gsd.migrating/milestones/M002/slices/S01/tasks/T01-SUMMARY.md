---
id: T01
parent: S01
milestone: M002
provides: []
requires: []
affects: []
key_files: ["pagefolio/__init__.py", "pagefolio/__main__.py", "pagefolio/constants.py", "pagefolio/settings.py", "pagefolio/plugins.py", "pagefolio/app.py", "pagefolio/ui_builder.py", "pagefolio/file_ops.py", "pagefolio/page_ops.py", "pagefolio/viewer.py", "pagefolio/dnd.py", "pagefolio/dialogs.py", "pagefolio/file_drop.py", "pagefolio.py", "tests/test_utils.py", "tests/test_plugins.py"]
key_decisions: ["MixinパターンでPDFEditorAppを5モジュールに分割", "後方互換は__init__.pyのre-exportで維持", "テストのmonkeypatch対象を内部モジュールに変更", "_get_settings_pathをプロジェクトルート基準に変更"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "python -c 'import pagefolio; print(pagefolio.APP_VERSION)' → v0.9.5、ruff check + format --check グリーン、pytest 78件全パス"
completed_at: 2026-03-31T10:22:09.912Z
blocker_discovered: false
---

# T01: pagefolio.py を13モジュールのパッケージに分割、78テスト全パス

> pagefolio.py を13モジュールのパッケージに分割、78テスト全パス

## What Happened
---
id: T01
parent: S01
milestone: M002
key_files:
  - pagefolio/__init__.py
  - pagefolio/__main__.py
  - pagefolio/constants.py
  - pagefolio/settings.py
  - pagefolio/plugins.py
  - pagefolio/app.py
  - pagefolio/ui_builder.py
  - pagefolio/file_ops.py
  - pagefolio/page_ops.py
  - pagefolio/viewer.py
  - pagefolio/dnd.py
  - pagefolio/dialogs.py
  - pagefolio/file_drop.py
  - pagefolio.py
  - tests/test_utils.py
  - tests/test_plugins.py
key_decisions:
  - MixinパターンでPDFEditorAppを5モジュールに分割
  - 後方互換は__init__.pyのre-exportで維持
  - テストのmonkeypatch対象を内部モジュールに変更
  - _get_settings_pathをプロジェクトルート基準に変更
duration: ""
verification_result: passed
completed_at: 2026-03-31T10:22:09.913Z
blocker_discovered: false
---

# T01: pagefolio.py を13モジュールのパッケージに分割、78テスト全パス

**pagefolio.py を13モジュールのパッケージに分割、78テスト全パス**

## What Happened

pagefolio.py（3,136行）を pagefolio/ パッケージ（13モジュール）に分割した。PDFEditorApp は5つの Mixin（UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin）で機能分離。ダイアログ4クラスは dialogs.py に集約。後方互換は __init__.py で維持。テスト8件がパッチ対象変更で失敗したため、monkeypatch/patch.object の対象を内部モジュール（pagefolio.settings, pagefolio.plugins）に修正して全78件パス。

## Verification

python -c 'import pagefolio; print(pagefolio.APP_VERSION)' → v0.9.5、ruff check + format --check グリーン、pytest 78件全パス

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "import pagefolio; print(pagefolio.APP_VERSION)"` | 0 | ✅ pass | 500ms |
| 2 | `ruff check . && ruff format --check .` | 0 | ✅ pass | 500ms |
| 3 | `python -m pytest tests/ -v` | 0 | ✅ pass (78 passed) | 840ms |


## Deviations

テストのパッチ対象を pagefolio.settings / pagefolio.plugins モジュールに変更する必要があった（__init__.py 経由のパッチではモジュール内参照に効かないため）

## Known Issues

None.

## Files Created/Modified

- `pagefolio/__init__.py`
- `pagefolio/__main__.py`
- `pagefolio/constants.py`
- `pagefolio/settings.py`
- `pagefolio/plugins.py`
- `pagefolio/app.py`
- `pagefolio/ui_builder.py`
- `pagefolio/file_ops.py`
- `pagefolio/page_ops.py`
- `pagefolio/viewer.py`
- `pagefolio/dnd.py`
- `pagefolio/dialogs.py`
- `pagefolio/file_drop.py`
- `pagefolio.py`
- `tests/test_utils.py`
- `tests/test_plugins.py`


## Deviations
テストのパッチ対象を pagefolio.settings / pagefolio.plugins モジュールに変更する必要があった（__init__.py 経由のパッチではモジュール内参照に効かないため）

## Known Issues
None.
