# Technology Stack

**Analysis Date:** 2026-07-03

## Languages

**Primary:**
- Python 3.8+ - All application code, CLI entry points, GUI framework integration

**Build Output:**
- Windows executable (.exe) - Generated via PyInstaller (onedir format)

## Runtime

**Environment:**
- Python 3.8+ with pip package manager
- Virtual environment: `venv/` (Windows-specific)
- Lockfile: `requirements.txt` with pinned versions

**Package Manager:**
- pip (via requirements.txt)
- Lockfile: `requirements.txt` (version-fixed)

## Frameworks

**Core GUI:**
- Tkinter (standard library) - All UI components, dialogs, event handling
  - `tk.Tk`, `tk.Canvas`, `ttk.Button`, `ttk.Style` for widget styling
  - `tkinter.filedialog`, `messagebox`, `simpledialog` for dialogs
  - `tkinter.ttk` for themed widgets

**PDF Processing:**
- PyMuPDF (fitz) 1.27.2.2 - PDF reading, writing, rendering
  - `fitz.Document` for PDF document handling
  - `page.get_pixmap()` for rasterization
  - `doc.save()` for persistence

**Image Processing:**
- Pillow (PIL) 12.2.0 - Image conversion and display
  - `ImageTk.PhotoImage` for Tkinter canvas rendering
  - Image format conversion (PNG/JPEG/BMP)

**File Drag & Drop:**
- tkinterdnd2 0.4.3 - Drag-and-drop file operations
  - `TkinterDnD.Tk` for DnD-enabled root window
  - `DND_FILES` protocol handling

**Build & Distribution:**
- PyInstaller 6.19.0 - Windows executable bundling (onedir format)
  - Config: `PageFolio.spec`
  - Output: `dist/PageFolio/` directory with _internal subdirectory

**Testing:**
- pytest 9.0.2 - Test runner
- pytest-cov 7.1.0 - Coverage measurement

**Code Quality:**
- Ruff 0.15.7 - Linting and formatting
  - `line-length = 88`
  - Rules: E (pycodestyle), F (Pyflakes), W (warnings), I (isort), S (bandit), B (flake8-bugbear)
  - Tests exempt: `tests/**/*.py` excludes S101 (assert)

## Key Dependencies

**Critical:**
- PyMuPDF 1.27.2.2 - PDF is core functionality; version pinned for API stability
- Pillow 12.2.0 - Image rendering on canvas; version pinned
- tkinterdnd2 0.4.3 - File drop UX; version pinned

**OCR Infrastructure:**
- urllib (standard library) - HTTP client for vision APIs
  - `urllib.request.Request`, `urllib.request.urlopen` for REST calls
  - `urllib.error.HTTPError`, `urllib.error.URLError` for error handling
- base64 (standard library) - Image encoding for API transmission
- json (standard library) - API request/response serialization
- socket (standard library) - Timeout handling

**Threading & Concurrency:**
- concurrent.futures.ThreadPoolExecutor - Multi-page OCR parallelization (max 8 workers)
- threading (standard library) - Background task management

**Plugin System:**
- importlib, importlib.util (standard library) - Dynamic plugin loading from `plugins/` directory

**Standard Library Usage:**
- logging - Module-level loggers across codebase
- os - Path operations, file/directory manipulation
- sys - Runtime detection (PyInstaller vs. normal execution)
- json - Settings persistence (`pagefolio_settings.json`)
- subprocess - Tesseract OCR subprocess invocation

## Configuration

**Environment:**
- Runtime settings: `pagefolio_settings.json` (user's home/exe directory)
  - Theme selection (dark/light/system)
  - Font size (8-16)
  - Language (ja/en)
  - OCR provider choice and model selection
  - Thumbnail page size (10-100, default 20)
  - Window geometry (position and size)

**API Key Storage:**
- Environment variables only (never persisted to settings.json):
  - `ANTHROPIC_API_KEY` - Claude API
  - `GEMINI_API_KEY` - Gemini API (primary)
  - `GOOGLE_API_KEY` - Gemini API (fallback)
- Session memory (`app._session_api_keys`) for temporary session-duration keys
- Structural guard: `_SENSITIVE_KEYS` set in `pagefolio/settings.py` prevents accidental leaks

**Build:**
- `pyproject.toml` - Ruff config, pytest paths
- `requirements.txt` - Direct dependency versions (no transitives listed)
- `PageFolio.spec` - PyInstaller config (icon, onedir mode)

## Platform Requirements

**Development:**
- Python 3.8+
- pip and venv
- Windows 11 (primary development target)
- Optional: Tesseract OCR binary (for Tesseract provider)
- Optional: LM Studio server running locally (for LM Studio provider)

**Production (End-User):**
- Windows 11
- No Python installation required (packaged as .exe via PyInstaller)
- Optional: Tesseract OCR installed and in PATH (for Tesseract OCR)
- Optional: LM Studio running on localhost:1234 (for LM Studio OCR)
- Network: HTTPS access for Claude/Gemini APIs (if cloud providers enabled)

## Architectural Constraints

**Threading Model:**
- Single Tkinter main thread for UI event loop
- Preview/thumbnail renders queued via `root.after()` (cooperative, not threaded)
- Generation counters (`_preview_gen`, `_thumb_gen`) prevent stale results
- OCR uses `ThreadPoolExecutor` (max 8 workers) for concurrent vision API calls
- `fitz.Document` **not shared** across threads; only base64 images sent to workers

**Module-Level Singletons:**
- `C` (theme dictionary in `pagefolio/themes.py`) - Runtime mutable
- Settings loaded once on startup and persisted on save
- PluginManager singleton per app instance

**Global State:**
- `THEMES` and `LANG` constants in `pagefolio/constants.py` (immutable)
- `_SENSITIVE_KEYS` set for credential guard (immutable)

**Undo/Redo Memory:**
- Hard limit: 20 stack entries (MAX_UNDO in `pagefolio/app.py`)
- v1.7.0+: Large deltas (≥64KB) auto-spilled to tempfiles via `UndoBlobStore`
- Small deltas (<64KB) remain in-memory as `MemBlob`

---

*Stack analysis: 2026-07-03*
