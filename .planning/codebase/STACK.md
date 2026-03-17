# Technology Stack

**Analysis Date:** 2026-03-17

## Languages

**Primary:**
- Python 3.8+ - Entire application codebase, single-file monolithic design

## Runtime

**Environment:**
- Python 3.8 or later (tested and documented)

**Package Manager:**
- pip (implicit, no lock file)
- Lockfile: Missing (dependencies listed in README and docstring only)

## Frameworks

**Core:**
- Tkinter (Python standard library) - All GUI components, dialogs, styling

**PDF Processing:**
- PyMuPDF (fitz) [version not pinned] - PDF reading, page manipulation, rendering

**Image Handling:**
- Pillow (PIL) [version not pinned] - Image conversion, thumbnail generation, display in Tkinter

**Optional Enhancement:**
- windnd [optional] - Windows drag-and-drop file support (gracefully degrades if missing)

## Key Dependencies

**Critical:**
- `pymupdf` (fitz) - Core PDF manipulation: reading, page rotation, cropping, deletion, merging
- `Pillow` (PIL) - Image rendering for previews and thumbnails

**Optional:**
- `windnd` - Enables Windows explorer file drop onto application window

**Standard Library Usage:**
- `io` - In-memory file operations for PDF rendering
- `json` - Settings persistence (`pagefolio_settings.json`)
- `os` - File path operations, directory management
- `importlib` / `importlib.util` - Plugin system dynamic loading
- `traceback` - Error reporting

## Configuration

**Environment:**
- No environment variables required
- No .env or configuration files beyond runtime settings

**Settings Persistence:**
- `pagefolio_settings.json` (auto-generated at first run)
  - Stored in application directory (same location as `pagefolio.py`)
  - Format: JSON dictionary containing:
    - `theme` (string): "dark" | "light" | "system"
    - `font_size` (integer): 8–16 (pt)
    - `lang` (string): "ja" | "en"

**Build/Launch:**
- `PageFolio起動.bat` - Windows batch script
  - Sets codepage to UTF-8 (65001)
  - Changes directory to script location
  - Runs `python pagefolio.py`
  - Displays error message on failure

## Platform Requirements

**Development:**
- Python 3.8+
- Windows 11 (stated as target OS in CLAUDE.md)
- Tkinter support (included with Python on most distributions)

**Production/Distribution:**
- Windows 11 (primary target)
- Python 3.8+ installation with tkinter and pip
- Access to PyPI for dependency installation
- No compiled binaries or exe distribution currently configured

**Deployment Notes:**
- Application is single `.py` file (no package structure)
- Settings file auto-generated at runtime
- Plugins directory (`plugins/`) optional but supported
- Automatic dependency installation mentioned in README but not implemented in codebase (users must run `pip install pymupdf pillow` manually)

---

*Stack analysis: 2026-03-17*
