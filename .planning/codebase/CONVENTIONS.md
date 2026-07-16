# Coding Conventions

**Analysis Date:** 2026-07-16

## Naming Patterns

**Files:**
- Module files: `snake_case` (e.g., `file_ops.py`, `ocr_pipeline.py`)
- Mixin files: `feature_name.py` (e.g., `ui_builder.py`, `page_ops.py`, `redact_ops.py`)
- Dialog files: `feature_name.py` placed in `pagefolio/dialogs/` directory (e.g., `merge.py`, `settings.py`)
- Test files: `test_module_name.py` matching the module being tested (e.g., `test_ocr_engine.py`, `test_pagination.py`)

**Classes:**
- Mixin classes: PascalCase ending with `Mixin` (e.g., `FileOpsMixin`, `UIBuilderMixin`, `ViewerMixin`)
- Dialog classes: PascalCase ending with `Dialog` or `Toplevel` subclass (e.g., `OCRDialog`, `SettingsDialog`, `MergeOrderDialog`)
- Business logic classes: PascalCase (e.g., `PDFEditorApp`, `OCRRunEngine`, `PluginManager`)
- Exception classes: PascalCase ending with `Error` or `Exception` (e.g., `PDFPasswordError`, `OCRAPIKeyError`, `OCRRetryableError`)
- Data holder classes: PascalCase (e.g., `BatchFileEntry`, `BatchState`, `PipelineState`)

**Functions:**
- Public functions: `snake_case` (e.g., `window_bounds()`, `to_global()`, `merge_shortcuts()`)
- Private module-level functions: `_snake_case` prefix (e.g., `_resolve_api_key()`, `_split_inline()`, `_lookup_price()`)
- Methods (public): `snake_case` (e.g., `ocr_image()`, `list_models()`)
- Methods (private/internal): `_snake_case` prefix, often called by UI handlers (e.g., `_save_undo()`, `_refresh_all()`, `_open_file()`)
- Callback/event handlers: `_on_event_name` or `_callback_name` (e.g., `_on_file_open()`, `_on_progress()`)
- Helper properties: `@property` decorated, `_name` format (e.g., `_pending_pages`, `_font_size`)

**Variables:**
- Constants: `UPPER_CASE` (e.g., `SUPPORTED_EXTENSIONS`, `MAX_UNDO`, `THUMB_CACHE_MAX`, `PT_PER_MM`)
- Instance attributes: `snake_case` or `_snake_case` if private (e.g., `self.doc`, `self._undo_stack`, `self.current_page`)
- Local variables: `snake_case` (e.g., `page_i`, `selected_pages`, `window_start`)
- Loop variables: `i`, `j`, `k` for indices; named descriptively for content (e.g., `for page in pages:`)
- Configuration dict keys: lowercase with underscores (e.g., `"theme"`, `"font_size"`, `"edit_mode"`)

**Types:**
- Type hints use PEP 484 format (e.g., `str`, `int`, `bool`, `list[int]`, `dict[str, Any]`)
- Union types: `Optional[Type]` or `Type | None` style when imported

## Code Style

**Formatting:**
- Line length: 88 characters (configured in `pyproject.toml`)
- Indentation: 4 spaces
- Enforced by: `ruff format` (automatic formatting)

**Linting:**
- Tool: `ruff` (configured in `pyproject.toml`)
- Selection: `["E", "F", "W", "I", "S", "B"]` (Error, Pyflakes, Warning, Isort, flake8-bandit, flake8-bugbear)
- All fixable rules enabled via `fixable = ["ALL"]`
- Exception: Tests allow `S101` (assert statement) via per-file-ignores

**Code organization:**
```
1. Module docstring (with description and design notes)
2. Imports (standard library, third-party, local)
3. Logger setup: `logger = logging.getLogger(__name__)`
4. Constants (UPPER_CASE)
5. Exception classes (custom exceptions)
6. Helper functions (module-level utilities prefixed with `_`)
7. Main classes (Mixins, Dialogs, etc.)
8. Entry point or test code
```

**Run formatting:**
```bash
ruff check . && ruff format .
```

## Import Organization

**Order:**
1. Standard library imports (`os`, `sys`, `logging`, `tkinter`, etc.)
2. Third-party imports (`fitz`, `pytest`, etc.)
3. Local relative imports from `pagefolio` package

**Path Aliases:**
- No aliases configured; use absolute imports from package root
- Pattern: `from pagefolio.module import Class`
- Example: `from pagefolio.constants import LANG, C`, `from pagefolio.file_ops import FileOpsMixin`

**Special imports:**
- `from pagefolio.constants import C` for theme colors (never hardcode color values)
- `from pagefolio.constants import LANG` for user-visible strings
- `from pagefolio.constants import APP_VERSION` for version information

## Error Handling

**Patterns:**
- **Custom exceptions:** Define in the module where they're primary (e.g., `PDFPasswordError` in `file_ops.py`, `OCRAPIKeyError` in `ocr_providers/errors.py`)
- **Specific catches:** Always catch specific exception types, never bare `except:`
- **Format:** `except SpecificError as e:` or `except (Error1, Error2) as e:`
- **User-visible errors:** Use `messagebox.showerror(title, msg)` for dialog display
- **Logging errors:** Use `logger.debug()` for debugging context, `logger.exception()` for full traceback on failure
- **Plugin failure isolation:** Plugin callbacks are wrapped individually so one plugin crash doesn't crash others (see `plugins.py`)

