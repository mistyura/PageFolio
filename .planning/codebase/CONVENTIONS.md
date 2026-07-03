# Coding Conventions

**Analysis Date:** 2026-07-03

## Naming Patterns

**Files:**
- Modules use `snake_case.py` (e.g., `file_ops.py`, `ui_builder.py`, `page_ops.py`, `ocr_providers.py`)
- Test files use `test_<module>.py` prefix (e.g., `test_pdf_ops.py`, `test_plugins.py`, `test_ocr.py`)
- Dialogs stored in `pagefolio/dialogs/` subpackage with individual files per dialog type (e.g., `settings.py`, `merge.py`, `llm_config.py`)

**Classes:**
- PascalCase for all classes (e.g., `PDFEditorApp`, `FileOpsMixin`, `SettingsDialog`)
- Mixin classes end with `Mixin` suffix (e.g., `UIBuilderMixin`, `ViewerMixin`, `DnDMixin`, `OCRMixin`, `PageOpsMixin`)
- Dialog classes end with `Dialog` suffix (e.g., `AboutDialog`, `SettingsDialog`, `PluginDialog`, `MergeOrderDialog`)
- Custom exception classes end with `Error` suffix (e.g., `PDFPasswordError`, `OCRAPIKeyError`)

**Functions & Methods:**
- Use `snake_case` for all function/method names (e.g., `_refresh_all`, `_set_status`, `_capture_page_blob`)
- `_` prefix for private/internal methods (e.g., `_build_styles`, `_do_merge`, `_refresh_all`)
- Tk event handlers use `_on_` or `_do_` prefix (e.g., `_on_merge`, `_do_insert`, `_on_run`)
- Public API methods use plain names (e.g., `discover_plugins`, `load_plugin`, `fire_event`, `ocr_image`)

**Variables & Attributes:**
- `snake_case` for all variable names (e.g., `current_page`, `selected_pages`, `thumb_cache`, `font_size`)
- Boolean variables often prefixed with `is_` or `has_` but not required (e.g., `edit_mode`, `pdf_has_password`)
- Theme colors accessed via `C["KEY"]` dict (e.g., `C["BG_DARK"]`, `C["ACCENT"]`, `C["TEXT_MAIN"]`), never hardcoded hex strings
- Settings dict keys use `snake_case` (e.g., `font_size`, `thumb_page_size`, `window_geometry`)

**Constants:**
- `UPPER_SNAKE_CASE` for module-level constants (e.g., `APP_VERSION`, `MAX_UNDO`, `SUPPORTED_EXTENSIONS`, `MOSAIC_BLOCK`)
- `frozenset` for immutable extension sets (e.g., `SUPPORTED_EXTENSIONS`, `IMAGE_EXTENSIONS`)
- Dictionary constants like `THEMES`, `LANG`, `OCR_PROMPTS` defined in dedicated modules

## Code Style

**Formatting:**
- Line length: 88 characters (configured in `pyproject.toml`)
- 4-space indentation (Python standard)
- Tool: Ruff 0.15.7 for linting and auto-formatting

**Linting Rules (Ruff):**
- Selected rule categories: `E` (errors), `F` (Pyflakes), `W` (warnings), `I` (isort imports), `S` (security), `B` (bugbear)
- All errors/warnings must be fixed before commit
- Exception: `S101` (assert) is allowed in `tests/**/*.py`
- Run before commit: `ruff check . && ruff format .`

**Imports:**
- Use absolute imports from `pagefolio` package (e.g., `from pagefolio.constants import LANG, C`)
- Organize imports in standard Python order: stdlib, third-party, local
- Use `# noqa: F401` when re-exporting (e.g., in `__init__.py` and `constants.py`)
- Use `# noqa: E402` for post-path-insert imports (e.g., in test files that modify `sys.path`)
- Avoid circular imports by structuring modules as pure functions or classes with minimal coupling

**Import Organization Example (from `pagefolio/app.py`):**
```python
import logging
import os
import tkinter as tk
from collections import deque
from tkinter import messagebox

from pagefolio.constants import LANG, SUPPORTED_EXTENSIONS, C
from pagefolio.dialogs import PluginDialog, SettingsDialog
from pagefolio.dnd import DnDMixin
from pagefolio.file_drop import _setup_file_drop
# ... more imports
```

## Error Handling

**Exception Handling:**
- Never use bare `except:` — always `except Exception as e:`
- Catch specific exceptions when possible (e.g., `except FileNotFoundError:`, `except fitz.FileNotFoundError:`)
- Log exceptions with context using `logger.error()` or `logger.exception()`
- User-facing errors use `messagebox.showerror()` from tkinter

**Exception Patterns:**

*File operations:*
```python
try:
    doc = fitz.open(filepath)
except (FileNotFoundError, fitz.FileNotFoundError) as e:
    logger.error("Failed to open PDF: %s", e)
    messagebox.showerror(self._t("error_title"), self._t("error_open_failed"))
```

*Password-protected PDFs:*
```python
except fitz.FileError as e:
    if "encrypted" in str(e).lower():
        # Handle password-required case
    else:
        raise
```

*Custom exceptions:*
```python
class PDFPasswordError(Exception):
    """パスワード付き PDF の認証がキャンセル/失敗したことを表す例外。"""

class OCRAPIKeyError(RuntimeError):
    """API キーが見つからない場合の例外。"""
    def __init__(self, env_var):
        self.env_var = env_var
        super().__init__(f"API key not found: {env_var}")
```

## Logging

**Framework:** Standard library `logging` module

**Logger Setup:**
- Each module creates its own logger: `logger = logging.getLogger(__name__)`
- Root logger configured in `PDFEditorApp.__init__()` with WARNING level
- Format: `"%(levelname)s:%(name)s:%(message)s"`

