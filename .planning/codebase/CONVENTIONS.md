# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

**Files:**
- Single-file monolithic structure: `pagefolio.py` (main application)
- Plugin files: `{name}.py` stored in `plugins/` directory (e.g., `plugins/page_info.py`)
- Configuration files: `pagefolio_settings.json` (runtime-generated, not committed)

**Functions:**
- Private/internal methods: `_method_name` (underscore prefix)
  - Example: `_save_undo()`, `_crop_page()`, `_build_ui()`
- Public methods: `method_name` (no prefix, rarely used in this codebase)
- Constant helper functions at module level: `_snake_case` (e.g., `_load_settings()`, `_apply_theme()`, `_get_plugins_dir()`)

**Variables:**
- Instance attributes: `self.attr_name` (simple camelCase or snake_case)
  - Example: `self.doc` (current PDF document), `self.current_page` (page index)
  - Private state: `self._undo_stack`, `self._redo_stack`, `self._dnd_src_idx`
  - UI references: `self.thumb_canvas`, `self.preview_canvas`, `self.zoom_label`
- Module-level globals: `UPPERCASE` for constants, `lowercase` for runtime state
  - Example: `THEMES` (dict), `LANG` (dict), `C` (current theme colors), `_current_font_size` (runtime state)
- Loop variables: `i` (page index), `e` (exception), `w` (widget)

**Types & Classes:**
- Class names: `PascalCase` (e.g., `PDFEditorApp`, `SettingsDialog`, `PluginManager`, `MergeOrderDialog`)
- Plugin base class: `PDFEditorPlugin` (inherited by all plugins)

## Code Style

**Formatting:**
- No linter configured (no `.eslintrc`, `.prettierrc`, or similar)
- Indentation: 4 spaces (Python standard)
- Line length: Observed ~80-120 character average (not enforced)
- Trailing whitespace: Not observed, implicit style is clean
- No type hints used (Python 3.8+ available but not utilized)

**Linting:**
- No linting framework detected
- Convention enforcement relies on developer discipline and code review

## Import Organization

**Order:**
1. Standard library imports (tkinter, fitz, PIL, io, os, json, importlib, traceback)
2. Module-level constants (THEMES, LANG, PLUGINS_DIR)
3. Module-level functions (setup functions like `_load_settings`, `_apply_theme`)
4. Class definitions (plugin base class, managers, app classes)

**Path Aliases:**
- Not used in this codebase (single-file structure)
- Plugin system uses dynamic module loading: `importlib.util.spec_from_file_location()`

**Example from line 10-19:**
```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import fitz  # pymupdf
from PIL import Image, ImageTk
import io
import os
import json
import importlib
import importlib.util
import traceback
```

## Error Handling

**Patterns:**
- Generic `try-except Exception:` blocks catching all exceptions (permissive approach)
  - Used for operations that may fail gracefully: file I/O, PDF operations, plugin loading
  - Example (line 1076-1077):
    ```python
    try:
        # ... PDF merge operation
    except Exception as e:
        messagebox.showerror(self._t("err_title"), str(e))
    ```
- Nested try-except for fallback strategies (e.g., save with incremental fallback to full save, line 1112-1118):
  ```python
  try:
      try:
          self.doc.save(self.filepath, incremental=True,
                        encryption=fitz.PDF_ENCRYPT_KEEP)
      except Exception:
          tmp = self.filepath + ".tmp"
          self.doc.save(tmp)
          os.replace(tmp, self.filepath)
  except Exception as e:
      messagebox.showerror(...)
  ```
- Pre-condition checks using guard clauses:
  ```python
  def _crop_page(self):
      if not self._check_doc():  # Returns bool, shows messagebox if false
          return
      if not self.crop_rect:
          messagebox.showinfo(...)
          return
  ```

**Error Communication:**
- User-facing errors: `messagebox.showerror()` with translated key from `LANG` dict
- Stack traces: Printed to console via `traceback.print_exc()` (plugin loading, line 553)
- Status messages: `self._set_status(msg)` for non-error feedback (success, undo/redo, file operations)

## Logging

**Framework:** `print()` via `traceback.print_exc()` for errors; no logging library

**Patterns:**
- Exception traces: Line 553, 562, 573, 581, 599, 1875 in plugin system
  ```python
  except Exception:
      traceback.print_exc()
  ```
