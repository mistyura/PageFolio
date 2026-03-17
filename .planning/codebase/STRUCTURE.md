# Codebase Structure

**Analysis Date:** 2026-03-17

## Directory Layout

```
PageFolio/
├── pagefolio.py               # Main application (2,397 lines) - all UI, logic, plugins
├── plugins/                   # Plugin directory (auto-discovered at runtime)
│   └── page_info.py           # Sample plugin - displays page metadata
├── PageFolio起動.bat          # Windows batch launcher
├── README.md                  # User-facing feature overview
├── CLAUDE.md                  # AI developer instructions (this file guides Claude)
├── 開発履歴.md                # Japanese development changelog
├── LICENSE                    # MIT License
└── pagefolio_settings.json    # User settings (generated at runtime)
```

## Directory Purposes

**Root Directory:**
- Purpose: Application entry point and documentation
- Contains: Main executable, launcher, licenses, development notes
- Key files: `pagefolio.py` (core), `PageFolio起動.bat` (Windows launcher)

**plugins/ Directory:**
- Purpose: User/developer extensible plugin directory
- Contains: Python modules inheriting from `PDFEditorPlugin`
- Generated: At runtime, scanned by `PluginManager` for `.py` files
- Committed: Yes (includes sample `page_info.py` template)
- Discovery mechanism: `PluginManager._scan_plugins()` walks `plugins/` directory, imports each `.py` file

## Key File Locations

**Entry Points:**

- `pagefolio.py` (lines 2380-2397): Application main entry
  - Creates Tk root window, instantiates `PDFEditorApp(root)`, starts `root.mainloop()`
  - Executed via `python pagefolio.py` or batch file `PageFolio起動.bat`

- `plugins/page_info.py` (lines 1-69): Sample plugin demonstrating plugin API
  - Extends `PDFEditorPlugin` base class
  - Shows how to hook into lifecycle (`build_ui`, `on_file_open`, `on_page_change`, etc.)

**Configuration:**

- `pagefolio_settings.json`: User preferences JSON file (auto-created on first run)
  - Location: Same directory as `pagefolio.py`
  - Keys: `"theme"` (dark/light/system), `"font_size"` (8-16), `"lang"` (ja/en), `"disabled_plugins"` (list)
  - Loaded via `_load_settings()` (line 363); saved via `_save_settings()` (line 378)

**Core Logic:**

- `pagefolio.py` (lines 607-1930): `PDFEditorApp` class - primary application controller
  - Lines 610-646: `__init__` - Initialize state, settings, UI, keyboard bindings
  - Lines 668-717: `_build_styles` - Tkinter theme configuration
  - Lines 720-756: `_build_ui` - Main window layout (header, left/center/right panes)
  - Lines 758-793: `_build_thumb_panel` - Thumbnail panel with Canvas
  - Lines 795-850+: `_build_preview` - PDF preview area with zoom/nav controls
  - Lines 850+: `_build_tools_scrollable` - Right panel scrollable tools
  - Lines 1038-1140: File operations (`_open_file`, `_save_file`, `_save_as`, `_open_pdf_path`)
  - Lines 1144-1180: Page operations (`_rotate_selected`, `_delete_selected`)
  - Lines 1190-1330: Crop operations (`_toggle_crop_mode`, `_crop_drag_*`, `_crop_page`, `_crop_reset`)
  - Lines 1345-1410: Insert/Merge operations (`_insert_from_file`, `_merge_pdf`, `_do_merge`)
  - Lines 1415-1490: Display (`_show_preview`, `_build_thumbnails`, `_add_thumb`)
  - Lines 1528-1820: Utilities (`_refresh_all`, `_get_targets`, `_check_doc`, `_update_doc_buttons_state`)
  - Lines 1782-1820: Drag & Drop (`_dnd_start_ghost`, `_dnd_move_ghost`, `_dnd_drop`, `_dnd_show_indicator`)
  - Lines 998-1030: Undo/Redo (`_save_undo`, `_undo`, `_redo`, `_restore_state`, `_get_state`)

