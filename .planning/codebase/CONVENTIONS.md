# Coding Conventions

**Analysis Date:** 2026-06-10

## Naming Patterns

**Files:**
- Module files use `snake_case.py` (e.g., `ui_builder.py`, `file_ops.py`, `page_ops.py`, `ocr.py`)
- Test files use `test_<module>.py` prefix (e.g., `test_pdf_ops.py`, `test_plugins.py`, `test_ocr.py`)
- Dialog modules in subpackage: `about.py`, `settings.py`, `plugin.py`, `merge.py`, `llm_config.py`

**Classes:**
- Use PascalCase (e.g., `PDFEditorApp`, `UIBuilderMixin`, `FileOpsMixin`)
- Mixin classes end with `Mixin` suffix (e.g., `UIBuilderMixin`, `ViewerMixin`, `DnDMixin`, `OCRMixin`)
- Dialog classes end with `Dialog` suffix (e.g., `AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog`)
- Base classes use clear inheritance names (e.g., `OCRProvider` abstract base)

**Methods and Functions:**
- Private/internal methods use `_` prefix (e.g., `_build_styles`, `_refresh_all`, `_set_status`, `_check_doc`)
- Event handlers use `_on_<event>` or `_do_<action>` convention (e.g., `_on_dnd_drop`, `_do_merge`, `_on_file_open`)
- Public API methods use plain names without prefix (e.g., `discover_plugins`, `load_plugin`, `fire_event`)
- Getter/setter pairs use `get_<attr>`/`set_<attr>` (e.g., `get_current_font_size()`, `set_current_font_size()`)
- Test methods use `test_<feature>` format describing what is tested (e.g., `test_open_valid_pdf`, `test_rotate_90`, `test_discover_plugins`)

**Variables and Attributes:**
- Instance attributes use `snake_case` (e.g., `self.current_page`, `self.selected_pages`, `self.thumb_cache`, `self._undo_stack`)
- Private attributes use `_` prefix (e.g., `self._undo_stack`, `self._redo_stack`, `self._preview_gen`, `self._session_api_keys`)
- Cache/state variables clearly indicate purpose (e.g., `thumb_cache`, `crop_rect`, `crop_drag_start`, `_pending_click`)
- Generation counters for thread safety use `_<component>_gen` suffix (e.g., `self._preview_gen`, `self._thumb_gen`)

**Constants:**
- Use `UPPER_SNAKE_CASE` (e.g., `APP_VERSION`, `SETTINGS_FILE`, `PLUGINS_DIR`, `MAX_UNDO`, `SUPPORTED_EXTENSIONS`)
- Theme color constants accessed via `C["KEY"]` dictionary (e.g., `C["BG_DARK"]`, `C["ACCENT"]`, `C["TEXT_MAIN"]`)
- Never hardcode hex color strings in code—always use the `C` dict
- Configuration constants defined at module level (e.g., `DEFAULT_LM_STUDIO_URL`, `DEFAULT_OCR_TIMEOUT`, `DEFAULT_OCR_SCALE`)
- Security-related constants as frozensets (e.g., `SUPPORTED_EXTENSIONS`, `IMAGE_EXTENSIONS`, `_SENSITIVE_KEYS`)

## Code Style

**Formatting:**
- Line length: 88 characters (Ruff configuration in `pyproject.toml`)
- Indentation: 4 spaces (PEP 8)
- No trailing whitespace

**Linting:**
- Tool: Ruff (`v0.15.7`)
- Command: `ruff check . && ruff format .`
- Enabled rules: `["E", "F", "W", "I", "S", "B"]` (E: errors, F: undefined names, W: warnings, I: imports, S: security, B: bugbear)
- Per-file exceptions: `tests/**/*.py` exempt from `S101` (assert allowed in tests only)

**Import Organization:**

Order imports as:
1. Standard library (`import os`, `import json`, `import logging`, etc.)
2. Third-party packages (`import tkinter`, `import fitz`, `import pytest`, etc.)
3. Local application (`from pagefolio.constants import ...`, `from pagefolio.app import ...`)

