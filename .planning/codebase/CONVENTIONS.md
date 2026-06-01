# Coding Conventions

**Analysis Date:** 2026-06-01

## Naming Conventions

**Files:**
- Modules use `snake_case.py` (e.g., `file_ops.py`, `ui_builder.py`, `page_ops.py`)
- Test files use `test_<module>.py` prefix (e.g., `test_pdf_ops.py`, `test_plugins.py`)

**Classes:**
- PascalCase (e.g., `PDFEditorApp`, `UIBuilderMixin`, `FileOpsMixin`, `AboutDialog`)
- Mixin classes end with `Mixin` suffix (e.g., `UIBuilderMixin`, `ViewerMixin`, `DnDMixin`)
- Dialog classes end with `Dialog` suffix (e.g., `AboutDialog`, `SettingsDialog`)
- Test classes use `Test<FeatureName>` prefix (e.g., `TestLoadSettings`, `TestPdfOpen`)

**Methods:**
- `_` prefix for internal/private methods (e.g., `_build_styles`, `_refresh_all`, `_set_status`)
- Public API methods use plain names (e.g., `discover_plugins`, `load_plugin`, `fire_event`)
- Tkinter event handlers conventionally begin with `_on_` or `_do_` (e.g., `_do_merge`, `_do_insert`)

**Variables:**
- `snake_case` throughout (e.g., `current_page`, `selected_pages`, `thumb_cache`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `APP_VERSION`, `THEMES`, `LANG`, `SETTINGS_FILE`)
- Theme colors accessed via `C["KEY"]` dict, never hardcoded hex strings

## Code Style

**Line Length:** 88 characters (Ruff default)

**Formatter:** Ruff (`ruff format .`)

**Linter:** Ruff with rules E, F, W, I, S, B
- `tests/**/*.py` exempt from S101 (assert allowed in tests)
- No bare `except:` — always `except Exception as e:`
- No `# type: ignore` without prior approval

**String Quotes:** Double quotes (Ruff default)

**Imports:** Organized by Ruff (rule I — isort-compatible):
1. Standard library
2. Third-party (e.g., `fitz`, `PIL`)
3. Local package (`from pagefolio.constants import C`)

## Module Organization

Each module opens with:
```python
# PageFolio - PDF Page Organizer
# Copyright (c) 2026 mistyura
# Released under the MIT License
"""<Module description in Japanese>"""
```

Modules declare a `logger` where logging is needed:
```python
import logging
logger = logging.getLogger(__name__)
```

Mixin modules define one class (e.g., `UIBuilderMixin`) containing related methods only. `app.py` combines all mixins via multiple inheritance:
```python
class PDFEditorApp(UIBuilderMixin, FileOpsMixin, PageOpsMixin, ViewerMixin, DnDMixin, tk.Tk):
```

Dialogs in `pagefolio/dialogs.py` are self-contained `tk.Toplevel` subclasses. Each dialog:
- Takes `parent`, font function, and `lang` parameter
- Sets `self.grab_set()` for modal behavior
- Centers itself relative to parent window

## Error Handling Patterns

**Standard pattern** — catch, log (or show dialog), return/pass:
```python
try:
    ...
except Exception as e:
    logger.error("context: %s", e)
    messagebox.showerror(self._t("err_title"), str(e))
    return
```

**Silent fallback** — used in settings/plugin loading when errors should not surface to user:
```python
try:
    ...
except Exception as e:
    logger.warning("...: %s", e)
    return
```

**Guard pattern** for doc existence before PDF operations:
```python
if not self._check_doc():
    return
```
`_check_doc()` is defined in `pagefolio/app.py` and shows an info dialog when `self.doc` is `None`.

**Forbidden:**
- Bare `except:` without exception type
- Silencing exceptions without at minimum a `logger` call

## UI Patterns

**Button styles** (defined in `pagefolio/ui_builder.py`, `_build_styles`):
- `"TButton"` — standard operation
- `"Accent.TButton"` — primary/important action
- `"Danger.TButton"` — destructive action (delete, quit)
- `"CropOn.TButton"` — trim mode active state

**Theme colors** — always via `C["KEY"]`, never hardcoded hex:
```python
from pagefolio.constants import C
bg=C["BG_DARK"]
fg=C["ACCENT"]
```

**Font sizes** — never hardcoded; use `self._font(delta)` helper:
```python
font=self._font(0)        # base size
font=self._font(2)        # base + 2
font=self._font(-1, weight="bold")
```
`_font` is defined in `pagefolio/app.py` and clamps minimum size to 7.

**Widget layout** — `pack()` used in dialogs; `grid()` used in tool panels; `PanedWindow` for main split layout.

**Scrollable right panel** — built via `_build_tools_scrollable` in `pagefolio/ui_builder.py` using a Canvas + inner Frame.

## Logging & Status

**User-visible status** — use `self._set_status(msg)` to update header label (defined in `pagefolio/app.py:204`):
```python
self._set_status(self._t("status_saved"))
```

**Localized strings** — always via `self._t("key")` which resolves from `LANG[lang]` dict in `pagefolio/constants.py`.

**Error dialogs:**
```python
messagebox.showerror(self._t("err_title"), str(e))      # recoverable error
messagebox.showwarning(self._t("warn_title"), msg)       # warning
messagebox.showinfo(self._t("info_title"), msg)          # info
messagebox.askyesno(self._t("confirm_title"), question)  # confirmation
```

**Developer logging** — `logging.getLogger(__name__)` per module; level INFO for normal operations, WARNING/ERROR for exceptions.

---

*Convention analysis: 2026-06-01*
