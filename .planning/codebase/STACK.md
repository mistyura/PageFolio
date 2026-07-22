# Technology Stack

**Analysis Date:** 2026-07-22

## Languages

**Primary:**
- Python 3.8+ - Desktop application for Windows 11

## Runtime

**Environment:**
- Python 3.8+ (CPython)

**Package Manager:**
- pip (requirements.txt)
- Lockfile: present (via pip freeze compatible format)

## Frameworks

**Core UI:**
- Tkinter (Python standard library) - GUI framework
  - ttk (themed widgets) for modern widget styling
  - Canvas, PanedWindow for complex layouts

**PDF Processing:**
- PyMuPDF (fitz) 1.28.0 - PDF parsing, rendering, manipulation
  - Supports page rotation, cropping, deletion, insertion, merge
  - Vision capabilities for OCR via image rendering
  - Password protection (AES-256 encryption/decryption)

**Image Processing:**
- Pillow (PIL) 12.3.0 - Image format handling, base64 encoding for OCR APIs

**UI Enhancements:**
- tkinterdnd2 0.6.2 - Drag & drop support for thumbnail reordering and file drops

**Testing:**
- pytest 9.1.1 - Unit test runner
- pytest-cov 7.1.0 - Code coverage reporting

**Build/Distribution:**
- PyInstaller 6.21.0 - Standalone Windows executable bundling
  - Spec file: `PageFolio.spec`
  - Output: `.exe` distribution

**Development Tools:**
- ruff 0.15.20 - Linting (E, F, W, I, S, B rules) and auto-formatting
  - Line length: 88 characters

## Key Dependencies

**Critical:**
- PyMuPDF 1.28.0 - All PDF operations depend on this core library
- Pillow 12.3.0 - Required for image export and base64 encoding for OCR
- tkinterdnd2 0.6.2 - Enables drag-and-drop UI interactions (optional at import, degrades gracefully)

**Infrastructure:**
- urllib (stdlib) - HTTP requests for cloud OCR APIs (Claude, Gemini, RunPod)
- subprocess (stdlib) - Tesseract invocation for local OCR
- json (stdlib) - Settings persistence
- threading/concurrent.futures (stdlib) - Background OCR execution with ThreadPoolExecutor

## Configuration

**Runtime Settings:**
- File: `pagefolio_settings.json` (JSON format, UTF-8)
- Location: Same directory as executable (frozen) or project root (development)
- Persisted settings: theme, font_size, lang, OCR provider config, UI geometry, prompt templates
- API keys NOT persisted (environment variables only)

**Development Configuration:**
- `pyproject.toml` - Ruff linting rules and pytest configuration
  - Ruff select: E (pycodestyle), F (pyflakes), W (warnings), I (isort), S (bandit), B (flake8-bugbear)
  - Per-file ignores: S101 (assert) in tests
  - Test path: `tests/`

**External Prompt Files (Optional):**
- `ocr_custom_prompt.md` - Custom OCR instruction (managed externally, reloaded per invocation)
- `ocr_summary_prompt.md` - Summary generation instruction (managed externally, reloaded per invocation)
- Both files: UTF-8, same directory as executable/project root

## Platform Requirements

**Development:**
- Windows 11 (primary target)
- Python 3.8+ interpreter
- pip for dependency installation
- Optional: Tesseract OCR engine (for local OCR)
- Optional: LM Studio (localhost:1234 for local LLM)
- Optional: Ollama (localhost:11434 for local LLM)
- Environment variables: ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, RUNPOD_API_KEY (if using cloud OCR)

**Production:**
- Windows 11 (distributed as `.exe` via PyInstaller)
- Standalone executable (no Python installation required by end users)
- Optional: Tesseract, LM Studio, Ollama for local OCR (external installations)
- Environment variables accessible to the executable process (for cloud API keys)

## Architecture Notes

- **UI Threading:** Single-threaded Tkinter main loop with background generation counters (`_preview_gen`, `_thumb_gen`) for debounced renders
- **OCR Execution:** ThreadPoolExecutor for parallel API calls (concurrency varies by provider)
- **State Persistence:** Settings via JSON, undo/redo via deque with optional blob tempfile for large page captures
- **Plugin System:** Dynamic loading from `plugins/` directory with standardized lifecycle hooks

---

*Stack analysis: 2026-07-22*