- `pagefolio.py` (lines 483-605): `PluginManager` class - plugin lifecycle
  - Lines 483-605: Load, enable/disable, event dispatch to plugins

- `pagefolio.py` (lines 431-480): `PDFEditorPlugin` base class - plugin interface
  - Defines expected methods: `build_ui(app, parent)`, `on_file_open(app, path)`, etc.

**Testing:**

- None (no test files in codebase; manual testing via running application)

**Theme & Language Configuration:**

- `pagefolio.py` (lines 22-59): `THEMES` global dict - Color palette definitions
  - Dark theme: `THEMES["dark"]` with 15+ color keys (BG_DARK, ACCENT, SUCCESS, etc.)
  - Light theme: `THEMES["light"]` with corresponding colors
  - Runtime global `C = dict(THEMES["dark"])` updated by `_apply_theme(name)`

- `pagefolio.py` (lines 61-355): `LANG` global dict - Internationalization strings
  - `LANG["ja"]` - Japanese labels/messages (100+ keys)
  - `LANG["en"]` - English labels/messages (100+ keys)
  - Access via `self._t(key)` helper method (line 1847)

**Dialogs:**

- `pagefolio.py` (lines 1932-1980): `AboutDialog` - Version/license information
- `pagefolio.py` (lines 1980-2074): `SettingsDialog` - Theme and font size configuration
- `pagefolio.py` (lines 2074-2228): `PluginDialog` - Plugin management UI
- `pagefolio.py` (lines 2230-2397): `MergeOrderDialog` - Confirm/reorder PDF merge sequence

**Utility Functions:**

- `pagefolio.py` (lines 359-398): Settings I/O
  - `_get_settings_path()` - Resolve `pagefolio_settings.json` path
  - `_load_settings()` - Load JSON with defaults fallback
  - `_save_settings(settings)` - Persist settings to JSON
  - `_detect_system_theme()` - Query Windows registry for system theme
  - `_apply_theme(theme_name)` - Update global `C` dict with resolved theme colors
  - `_resolve_theme(theme_name)` - Resolve "system" → actual dark/light via `_detect_system_theme()`

## Naming Conventions

**Files:**

- `.py` files: Snake case (`pagefolio.py`, `page_info.py`)
- Settings file: JSON with key names in `snake_case` (`pagefolio_settings.json`)
- Batch launcher: Japanese description (`PageFolio起動.bat`)

**Classes:**

- PascalCase: `PDFEditorApp`, `PluginManager`, `PDFEditorPlugin`, `SettingsDialog`, `MergeOrderDialog`
- Suffix with dialog type: `Dialog`, `Manager`, `Plugin`

**Methods:**

- Private methods (internal to class): Prefixed with `_` e.g., `_open_file`, `_rotate_selected`, `_save_undo`
- Public methods: None (single-file app, no external API)
- UI builders: Prefixed `_build_*` (e.g., `_build_ui`, `_build_styles`, `_build_thumb_panel`)
- Event handlers: Prefixed `_*_*` describing action (e.g., `_crop_drag_start`, `_dnd_drop`, `_single_click`)
- Display updates: Prefixed `_show_*` or `_refresh_*` (e.g., `_show_preview`, `_refresh_all`)

**Variables:**

- Instance state: Lowercase with underscore (e.g., `self.doc`, `self.current_page`, `self._undo_stack`)
- Local widget references: Lowercase (e.g., `header`, `toolbar`, `preview_canvas`)
- Constants (global): UPPERCASE (e.g., `THEMES`, `LANG`, `MAX_UNDO`, `SETTINGS_FILE`)
- Theme colors: Via global `C` dict accessed as `C["BG_DARK"]`, `C["ACCENT"]`

**Language Keys:**

