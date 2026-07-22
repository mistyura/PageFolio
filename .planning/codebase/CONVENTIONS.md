# Coding Conventions

**Analysis Date:** 2026-07-22

## Naming Patterns

**Files:**
- Module files use lowercase with underscores: `file_ops.py`, `ui_builder.py`, `ocr_providers.py`
- Test files prefixed with `test_`: `test_ocr.py`, `test_pagination.py`, `test_pdf_ops.py`
- Mixin classes named `[Domain]Mixin`: `UIBuilderMixin`, `FileOpsMixin`, `PageOpsMixin`

**Functions:**
- Public functions: lowercase with underscores (`window_bounds()`, `save_with_password()`)
- Private/internal functions: underscore prefix (`_build_styles()`, `_on_thumb_dnd_drop()`)
- Pure functions (Tk/fitz-independent): documented with "純関数" in docstring and reference to tracking IDs (e.g., "D-10", "V171-TEST-01")

**Variables:**
- Instance attributes: `self.doc`, `self.current_page`, `self.selected_pages` (all lowercase, underscores for privacy)
- Private attributes: underscore prefix (`self._undo_stack`, `self._redo_stack`, `self._pending_click`)
- Module-level constants: UPPERCASE (`MAX_UNDO`, `SETTINGS_FILE`, `PAGE_SIZE_MAX`)
- Local variables: lowercase with underscores (`window_start`, `page_size`, `local_pos`)

**Types:**
- Classes: PascalCase (`PDFEditorApp`, `PDFPasswordError`, `UIBuilderMixin`)
- Custom exceptions: PascalCase ending in `Error` (`PDFPasswordError`)
- Theme dictionary keys: UPPERCASE with underscores (`C["BG_DARK"]`, `C["TEXT_MAIN"]`, `C["ACCENT"]`)

## Code Style

**Formatting:**
- Tool: `ruff` (ruff format)
- Line length: 88 characters (configured in `pyproject.toml`)
- Indentation: 4 spaces

**Linting:**
- Tool: `ruff` (ruff check)
- Selected rules: E (errors), F (Pyflakes), W (warnings), I (isort import sorting), S (security), B (flake8-bugbear)
- All rules fixable (`fixable = ["ALL"]`)
- Exception: S101 (assert statements) ignored in `tests/**/*.py`

**Command:**
```bash
ruff check . && ruff format .
```

## Import Organization

**Order:**
1. Standard library imports (`import os`, `from collections import deque`)
2. Third-party imports (`import tkinter as tk`, `import fitz`, `from PIL import Image`)
3. Local pagefolio imports (`from pagefolio.constants import ...`, `from pagefolio.dialogs import ...`)

**Path Aliases:**
- No path aliases used
- Full module paths referenced: `pagefolio.constants`, `pagefolio.dialogs`, `pagefolio.ocr_providers`

**Pattern Example:**
```python
import logging
import os
from tkinter import messagebox

import fitz
from PIL import Image

from pagefolio.constants import C, SUPPORTED_EXTENSIONS
from pagefolio.settings import _load_settings
```

## Error Handling

**Patterns:**
- Always use `except Exception as e:` (bare `except:` is forbidden per CLAUDE.md)
- Exceptions are caught and logged rather than silently ignored
- User-visible errors use `messagebox.showerror()` for dialogs
- Plugin callbacks wrapped individually to prevent cascade failures
- File operations may raise custom exceptions (e.g., `PDFPasswordError`)

**Examples from codebase:**
```python
# Logging errors
try:
    b.state(state)
except Exception as e:
    logger.debug("編集ボタン状態変更失敗: %s", e)

# User-visible errors via messagebox
except Exception as e:
    messagebox.showerror(self._t("error_title"), str(e))

# Custom exception definition
class PDFPasswordError(Exception):
    """パスワード付き PDF の認証がキャンセル/失敗したことを表す例外。"""
```

## Logging

**Framework:** Python's standard `logging` module

**Setup pattern (in `app.py`):**
```python
logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)
```

**Patterns:**
- One logger per module: `logger = logging.getLogger(__name__)`
- Log level: WARNING (used for user-impacting issues)
- DEBUG level used for development debugging (e.g., "編集ボタン状態変更失敗")
- Do not log environment variable contents or secrets