Example from `pagefolio/app.py`:
```python
import logging
import os
import tkinter as tk
from collections import deque
from tkinter import messagebox

from pagefolio.constants import LANG, SUPPORTED_EXTENSIONS, C
from pagefolio.dialogs import PluginDialog, SettingsDialog
from pagefolio.file_ops import FileOpsMixin
from pagefolio.plugins import PluginManager
```

**Module Docstrings:**
- Every module has a top-level docstring (triple-quoted) describing its purpose
- Format: One line description on first line, optional details below
- Example: `"""ファイル操作 Mixin — open/save/undo/redo"""`

**Class and Method Docstrings:**
- Public methods and classes typically have single-line docstrings (brief description)
- Complex methods include parameter documentation
- Example:
  ```python
  def _apply_inverse(self, state):
      """現在の doc 状態から逆デルタを構築して返す。
      _restore_state 内で逆操作を適用する直前に呼ぶ。
      返り値は pdf_bytes キーを持たない op 別 state dict。
      """
  ```

## Error Handling

**Patterns:**

1. **Explicit Exception Types:**
   - NEVER use bare `except:` clause
   - Always use `except Exception as e:` or specific exception types
   - Example from `pagefolio/app.py`:
     ```python
     except Exception as e:
         logger.debug("ジオメトリ復元失敗: %s", e)
     ```

2. **User-Visible Errors:**
   - Use `messagebox.showerror()` for file operations and user-facing failures
   - Use `messagebox.showinfo()` for informational messages
   - Use `messagebox.askyesno()` for confirmation dialogs
   - Example from `pagefolio/page_ops.py`:
     ```python
     except Exception as e:
         messagebox.showerror(self._t("err_title"), str(e))
     ```

3. **Logging Errors:**
   - Use `logger.debug()` for recoverable errors (UI state issues, temporary failures)
   - Use `logger.exception()` for unexpected exceptions (log full traceback)
   - Use `logger.error()` for security violations (e.g., sensitive key leakage detection)
   - Example from `pagefolio/settings.py`:
     ```python
     logger.error(
         "機密キー '%s' が settings に混入しています（保存から除外します）", k
     )
     ```

4. **Silent Failures:**
   - Background render threads silently discard results when generation counter has advanced
   - Plugin lifecycle callbacks are individually wrapped so one plugin failure doesn't crash others
   - Rationale: UI remains responsive; non-critical async operations don't block main thread

## Logging

**Framework:** Python's built-in `logging` module

**Initialization:**
- Each module declares: `logger = logging.getLogger(__name__)`
- App-level setup in `pagefolio/app.py.__init__()`:
  ```python
  logging.basicConfig(
      level=logging.WARNING,
      format="%(levelname)s:%(name)s:%(message)s",
  )
  ```

**Patterns:**

- **Debug level:** Recoverable issues, state changes that may aid diagnostics
  - Window geometry save/restore failures
  - Button state updates that fail
  - File I/O edge cases
  - Example: `logger.debug("ジオメトリ復元失敗: %s", e)`

- **Exception level:** Unexpected errors with full traceback
  - Plugin UI construction failures
  - OCR backend unexpected exceptions
  - Example: `logger.exception("プラグイン UI 構築失敗: %s", e)`

- **Error level:** Security and critical issues
  - Sensitive key leakage detection
  - Example: `logger.error("機密キー '%s' が settings に混入しています")`

## Comments

**When to Comment:**
- Complex undo/redo state reconstruction logic
- Non-obvious PDF transformation mathematics (crop box clamping, coordinate transforms)
- Security-critical decisions (API key handling, file path validation)
- Plugin lifecycle edge cases
- Rationale for generation counter patterns in threading code

**Comment Style:**
- Use inline comments (`#`) for single-line explanations
- Use section dividers for related groups of methods:
  ```python
  # ══════════════════════════════════════════
  #  Undo / Redo
  # ══════════════════════════════════════════
  ```
- Use task tags in comments to mark implementation notes:
  - `# D-01:` Design decision with tag reference
  - `# M-5:` Milestone or bug fix reference
  - `# WR-03:` Work-related context

**Language:** All comments written in Japanese (マークダウン記号含む). Exception: code identifiers (variable names, function calls) remain in English.

## Function Design