- Underscore-separated: `"status_initial"`, `"btn_open"`, `"err_crop_msg"`
- Section prefixes: `status_*`, `btn_*`, `err_*`, `info_*`, `warn_*`, `lbl_*`, `sec_*`, `crop_*`, `dlg_*`
- Placeholders in format strings: `{name}`, `{count}`, `{path}` for `.format()` substitution

## Where to Add New Code

**New Feature (Page Operation):**

1. **Primary code:** Add method to `PDFEditorApp` class
   - Location: `pagefolio.py` around line 1144-1410 (existing page op methods)
   - Pattern:
     - Start with `if not self._check_doc(): return`
     - Call `self._save_undo()` before modification
     - Modify `self.doc` pages using fitz API
     - Call `self._refresh_all()` to redraw
     - Fire plugin event: `self.plugin_manager.fire_event("on_page_*", self, ...)`
     - Display status: `self._set_status(self._t("status_*"))`

2. **Tests:** Manual testing only (no automated test framework)
   - Launch `python pagefolio.py`
   - Verify feature works with sample PDFs

3. **UI Integration:**
   - Add button in `_build_tools` (line 850+) or appropriate tool section
   - Bind button to method: `ttk.Button(parent, command=self._your_method)`
   - Add language strings to `LANG["ja"]` and `LANG["en"]`

**New Dialog:**

1. **Implementation:** Create new `tk.Toplevel` subclass in `pagefolio.py`
   - Location: After line 2230, before or after existing dialogs
   - Pattern:
     ```python
     class YourDialog(tk.Toplevel):
         def __init__(self, parent, ..., callback):
             super().__init__(parent)
             self.callback = callback
             self.title(self._t("title_key"))
             # Build UI with _font(), _t() helpers

         def _apply(self):
             self.callback(result)
             self.destroy()
     ```
   - Use `self._font(delta)` and `self._t(key)` for consistency

2. **Caller Integration:**
   - From `PDFEditorApp` method, instantiate: `dialog = YourDialog(self.root, callback=self._your_callback)`
   - Callback receives result and updates app state

**New Plugin:**

1. **Create file:** `plugins/your_plugin.py`
   - Inherit from `PDFEditorPlugin`
   - Override `name`, `version`, `description`, `author` class attributes
   - Implement `build_ui(app, parent)` to add custom panel to right toolbar
   - Implement event handlers: `on_file_open(app, path)`, `on_page_change(app, page_index)`, etc.
   - Use `app._font()`, `app._t()`, theme colors from `from pdf_editor import C`

2. **Example Structure:**
   ```python
   from pdf_editor import PDFEditorPlugin, C

   class YourPlugin(PDFEditorPlugin):
       name = "Plugin Name"
       version = "1.0.0"
       description = "What it does"
       author = "Your Name"

       def build_ui(self, app, parent):
           label = tk.Label(parent, text="Custom Info",
                           bg=C["BG_CARD"], fg=C["TEXT_SUB"])
           label.pack()

       def on_page_change(self, app, page_index):
           # Update when page changes
           pass
   ```

3. **Discovery:** Automatically loaded by `PluginManager._scan_plugins()` at startup

**Utilities & Helpers:**

- Shared font: Use `self._font(delta)` with delta as offset from base size
- Localized text: Use `self._t(key)` to look up from `LANG[self.lang]`
- Theme colors: Access via global `C` dict (e.g., `C["ACCENT"]`)
- Status messages: Call `self._set_status(msg)` to display in header

## Special Directories

**plugins/ Directory:**

- Purpose: Runtime-discovered plugin system
- Generated: Yes (auto-created by app if missing)
- Committed: Yes (includes `page_info.py` template)
- Scan mechanism: `PluginManager._scan_plugins()` (line 515) walks directory, imports `.py` files
- Configuration: Disabled plugins listed in `pagefolio_settings.json` under `"disabled_plugins"` key
- Plugin manager caches loaded modules in `self._plugin_modules` dict

---

*Structure analysis: 2026-03-17*
