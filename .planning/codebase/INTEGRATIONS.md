# External Integrations

**Analysis Date:** 2026-03-17

## APIs & External Services

**None** - PageFolio has no external API integrations or cloud service dependencies.

## Data Storage

**Databases:**
- None (not applicable for this application)

**File Storage:**
- Local filesystem only
  - Input: User selects PDF files via file dialog or drag-and-drop
  - Output: Saves modified PDFs to user-selected locations
  - Settings: `pagefolio_settings.json` stored in application directory

**Caching:**
- Thumbnail cache (in-memory)
  - Stored in `PDFEditorApp.thumb_cache` dictionary
  - Generated from PDF pages using `fitz.Matrix(0.22, 0.22)` scaling
  - Cache invalidated via `_invalidate_thumb_cache()` method when document changes
  - Location: `pagefolio.py` lines 487, 1619–1631

**Configuration Files:**
- `pagefolio_settings.json`
  - Path: Same directory as `pagefolio.py`
  - Accessed via `_get_settings_path()` at `pagefolio.py:359`
  - Loaded on app startup via `_load_settings()` at `pagefolio.py:363`
  - Saved on settings changes via `_save_settings()` at `pagefolio.py:378`

## Authentication & Identity

**Not applicable** - No user authentication or identity system.

## Monitoring & Observability

**Error Tracking:**
- None (no external error reporting)

**Logs:**
- Console/stderr only
- Error tracebacks printed to console via `traceback` module
- No persistent logging

**Debugging:**
- Plugin loading exceptions caught and displayed in Plugin Manager dialog

## CI/CD & Deployment

**Hosting:**
- GitHub repository (`https://github.com/mistyura/PageFolio`)
- No cloud deployment

**CI Pipeline:**
- None detected in codebase

**Distribution:**
- Manual distribution as `.zip` with `pagefolio.py`, batch file, and documentation
- PyInstaller mentioned as future candidate in CLAUDE.md (not implemented)

## Environment Configuration

**Required env vars:**
- None

**Optional env vars:**
- None detected

**Secrets location:**
- No secrets management (application is local/offline)

## Webhooks & Callbacks

**Incoming:**
- File drag-and-drop handler via `windnd` (Windows optional feature)
  - Implementation: `_setup_file_drop()` at `pagefolio.py:2375`
  - Graceful degradation if `windnd` not installed

**Outgoing:**
- None

## Plugin System

**Plugin Architecture:**
- Plugin base class: `PDFEditorPlugin` (defined in `pagefolio.py:430–445`)
- Plugin directory: `plugins/` (adjacent to `pagefolio.py`)
- Discovery: `PluginManager.discover_plugins()` scans `.py` files in `plugins/`
- Loading: Dynamic module import via `importlib.util.spec_from_file_location()`
- Module registration: Plugins imported as `pdf_editor` for backward compatibility (`pagefolio.py:542`)

**Sample Plugin:**
- `plugins/page_info.py` - Displays page size, rotation, cropbox information
  - Base class: `PDFEditorPlugin`
  - Implements hooks: `on_file_open()`, `on_page_change()`, `on_page_rotate()`, `on_page_crop()`, `on_page_delete()`
  - Location: `/c/Users/shdwf/work/project/PageFolio/plugins/page_info.py`

**Plugin Hooks:**
The plugin system supports callback hooks at:
- `on_file_open(app, path)` - File opened
- `on_page_change(app, page_index)` - Current page changed
- `on_page_rotate(app, pages, degrees)` - Pages rotated
- `on_page_crop(app, page_index)` - Page cropped
- `on_page_delete(app, pages)` - Pages deleted

## Theme & Language System

**Theming:**
- Built-in color themes defined in `THEMES` dictionary (`pagefolio.py:23–56`)
  - Themes: "dark", "light"
  - System theme auto-detection via `SettingsDialog._get_system_theme()` (not found in current code)
  - Active theme colors exposed via module-level `C` dictionary
  - Persistence: Stored in `pagefolio_settings.json` as `"theme"` key

**Internationalization:**
- Language dictionary: `LANG` (`pagefolio.py:62–349`)
- Supported languages: Japanese ("ja"), English ("en")
- Text access via `_t(key)` method (translates to `LANG[self.lang][key]`)
- Default language: Japanese ("ja")
- Persistence: Stored in `pagefolio_settings.json` as `"lang"` key

---

*Integration audit: 2026-03-17*
