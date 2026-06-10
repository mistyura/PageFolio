# Technology Stack

**Analysis Date:** 2026-06-10

## Languages

**Primary:**
- Python 3.8+ - Full application (GUI, PDF processing, OCR integration)

**Secondary:**
- None - Pure Python implementation with standard library focus

## Runtime

**Environment:**
- Python 3.14.3 (development); 3.8+ (supported)

**Package Manager:**
- pip - Lockfile: `requirements.txt` (fixed versions)

## Frameworks

**Core:**
- Tkinter - Standard library GUI framework. Used for all UI components: `tk.Tk`, `ttk.Button`, `tk.Canvas`, `tk.PanedWindow`, `tk.Frame`

**PDF Processing:**
- PyMuPDF (fitz) 1.27.2.2 - PDF reading, writing, rendering, page manipulation (`fitz.Document`, `page.get_pixmap()`, `doc.save()`)
- Pillow (PIL) 12.2.0 - Image conversion and display (`Image`, `ImageTk.PhotoImage` for preview rendering)

**File Drag & Drop:**
- tkinterdnd2 0.4.3 - Native drag-and-drop support for files (`TkinterDnD.Tk`, `DND_FILES`, `drop_target_register()`)

## Key Dependencies

**Critical:**
- PyMuPDF 1.27.2.2 - Core PDF manipulation, rendering, CropBox operations. Project cannot function without it.
- Tkinter (standard library) - All UI rendering. No alternative display framework.

**Infrastructure:**
- Pillow 12.2.0 - Bridge between fitz pixmaps and Tkinter PhotoImage. Required for preview/thumbnail display.
- tkinterdnd2 0.4.3 - File drag-and-drop feature. Provides native OS integration.

## Configuration

**Environment:**
- Settings persisted in `pagefolio_settings.json` (user home/executable directory)
- Theme: dark/light (runtime dict `C` in `pagefolio/themes.py`)
- Language: ja/en (dict `LANG` in `pagefolio/lang.py`)
- API keys: Read from environment variables only (never written to settings)

**Environment Variables (Optional - OCR backends):**
- `ANTHROPIC_API_KEY` - Claude API key (read-only, session-memory only)
- `GEMINI_API_KEY` - Google Gemini API key (primary, read-only)
- `GOOGLE_API_KEY` - Fallback for Gemini API (read-only)

**Build:**
- `pyproject.toml` - Ruff linting/formatting, pytest configuration
- `PageFolio.spec` - PyInstaller build definition (onedir format, Windows executable)
- `requirements.txt` - All runtime and dev dependencies with pinned versions

## Platform Requirements

**Development:**
- Python 3.8+ with pip
- Ruff 0.15.7 for linting/formatting (`ruff check . && ruff format .`)
- pytest 9.0.2 + pytest-cov 7.1.0 for testing

**Production:**
- Windows 11 (primary target, Registry access for system theme detection)
- Python 3.8+ runtime
- PyInstaller builds single `.exe` (no external dependencies needed)
- Optional: LM Studio (http://localhost:1234) for local OCR
- Optional: tesseract command-line tool for offline OCR
- Optional: Internet connection for Claude/Gemini cloud OCR

## Build Tooling

| Tool | Version | Purpose |
|------|---------|---------|
| Ruff | 0.15.7 | Linting (E/F/W/I/S/B rules) + formatting |
| PyInstaller | 6.19.0 | Windows executable generation |
| pytest | 9.0.2 | Test runner |
| pytest-cov | 7.1.0 | Coverage measurement |

**Ruff Configuration** (`pyproject.toml`):
- `line-length = 88`
- `select = ["E", "F", "W", "I", "S", "B"]`
- Tests exempt S101 (assert allowed in test code)

## Standard Library Usage

| Module | Purpose |
|--------|---------|
| `tkinter`, `tkinter.ttk` | GUI construction (`pagefolio/ui_builder.py`, dialogs) |
| `tkinter.filedialog`, `messagebox`, `simpledialog` | File dialogs and user messages |
| `json` | Settings file read/write (`pagefolio/settings.py`) |
| `os` | Path operations, file system checks |
| `logging` | Log output across all modules |
| `threading` | Background preview/thumbnail rendering (`pagefolio/viewer.py`) |
| `concurrent.futures.ThreadPoolExecutor` | Multi-page OCR parallel execution (`pagefolio/ocr.py`) |
| `urllib.request`, `urllib.error` | HTTP calls to LM Studio, Claude, Gemini APIs |
| `base64`, `socket` | OCR payload encoding and network handling |
| `subprocess` | Tesseract command invocation |
| `importlib`, `importlib.util` | Plugin system dynamic imports (`pagefolio/plugins.py`) |
| `winreg` | Windows system theme detection (optional, with fallback) |

## Code Quality

**Linting Rules:**
- E (pycodestyle errors)
- F (Pyflakes)
- W (pycodestyle warnings)
- I (isort - import sorting)
- S (bandit security)
- B (flake8-bugbear)

**Forbidden Patterns:**
- No bare `except:` - must use `except Exception as e:`
- No `# type: ignore` without justification
- API keys never written to `pagefolio_settings.json` (structural guard in `_SENSITIVE_KEYS`)

---

*Stack analysis: 2026-06-10*