## Comments

**When to Comment:**
- Functions with complex logic include docstrings (see below)
- Inline comments explain non-obvious "why" (not "what") decisions
- References to tracking/issue IDs (e.g., "D-10", "V171-TEST-01") appear in docstrings for traceability
- Comments about code limitations, workarounds, or design decisions are placed above the code

**Docstring Pattern (Multi-line for complex functions):**
```python
def reconcile_window_start(window_start, current_page, page_size, n_pages):
    """描画直前の窓正規化 + D-11 条件付き追従を 1 純関数に集約する。

    手順:
      1. clamp_window_start で window_start を有効窓の先頭へ寄せる
      2. current_page が正規化後の窓 [lo, hi) の **外** に出ている場合のみ
         window_for_page(current_page, page_size) でその窓へ追従する（D-11）。

    D-11 原文（02-RESEARCH.md:21）: 「current_page が表示窓外へ出たら、その窓へ
    自動切替」。追従は **窓外条件付き** であり無条件ではない。
    n_pages<=0 or page_size<=0 では 0 を返す（堅牢性・T-2-01）。
    """
```

**Docstring Pattern (One-liner for simple functions):**
```python
def to_global(local_pos, window_start):
    """窓ローカル位置を全ページインデックスへ換算する（D-06）。"""
    return local_pos + window_start
```

## Function Design

**Size:** Functions remain focused on single responsibilities. Complex logic is broken into pure functions (especially for Tk/fitz-independent calculations)

**Parameters:**
- Parameters ordered: required first, then optional (with defaults)
- Type hints not used (Python 3.8 compatibility)
- Docstrings describe parameter meanings when non-obvious

**Return Values:**
- Functions return early on error conditions
- `None` used explicitly when no meaningful return value
- Tuple unpacking used for multiple return values (e.g., `lo, hi = window_bounds(...)`)

**Example:**
```python
def export_page_image(
    page, out_path, target_long_px, fmt="png", jpg_quality=DEFAULT_EXPORT_JPG_QUALITY
):
    """fitz.Page を画像ファイルとして保存する。

    page.rect（CropBox・回転反映後の表示矩形）の長辺が target_long_px に
    なるよう倍率を計算してレンダリングする。
    """
    scale = compute_export_scale(page.rect.width, page.rect.height, target_long_px)
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    if fmt == "jpg":
        pix.save(out_path, jpg_quality=jpg_quality)
    else:
        pix.save(out_path)
```

## Module Design

**Exports:**
- Mixin classes exported via `from pagefolio.dialogs import PluginDialog, SettingsDialog` pattern
- Re-exports in `__init__.py` maintain backward compatibility
- `pagefolio.constants` re-exports `THEMES` and `C` from `themes.py`, `LANG` from `lang.py`

**Barrel Files:**
- `pagefolio/dialogs/__init__.py` re-exports all dialog classes
- `pagefolio/ocr_providers/__init__.py` provides provider registry (carefully structured to avoid circular imports)

**Mixin Pattern:**
- Mixins inherit from no base class (only mixed into `PDFEditorApp`)
- Each Mixin focuses on one functional area (FileOpsMixin, UIBuilderMixin, etc.)
- PDFEditorApp combines all Mixins in MRO order to access their methods
- Example from `app.py`:
```python
class PDFEditorApp(
    UIBuilderMixin,
    FileOpsMixin,
    PageOpsMixin,
    RedactOpsMixin,
    ViewerMixin,
    DnDMixin,
    OCRMixin,
    PrintOpsMixin,
):
```

## State Management Conventions

**Theme Dictionary (`C`):**
- Always use `C["BG_DARK"]` etc. rather than hardcoded hex values
- Never reference colors directly as strings
- Theme colors defined in `pagefolio/themes.py`
- Applied at runtime via `_apply_theme()` in `settings.py`

**Font Size (`self._font()`):**
- Never hardcode font sizes
- Use `self._font(delta)` helper for size + delta from base
- Base font size stored in `self.font_size` (8-16 range)

**Button Styling:**
- Normal operations: `"TButton"`
- Primary actions: `"Accent.TButton"`
- Destructive operations (delete/exit): `"Danger.TButton"`
- Crop mode active: `"CropOn.TButton"`

---

*Convention analysis: 2026-07-22*