- Status messages to UI: `self._set_status(self._t("key"))`
- Messagebox info/warning/error: `messagebox.showinfo()`, `messagebox.showwarning()`, `messagebox.showerror()`

## Comments

**When to Comment:**
- Section headers for major functional areas (e.g., line 667, 720, 795, 846, 887, 1858)
  ```
  # ─────────────────────────────────────────
  def _build_styles(self):
  ```
- Issue/ticket references for notable fixes (e.g., line 630, 651, 654, 706)
  ```python
  self.thumb_cache = {}       # サムネイルキャッシュ (#7)
  # WM_DELETE_WINDOW (#5)
  # キーボードショートカット (#12)
  ```
- Inline explanations for non-obvious logic (e.g., line 1066, 1276, 1287)
  ```python
  self.filepath = None  # 結合結果なので保存先なし
  EPS = 0.01
  new_rect = fitz.Rect(  # CropBox を MediaBox の範囲内に厳密にクランプ
  ```

**JSDoc/TSDoc:**
- Docstrings used for method documentation (Python convention)
- Format: Triple-quoted strings immediately after method signature
- Example (line 1049, 1053, 1079, 1080):
  ```python
  def _open_multiple_pdfs(self, paths):
      """複数PDFを結合して1つのドキュメントとして開く"""

  def _do_open_merged(self, ordered_paths):
      """結合順ダイアログ確定後、結合して開く"""
  ```
- Docstrings describe **what** the method does in Japanese; no parameter/return type documentation

## Function Design

**Size:** Functions range from 5-100+ lines
- Short utility methods: 5-15 lines (e.g., `_check_doc()`, `_get_targets()`, `_set_status()`)
- Medium methods: 20-50 lines (e.g., `_crop_page()`, `_open_pdf_path()`)
- Large methods: 50-100+ lines (e.g., `_build_ui()`, `_crop_drag_move()`)
- Longest method: `_build_tools()` (98 lines) — constructs entire tool panel

**Parameters:**
- Minimal: Most methods take only `self` and event parameters
- Callbacks: Pass `callback` function parameter (e.g., `MergeOrderDialog(..., callback, ...)`)
- Variable args: Rarely used; prefer named parameters

**Return Values:**
- Boolean returns for check methods (e.g., `_check_doc()` returns True/False)
- None for most state-changing methods
- No explicit returns for UI-building methods
- Dictionary/list returns for internal state retrieval (e.g., `_get_targets()` returns list)

## Module Design

**Exports:**
- Single executable entry point: `if __name__ == "__main__":` (not shown in excerpts, but standard)
- Main class: `PDFEditorApp` is instantiated with a Tk root
- Dialog classes: `SettingsDialog`, `MergeOrderDialog`, `AboutDialog`, `PluginDialog` created on-demand
- Plugin base: `PDFEditorPlugin` exported for external plugins to inherit from

**Barrel Files:**
- Not used (single-file structure precludes this pattern)
- Plugins use dynamic module loading instead of explicit imports

**Class Responsibilities (SOLID):**
- `PDFEditorApp`: Main UI + document operations + state management
- `SettingsDialog`: Theme/font configuration UI
- `MergeOrderDialog`: PDF reordering UI (used for open, insert, merge)
- `PluginManager`: Plugin discovery, loading, lifecycle, event dispatch
- `PDFEditorPlugin`: Interface/contract for external plugins

## Language & Localization

**Patterns:**
- All user-facing text stored in `LANG` dictionary with `"ja"` and `"en"` keys
- Retrieval via `self._t(key)` helper method (line 1847-1849):
  ```python
  def _t(self, key):
      """現在の言語でテキストを返すヘルパー"""
      return LANG[self.lang].get(key, LANG["ja"].get(key, key))
  ```
- Language toggle via `self._toggle_lang()` (line 1851-1856) switches UI entirely
- Settings persist language choice to `pagefolio_settings.json`

## Theme Management

**Patterns:**
- Theme dictionary `C` updated globally via `_apply_theme()` (line 406-409)
- All color references use `C["KEY"]` notation, never hardcoded hex values in widget code
- Example (line 672):
  ```python
  style.configure("TFrame", background=C["BG_DARK"])
  ```
- Three theme options: `"dark"`, `"light"`, `"system"` (Windows-specific detection)
- Theme applied at startup and on settings change via `_apply_theme()` + UI rebuild

---

*Convention analysis: 2026-03-17*