**Logging Levels:**
- `logger.debug()` — Detailed diagnostic info (e.g., geometry restoration, slow operations)
- `logger.info()` — General informational messages (rarely used in current codebase)
- `logger.warning()` — Warning conditions (default level set in app)
- `logger.error()` — Error conditions with context (exceptions, failed operations)
- `logger.exception()` — Error with full exception traceback (when catching in handlers)

**Patterns:**
```python
logger.debug("ジオメトリ復元失敗: %s", e)
logger.error("Failed to open PDF: %s", filepath)
logger.exception("Unexpected error during OCR")
```

## Comments & Documentation

**When to Comment:**
- Non-obvious algorithms or design decisions
- Complex state machines or Blob lifecycle management
- Bug workarounds or PyMuPDF quirks
- Section headers for logical groupings (using `# ══════════════════════`)

**Section Headers:**
```python
# ══════════════════════════════════════════
#  Undo / Redo
# ══════════════════════════════════════════
def _save_undo(self, op, **kwargs):
    ...
```

**Module Docstrings:**
All modules include docstrings in Japanese (e.g., `"""ファイル操作 Mixin — open/save/undo/redo"""`)

**Function Docstrings:**
Complex functions include docstrings explaining parameters and behavior:
```python
def _capture_page_blob(self, page_i):
    """page_i の 1 ページを単独 PDF として Blob 化して返す。

    delete / insert / merge / page_edit 系デルタの共有キャプチャ経路。
    64KiB 以上はディスク退避（FileBlob）、未満はメモリ保持（MemBlob）。
    """
```

## Function Design

**Size & Complexity:**
- Keep functions focused and single-responsibility
- Long Mixin classes are acceptable (each Mixin clusters related methods by responsibility)
- Helper functions extract common patterns (e.g., `_blob_bytes()`, `resolve_ocr_prompt()`)

**Parameters:**
- Use keyword arguments for complex functions (e.g., `_save_undo(self, op, **kwargs)`)
- Avoid excessive positional arguments; group related params into dicts or dataclasses
- Type hints use inline Python 3.8-compatible syntax (no `from __future__ import annotations`)

**Return Values:**
- Functions return concrete values or `None`, no sentinel values like `-1`
- Use tuples for multiple return values (e.g., `(page_i, cropbox_tuple)`)
- Generators used for thread-safe state updates (e.g., `_run_gen` in OCR dialog)

## Module Design

**Exports:**
- Public APIs defined at module top level (e.g., `OCRProvider` base class, `PluginManager`)
- Private/helper functions prefixed with `_` (e.g., `_setup_file_drop()`, `_apply_theme()`)
- Re-exports used for backward compatibility (e.g., `pagefolio/constants.py` re-exports `THEMES`, `LANG`, `C`)

**Barrel Files:**
- `pagefolio/__init__.py` exports public classes for simple imports: `from pagefolio import PluginManager, PDFEditorPlugin`
- `pagefolio/dialogs/__init__.py` re-exports all dialog classes for `from pagefolio.dialogs import SettingsDialog` compatibility
- Re-exports use `# noqa: F401` to silence unused import warnings

## Theme & UI Patterns

**Theme Color Usage:**
- Always reference colors via `C["KEY"]` dict, never hardcoded hex strings
- Available keys: `BG_DARK`, `BG_PANEL`, `BG_CARD`, `ACCENT`, `TEXT_MAIN`, `TEXT_SUB`, `SUCCESS`, `WARNING`, `DANGER_BG`, `DANGER_FG`, `CROP_ON_BG`
- Theme dict `C` is updated at runtime by `_apply_theme()` in settings module

**Button Styles (ttk.Button `style` parameter):**
- `"TButton"` — standard operations (default)
- `"Accent.TButton"` — primary/important actions (highlights accent color)
- `"Danger.TButton"` — destructive operations (delete, quit)
- `"CropOn.TButton"` — trim mode active indicator

**Font Handling:**
- Never hardcode font sizes; use `self._font(delta)` helper method
- `_font(delta, weight="")` returns `("Segoe UI", base_size + delta, weight)` tuple
- Tkinter widgets use `font=self._font(0)` for normal size, `self._font(2, "bold")` for headings

## State Management Conventions

**Instance Attributes (in `PDFEditorApp`):**
- `self.doc` — Current `fitz.Document` or `None` when no file open
- `self.filepath` — String path to open file or `None`
- `self.current_page` — 0-based page index (integer)
- `self.selected_pages` — `set[int]` for multi-page selection
- `self._undo_stack` / `self._redo_stack` — `deque` with operation state dicts
- `self.thumb_cache` — `dict[int, ImageTk.PhotoImage]` for thumbnail cache
- `self.settings` — `dict` with user preferences (loaded from JSON)
- `self.font_size` — Integer 8–16 (base size for relative font calculations)
- `self.edit_mode` — Boolean (persisted in settings)

**Never Mutate:**
- Call `_push_evicting()` instead of directly appending to undo/redo stacks (to release Blob files)
- Call `_clear_undo_stacks()` to clean up both stacks (not separate clears)
- Use `_dispose_state()` to release Blob objects in states

## Forbidden Patterns

**Prohibited:**
- Bare `except:` clause (always specify exception type)
- `# type: ignore` comments without approval (never use)
- Hardcoded hex color strings (use `C` dict instead)
- Hardcoded font sizes (use `_font()` helper)
- Direct append to `_undo_stack` / `_redo_stack` without `_push_evicting()`
- `pyproject.toml` edits (sacred configuration)

---

*Convention analysis: 2026-07-03*
