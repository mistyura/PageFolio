# Technology Stack

**Analysis Date:** 2026-07-16

## Languages

**Primary:**
- Python 3.8+ - Entire application, with Python 3.9+ optimizations for `ThreadPoolExecutor.shutdown(cancel_futures=True)`

**Secondary:**
- None - Pure Python project

## Runtime

**Environment:**
- Python 3.8+ (minimum 3.8, optimized for 3.9+)
- Windows 11 (primary target OS)

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (present, pinned versions)

## Frameworks

**Core:**
- Tkinter (standard library) - GUI framework for Windows 11
- PyMuPDF 1.28.0 - PDF document manipulation (reading, rendering, editing)
- Pillow 12.3.0 - Image processing (PIL, used for thumbnails and image conversion)
- tkinterdnd2 0.6.2 - Drag & drop support for Tkinter widgets (fallback to standard Tk if unavailable)

**Testing:**
- pytest 9.1.1 - Test runner and framework
- pytest-cov 7.1.0 - Coverage reporting

**Build/Dev:**
- pyinstaller 6.21.0 - CLI executable generation (--onedir format for Windows)
- ruff 0.15.20 - Linting and code formatting (88-char line length)

## Key Dependencies

**Critical:**
- PyMuPDF 1.28.0 - Single source of truth for PDF rendering, document manipulation, and page operations (rotation, cropping, deletion, redaction). Used across `page_ops.py`, `file_ops.py`, `redact_ops.py`
- Pillow 12.3.0 - Image rendering for thumbnails (`thumb_cache`, scale 0.22x) and preview generation (scale 1.5x zoom)
- Tkinter (stdlib) - All UI rendering in `pagefolio/` mixins and dialogs (`ui_builder.py`, dialogs package)

**Infrastructure:**
- tkinterdnd2 0.6.2 - Optional runtime dependency; graceful fallback to standard Tk if import fails (`__main__.py`)

## Configuration

**Environment:**
- API keys (ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, RUNPOD_API_KEY) supplied via environment variables only
- Settings file: `pagefolio_settings.json` (JSON format in exe/project directory)
- External prompt files: `ocr_custom_prompt.md`, `ocr_summary_prompt.md` (optional, same directory as executable)

**Build:**
- `pyproject.toml` - Ruff linting/formatting config, pytest configuration
- `PyFolio.spec` - PyInstaller spec for --onedir executable generation
- Ruff settings: line-length 88, enabled rules: E/F/W/I/S/B

## Platform Requirements

**Development:**
- Python 3.8+ (3.9+ recommended for concurrent.futures optimizations)
- Windows 11 (though code has Linux/macOS compatibility in UI framework layer, printing is Windows-only)
- Visual C++ redistributable (bundled by PyInstaller in `_internal/`)

**Production:**
- Windows 11
- No external runtime dependencies beyond included `_internal/` folder
- Bundled with PyInstaller --onedir, distributes as `PageFolio/` folder with `PageFolio.exe` and `_internal/` subdirectory

---

*Stack analysis: 2026-07-16*