**Size Guidelines:**
- Mixin methods typically 10–30 lines
- Complex methods (undo/redo logic) may reach 50+ lines but are broken into focused sub-steps
- Utility functions 5–15 lines
- Event handlers 5–20 lines

**Parameters:**
- Mixin methods receive `self` context (no `app` parameter needed)
- Dialog constructors take `(parent, font_func, lang="ja")` signature
- Callback functions receive event object as `event` parameter
- Optional keyword arguments use `**kwargs` for flexibility in undo/redo metadata

**Return Values:**
- Methods operating on documents return `None` (side-effect based)
- Validation methods return `bool` (e.g., `_check_doc() -> bool`)
- Query methods return data structures (lists, sets, dicts)
- Builders return constructed widgets (e.g., `_build_ui() -> None` but builds `self.*`)

## Module Design

**Exports:**
- Mixin modules export single class inheriting from Mixin (e.g., `FileOpsMixin`)
- Dialog modules export dialog class and optionally helper functions
- Utility modules export public functions (prefixed with `_` for internal/sensitive)
- Constants module re-exports from `lang.py`, `themes.py` for backward compatibility

**Barrel Files:**
- `pagefolio/__init__.py`: Re-exports main API (PDFEditorApp, dialogs, constants)
- `pagefolio/dialogs/__init__.py`: Re-exports all dialog classes
- Pattern: `from pagefolio.dialogs import SettingsDialog` (vs. `from pagefolio.dialogs.settings import SettingsDialog`)

**Backward Compatibility:**
- `constants.py` re-exports `THEMES`, `C`, `LANG` to maintain `from pagefolio.constants import THEMES`
- `__init__.py` maintains public surface for all dialog classes and utilities
- Test suite verifies backward compatibility explicitly (`tests/test_imports.py`)

## Theme Usage

**Pattern:**
- Never hardcode color values (e.g., `"#1a1a2e"`)
- Always use: `C["BG_DARK"]`, `C["ACCENT"]`, `C["TEXT_MAIN"]`, etc.
- Runtime theme dict `C` is updated by `_apply_theme()` in `settings.py`
- All Tkinter style definitions in `ui_builder.py` reference `C` dict

**Example:**
```python
style.configure(
    "TLabel",
    background=C["BG_DARK"],
    foreground=C["TEXT_MAIN"],
    font=("Segoe UI", fs),
)
```

## Font Size Handling

**Pattern:**
- Never hardcode font sizes (e.g., `font=("Segoe UI", 12)`)
- Use helper method `self._font(delta)` where available
- For dialogs, accept `font_func` parameter in constructor
- Example:
  ```python
  tk.Label(self, font=self._font(0))  # Use base size
  tk.Label(self, font=self._font(8, weight="bold"))  # Base + 8, bold
  ```
- Font size range: 8–16 (clamped in settings)
- Module-level helper: `pagefolio.settings._make_font(delta=0, weight=None, base_size=10)`

## Button Styling

**Standard Patterns:**
- `"TButton"` — regular operation buttons
- `"Accent.TButton"` — primary/important actions (main features)
- `"Danger.TButton"` — destructive operations (delete, quit)
- `"CropOn.TButton"` — toggle state ON (crop mode active)

**Example Usage:**
```python
ttk.Button(parent, text="Delete", style="Danger.TButton", command=self._delete_selected)
ttk.Button(parent, text="Crop", style="CropOn.TButton", command=self._toggle_crop_mode)
```

## Security & Sensitive Data

**API Key Handling:**
- API keys NEVER stored in `pagefolio_settings.json`
- Session-only storage in `self._session_api_keys` (in-memory, process scoped)
- Priority: Environment variable → Session memory (in `_resolve_api_key` in `pagefolio/ocr.py`)
- `_SENSITIVE_KEYS` frozenset in `settings.py` acts as structural guard

**Example of correct pattern:**
```python
# ❌ WRONG: Never let API keys reach settings dict
settings["api_key"] = "sk-..."

# ✅ RIGHT: Use session-only storage
self._session_api_keys["claude"] = "sk-..."
```

## Docstring Language

**Default Language:** Japanese (日本語)

All docstrings, comments, and user-facing strings are written in Japanese. Exception: code identifiers remain in English.

---

*Convention analysis: 2026-06-10*
