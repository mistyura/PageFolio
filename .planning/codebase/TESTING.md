# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

**Status:** No test framework detected

**What Exists:**
- No unit test runner (`pytest`, `unittest`, `nose2`, etc.)
- No test configuration files (`pytest.ini`, `setup.cfg`, `conftest.py`)
- No test files (`test_*.py`, `*_test.py`) in repository
- No CI/CD pipeline files (`.github/workflows`, `.gitlab-ci.yml`, etc.)

**Current Testing Approach:**
- Manual testing only (developer runs application and verifies behavior)
- No automated testing infrastructure
- Changes validated through manual interaction with PageFolio UI

## Implications for Adding Tests

If testing is added to this project, here are the structural constraints:

**Framework Recommendation:** `pytest` (lightweight, suitable for UI testing)

**Test Organization:**
- Create `tests/` directory at project root (sibling to `pagefolio.py`)
- Place test files as `tests/test_{module}.py`

**Fixtures Location:**
- `tests/fixtures/` for sample PDF files, test data
- `tests/conftest.py` for shared pytest fixtures (if using pytest)

**Run Commands (proposed):**
```bash
pytest tests/              # Run all tests
pytest tests/ -v           # Verbose output
pytest tests/ --cov        # Coverage report
pytest tests/ -k keyword   # Run tests matching keyword
pytest tests/ -s            # Show print statements
```

## Testing Strategy for Existing Code

**What's Hard to Test:**
- GUI code (Tkinter event binding, widget state, rendering)
- PDF manipulation using `fitz` library requires sample PDFs
- File I/O operations (open, save, delete) need fixtures
- Plugin system with dynamic loading requires careful mocking

**What's Easier to Test (if refactored):**
- Pure functions like `_detect_system_theme()`, `_resolve_theme()`, `_get_settings_path()` (line 387-404, 359-361)
- Plugin lifecycle methods (enable, disable, load, unload) — currently in `PluginManager` class (line 567-583)
- State management: undo/redo stack operations, page selection, crop rect calculations
- Configuration loading/saving (`_load_settings`, `_save_settings`) — line 363-385

**Testing Barriers (Current Structure):**
1. Single-file monolithic design makes unit isolation difficult
2. Heavy Tkinter coupling (most methods modify UI state)
3. Global state (`C` dictionary, `LANG` dictionary, `_current_font_size` variable)
4. No dependency injection; dependencies created internally (e.g., `fitz.open()`)

## Testable Components (Current Code)

**Configuration Management (Testable):**
```python
# From line 363-385
def _load_settings():
    """設定を読み込む。ファイルがなければデフォルト値を返す"""
    defaults = {"theme": "dark", "font_size": 12, "lang": "ja"}
    try:
        path = _get_settings_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return dict(defaults)
```
**Suggested Tests:**
- Load settings when file exists
- Load settings when file missing (returns defaults)
- Merge partial file with defaults
- Handle corrupted JSON gracefully

**Theme Resolution (Testable):**
```python
# From line 387-404
def _detect_system_theme():
    """Windowsのシステムテーマを検出。ダーク→'dark'、ライト→'light'"""
    ...

def _resolve_theme(theme_setting):
    """テーマ設定値を実際のテーマ名に解決する"""
    if theme_setting == "system":
        return _detect_system_theme()
    return theme_setting if theme_setting in THEMES else "dark"
```
**Suggested Tests:**
- Resolve explicit theme names ("dark", "light")
- System theme detection
- Unknown theme defaults to "dark"

**Plugin System (Partially Testable):**
```python
# From line 567-583
def enable_plugin(self, plugin_id, app=None):
    """プラグインを有効化する"""
    self._disabled.discard(plugin_id)
    if plugin_id in self._plugins and app:
        try:
            self._plugins[plugin_id].on_load(app)
        except Exception:
            traceback.print_exc()
```
**Suggested Tests:**
- Enable removes plugin from disabled set
- Load called when plugin exists and app provided
- Graceful exception handling
- (Harder: on_load actually calls plugin code — requires mocking)

**Undo/Redo Stack (Testable):**
```python
# From line 985-1025 (inferred pattern)
def _save_undo(self):
    """現在の状態を Undo スタックに保存する"""
    # Saves state to _undo_stack (capped at MAX_UNDO=20)

def _undo(self):
    """Undo スタックから状態を復元"""
    # Restores from _undo_stack, pushes current to _redo_stack

def _redo(self):
    """Redo スタックから状態を復元"""
    # Restores from _redo_stack, pushes to _undo_stack
```
**Suggested Tests:**
- Undo stack limited to MAX_UNDO (20 items)
- Redo cleared when new operation performed
- Undo/redo with empty stack shows user message
- State correctly restored