**Examples:**
```python
# From file_ops.py
except PDFPasswordError:
    # Handle password authentication failure
    ...
except Exception as e:
    logger.debug("operation failed: %s", e)
    messagebox.showerror(LANG["error_title"], str(e))

# From ocr.py
except OCRRetryableError as e:
    # Handle retryable API errors
    logger.debug("retryable error: %s", e)
except ConnectionError as e:
    # Handle network errors
    ...
except Exception as e:
    logger.exception("unexpected error: %s", e)
```

## Logging

**Framework:** `logging` (Python standard library)

**Setup pattern:**
```python
import logging

logger = logging.getLogger(__name__)
```

**Patterns:**
- **Debug:** `logger.debug(msg, *args)` - Implementation details, arguments, variable state
- **Info:** Not commonly used in this codebase
- **Warning:** `logger.warning(msg, *args)` - Unusual but recoverable situations (e.g., plugin name collision)
- **Error/Exception:** `logger.error(msg, *args)` or `logger.exception(msg, *args)` - Failures visible to user
- Format strings use `%s` style: `logger.debug("key: %s, value: %s", key, value)`

**Examples:**
```python
logger.debug("incremental save failed, reopening: %s", e)
logger.exception("OCR call failed (p.%d): %s", page_idx, e)
logger.warning("OCR provider name collision: %s overridden", name)
```

## Comments

**When to Comment:**
- Explain **why**, not **what** (code explains what; comments explain reasoning)
- Complex algorithms or non-obvious fixes (e.g., boundary conditions, workarounds for library bugs)
- **Decision references:** Cite design decisions (e.g., "D-05: Single page blob capture", "V180-ROBUST-02")
- **Invariant documentation:** State preconditions and postconditions for pure functions
- **Edge cases:** Document why a condition is needed (e.g., "堅牢性・T-2-01" = robustness requirement)

**Comment style:**
```python
# Single-line comment for brief notes

"""Multi-line docstring for modules, classes, functions"""

# ══════════════════════════════════════════
# Section markers for logical groupings
# ══════════════════════════════════════════
```

**JSDoc/DocString style:**
- Module docstring: Description + design notes
- Function docstring: One-line summary, then detailed description with parameter/return info
- Format: Google-style docstrings with newline paragraphs

**Example:**
```python
def reconcile_window_start(window_start, current_page, page_size, n_pages):
    """描画直前の窓正規化 + D-11 条件付き追従を 1 純関数に集約する。

    手順:
      1. clamp_window_start で window_start を有効窓の先頭へ寄せる
      2. current_page が窓の外にある場合のみ追従する（D-11）

    D-11 原文：「current_page が表示窓外へ出たら、その窓へ自動切替」。
    """
    ...
```

## Function Design

**Size:** Keep functions under 50 lines when possible; break complex logic into helper functions

**Parameters:**
- Positional parameters for required inputs
- Use `**kwargs` sparingly; prefer explicit parameters for clarity
- Avoid long parameter lists (>4-5 args); use dataclasses or dicts for related parameters

**Return Values:**
- Single return value (tuple if multiple related values, e.g., `(lo, hi)` for range)
- Use `|` for union types (Python 3.10+ style) or `Optional[]` when imported
- Document return type in docstring

**Pure functions:**
- Functions without side effects should be stateless (no self, no global state modifications)
- Examples: `window_bounds()`, `to_global()`, `merge_shortcuts()` in `app.py`, `pagination.py`
- These functions are testable without mocking and can be called from any context

## Module Design

**Exports:**
- Mixin classes implicitly exported by module name
- Helper functions and exceptions explicitly listed for import
- `__all__` not commonly used; rely on naming convention (`_` prefix for private)

**Barrel Files:**
- `pagefolio/dialogs/__init__.py` re-exports dialog classes for convenient imports:
  ```python
  from pagefolio.dialogs import SettingsDialog, PluginDialog, AboutDialog
  ```

## State Management

**Theme colors:**
- Access via `C["BG_DARK"]`, `C["FG_TEXT"]`, etc. (never hardcoded colors)
- `C` is a module-level mutable dict updated at runtime based on theme selection
- Defined in `pagefolio/themes.py` and re-exported via `pagefolio/constants.py`

**Font sizing:**
- Use `self._font(delta)` helper method instead of hardcoding sizes
- Font size persisted in settings file and read at startup

**PDF document reference:**
- Always check `self.doc` before use (may be `None` when no file is open)
- Use `self._check_doc()` in mixin methods to guard operations

**Settings persistence:**
- Settings stored as JSON in `pagefolio_settings.json` (user directory)
- Load at startup: `_load_settings()`
- Save after changes: `_save_settings()`
- API keys never persisted (environment variable or session memory only)

## Architectural Patterns

**Mixin composition:**
- `PDFEditorApp` integrates 8 Mixin classes, each responsible for one functional area
- Reduces monolithic class size while maintaining single instance cohesion
- See `app.py` for full integration

**Pure function layers:**
- `pagination.py`: Window/index conversion (Tk/fitz-free)
- `ocr_pipeline.py`: Producer-consumer queue logic (Tk/fitz-free)
- `md_render.py`: Markdown to span conversion (Tk/fitz-free)
- These enable focused unit testing without mocking UI frameworks

**UI builder pattern:**
- Methods prefixed with `_build_*` construct sections of the UI
- Theme colors passed via `C` dict, fonts via `self._font()`
- Scrollable panels use Canvas + Scrollbar (see `_build_tools_scrollable` in `ui_builder.py`)

**Dialog pattern:**
- Dialogs inherit from `tk.Toplevel`
- Center on parent window (call `self._center(parent)`)
- Return values via instance attributes or callback parameters
- Example: `SettingsDialog.settings` attribute holds form state

---

*Convention analysis: 2026-07-16*
