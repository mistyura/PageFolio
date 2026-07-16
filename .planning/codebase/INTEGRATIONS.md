# External Integrations

**Analysis Date:** 2026-07-16

## APIs & External Services

**OCR/LLM Providers:**
- Claude API (Anthropic) - Vision-based OCR and text completion
  - SDK/Client: urllib (stdlib) + manual HTTP requests
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Endpoint: `https://api.anthropic.com/v1/messages`
  - Supported models: claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-8 (and variants)
  - Features: effort parameter support (sonnet/opus), temperature control (haiku)
  - Concurrency: default 2, max 2
  - Timeout: 120 seconds (configurable)

- Google Gemini API - Vision-based OCR and text completion
  - SDK/Client: urllib (stdlib) + manual HTTP requests
  - Auth: `GEMINI_API_KEY` (primary) or `GOOGLE_API_KEY` (fallback) environment variables
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  - Supported models: gemini-2.5-flash, gemini-2.5-pro
  - Features: thinking config (non-pro models only), temperature control
  - Concurrency: default 1, max 1 (Free Tier 10 RPM rate limit)
  - Timeout: 120 seconds (configurable)

- RunPod Serverless - Inference endpoint for custom models
  - SDK/Client: urllib (stdlib) + manual HTTP requests
  - Auth: `RUNPOD_API_KEY` environment variable
  - Endpoint: User-configured RunPod endpoint URL (must be http/https scheme)
  - Features: Custom LM support, text-only completion capability
  - Concurrency: default 2, max 8
  - Model list timeout: 90 seconds (accounts for serverless cold starts)

**Local OCR/LLM Providers (No Auth):**
- LM Studio - Local OpenAI-compatible Vision API
  - SDK/Client: urllib (stdlib) + manual HTTP requests
  - Endpoint: User-configured URL (default: `http://localhost:1234`)
  - Scheme validation: http/https only (security gate L-6e/D-13)
  - Concurrency: default 2, max 8
  - Timeout: 120 seconds (configurable)

- Ollama - Local LLM inference
  - SDK/Client: urllib (stdlib) + manual HTTP requests
  - Endpoint: User-configured URL (default: `http://localhost:11434`)
  - Scheme validation: http/https only
  - Concurrency: default 2, max 8
  - Timeout: 120 seconds (configurable)

- Tesseract OCR - Local OCR engine
  - SDK/Client: subprocess call to `tesseract` binary
  - Requirements: Tesseract must be installed and in PATH
  - Text-only output (no vision model support)
  - Concurrency: default 2, max 8

## Data Storage

**Databases:**
- None - File-based only

**File Storage:**
- Local filesystem only
  - PDF documents: User-selected paths
  - Settings: `pagefolio_settings.json` in exe/project directory
  - Temporary files: System temp directory (for undo blob overflow >64KiB via `UndoBlobStore`)
  - External prompts: `ocr_custom_prompt.md`, `ocr_summary_prompt.md` (same directory as executable)

**Caching:**
- In-memory thumbnail LRU cache (`thumb_cache`) - 300-entry max
- In-memory preview generation cache (no persistent caching)
- Undo/Redo stacks - max 20 entries, large blobs overflow to tempfile

## Authentication & Identity

**Auth Provider:**
- None - Environment variable API keys only
- No login/user management
- All credentials supplied via environment variables: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `RUNPOD_API_KEY`
- API keys **never** persisted to `pagefolio_settings.json` (guarded by `_SENSITIVE_KEYS` in `pagefolio/settings.py`)

## Monitoring & Observability

**Error Tracking:**
- None - Local error handling via `messagebox.showerror()`

**Logs:**
- Python `logging` module to stdout/stderr
- No persistent log file
- Per-module loggers in OCR providers and dialogs

## CI/CD & Deployment

**Hosting:**
- GitHub Releases - Distribution of `PageFolio-vX.X.X-win64.zip`

**CI Pipeline:**
- None defined in repository
- Manual build via PyInstaller: `pyinstaller PageFolio.spec --onedir`

## Environment Configuration

**Required env vars:**
- None (optional for OCR features):
  - `ANTHROPIC_API_KEY` - Claude API (required for Claude OCR provider)
  - `GEMINI_API_KEY` or `GOOGLE_API_KEY` - Gemini API (required for Gemini provider, GEMINI_API_KEY has priority)
  - `RUNPOD_API_KEY` - RunPod endpoint (required for RunPod provider)

**Secrets location:**
- Environment variables only
- `.env` file support: Not implemented (environment variables directly)
- Hardcoded defaults: None (all credentials required at runtime for cloud providers)

**API Key Management:**
- Session memory (`app._session_api_keys` dict) - transient, not persisted
- Settings file exemption: `pagefolio/ocr_providers/registry.py` defines `sensitive_keys()` which blocks: `api_key`, `{provider}_api_key`, environment variable names and their lowercase variants

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- Plugin hooks: `on_load`, `on_unload`, `on_file_open`, `on_file_save`, `on_page_rotate`, `on_page_delete`, `on_page_crop`, `on_page_change`, `on_insert`, `on_merge`, `build_ui`
- Managed via `PDFEditorPlugin` base class and `PluginManager` (`pagefolio/plugins.py`)

## External File Dependencies

**OCR Providers:**
- Claude provider: `pagefolio/ocr_providers/claude.py` - Uses `ClaudeProvider` class for API calls
- Gemini provider: `pagefolio/ocr_providers/gemini.py` - Uses `GeminiProvider` class for API calls
- RunPod provider: `pagefolio/ocr_providers/runpod.py` - Custom LM endpoint support
- LM Studio: `pagefolio/ocr_providers/lmstudio.py` - OpenAI-compatible endpoint
- Ollama: `pagefolio/ocr_providers/ollama.py` - Local LLM endpoint
- Tesseract: `pagefolio/ocr_providers/tesseract.py` - Subprocess-based local OCR
- Registry: `pagefolio/ocr_providers/registry.py` - Central env var mapping (stdlib `os` only, no internal imports)

**OCR Pipeline:**
- `pagefolio/ocr_pipeline.py` - Pure logic (Tk/fitz-free) for queue-based page image processing
- `pagefolio/ocr_dialog.py` - UI for OCR execution, result display, markdown rendering
- `pagefolio/ocr_engine.py` - `OCRRunEngine` class coordinating provider selection and execution
- `pagefolio/md_render.py` - Markdown parsing for OCR result display

**External Prompt Files:**
- `ocr_custom_prompt.md` - Custom OCR system prompt (optional)
- `ocr_summary_prompt.md` - Summary generation prompt (optional)
- Loaded via `pagefolio/settings.py` functions: `load_custom_prompt()`, `load_summary_prompt()`, `load_prompt_file()`
- Written back to disk on LLM settings dialog apply

---

*Integration audit: 2026-07-16*