## Example Test Structure (Proposed)

If tests were added to this project, they would follow this pattern:

```python
# tests/test_config.py
import pytest
import json
import os
import tempfile
from pagefolio import _load_settings, _save_settings, _resolve_theme

@pytest.fixture
def temp_settings_file():
    """Temporary settings file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"theme": "dark", "font_size": 14}, f)
        path = f.name
    yield path
    os.unlink(path)

def test_load_settings_defaults():
    """Test loading settings when file missing"""
    # Mock settings path to non-existent file
    settings = _load_settings()
    assert settings["theme"] == "dark"
    assert settings["font_size"] == 12
    assert settings["lang"] == "ja"

def test_resolve_theme_dark():
    """Test explicit dark theme"""
    result = _resolve_theme("dark")
    assert result == "dark"

def test_resolve_theme_invalid():
    """Test invalid theme defaults to dark"""
    result = _resolve_theme("invalid_theme_name")
    assert result == "dark"

def test_resolve_theme_system():
    """Test system theme resolution"""
    # This test would require mocking _detect_system_theme()
    result = _resolve_theme("system")
    assert result in ["dark", "light"]
```

```python
# tests/test_plugin_manager.py
import pytest
from pagefolio import PluginManager, PDFEditorPlugin

@pytest.fixture
def manager():
    """Create a fresh PluginManager instance"""
    return PluginManager()

@pytest.fixture
def mock_plugin():
    """Mock plugin instance"""
    class TestPlugin(PDFEditorPlugin):
        name = "Test Plugin"
        def on_load(self, app):
            self.loaded = True
        def on_unload(self, app):
            self.unloaded = True
    return TestPlugin()

def test_enable_plugin(manager, mock_plugin):
    """Test enabling a disabled plugin"""
    manager._plugins["test"] = mock_plugin
    manager._disabled.add("test")

    mock_app = type('MockApp', (), {})()
    manager.enable_plugin("test", mock_app)

    assert "test" not in manager._disabled

def test_disable_plugin(manager, mock_plugin):
    """Test disabling a plugin"""
    manager._plugins["test"] = mock_plugin

    mock_app = type('MockApp', (), {})()
    manager.disable_plugin("test", mock_app)

    assert "test" in manager._disabled
```

## What NOT to Test (Current Codebase)

**GUI Rendering:**
- Widget creation and layout (requires Tkinter display)
- Color rendering and theme application
- Font rendering

**PDF Operations:**
- Actual PDF reading, rotation, cropping (requires real PDFs)
- File save/load with real filesystem
- Best tested with integration tests + sample PDFs

**Event Handling:**
- User interactions (mouse clicks, key presses)
- Event binding and callbacks
- Drag-and-drop (D&D) operations

## Coverage Target (if tests added)

**Realistic Target:** 30-40% coverage

- High priority: Configuration, theme resolution, plugin lifecycle
- Medium priority: Undo/redo logic, page selection state
- Lower priority: GUI rendering, file operations (integration tests only)
- Not covered: Tkinter event handling, PDF rendering

**Why Low Coverage is Acceptable:**
- Single-file monolithic design couples business logic to UI
- Most methods modify state and UI simultaneously
- Meaningful unit testing would require significant refactoring
- Integration tests (manual or automated with `pyautogui`/`pyppeteer`) more valuable

## Mocking Strategy (if tests added)

**Patterns to Use:**
- `unittest.mock.patch()` for file operations
- `unittest.mock.MagicMock()` for Tkinter widgets and fitz Document
- Fixtures with `pytest` for reusable mock objects

**Example:**
```python
from unittest.mock import patch, MagicMock

@patch('pagefolio.os.path.exists')
@patch('pagefolio.open', create=True)
def test_load_settings_from_file(mock_open, mock_exists):
    """Test loading settings from existing file"""
    mock_exists.return_value = True
    mock_open.return_value.__enter__.return_value.read.return_value = '{"theme": "light"}'

    settings = _load_settings()

    assert settings["theme"] == "light"
    mock_exists.assert_called()
    mock_open.assert_called_once()
```

---

*Testing analysis: 2026-03-17*
