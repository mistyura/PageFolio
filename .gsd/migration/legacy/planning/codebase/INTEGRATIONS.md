# External Integrations

**Analysis Date:** 2026-07-03

## APIs & External Services

**OCR Providers:**
- **LM Studio** - Local OpenAI-compatible Vision API (`/v1/chat/completions`)
  - SDK/Client: urllib.request (custom HTTP)
  - Configuration: `settings["lm_studio_url"]` (default: `http://localhost:1234`)
  - Model selection: `settings["lm_studio_model"]`
  - Auth: None (local server)
  - Implementation: `LMStudioProvider` in `pagefolio/ocr_providers.py`

- **Claude (Anthropic)** - HTTP vision API (`/v1/messages`)
  - SDK/Client: urllib.request (custom HTTP)
  - Auth env var: `ANTHROPIC_API_KEY` (never persisted)
  - Model selection: `settings["claude_model"]` (default: `claude-sonnet-4-6`)
  - Effort parameter: `settings["ocr_effort"]` (low/medium/high for supported models)
  - Endpoints: `https://api.anthropic.com/v1/messages` and `/v1/models`
  - Implementation: `ClaudeProvider` in `pagefolio/ocr_providers.py`

- **Google Gemini** - HTTP vision API (`/v1beta/models/{model}:generateContent`)
  - SDK/Client: urllib.request (custom HTTP)
  - Auth env vars: `GEMINI_API_KEY` (primary) or `GOOGLE_API_KEY` (fallback, D-06)
  - Auth method: `x-goog-api-key` header (not URL query param, D-05)
  - Model selection: `settings["gemini_model"]` (default: `gemini-2.5-flash`)
  - Endpoints: `https://generativelanguage.googleapis.com/v1beta/models`
  - Implementation: `GeminiProvider` in `pagefolio/ocr_providers.py`

- **Tesseract OCR** - Local binary subprocess call
  - SDK/Client: subprocess module (command-line invocation)
  - Platform requirement: Tesseract-OCR binary must be in PATH
  - Auth: None (local)
  - Implementation: `TesseractProvider` in `pagefolio/ocr_providers.py`

- **Ollama** - Local Ollama vision API (`/api/generate`)
  - SDK/Client: urllib.request (custom HTTP)
  - Configuration: `settings["ollama_url"]` (default: `http://localhost:11434`)
  - Model selection: `settings["ollama_model"]`
  - Auth: None (local server)
  - Implementation: `OllamaProvider` in `pagefolio/ocr_providers.py`

- **RunPod** - Serverless GPU API (via Runpod endpoint)
  - SDK/Client: urllib.request (custom HTTP)
  - Configuration: `settings["runpod_url"]` and `settings["runpod_model"]`
  - Auth: RunPod API key (environment variable, never persisted)
  - Implementation: `RunPodProvider` in `pagefolio/ocr_providers.py`

## Data Storage

**Configuration & Settings:**
- Local JSON file: `pagefolio_settings.json` (location: app executable directory or project root)
  - Stores: theme, font size, language, window geometry, OCR provider settings
  - Does NOT store: API keys (structural guard via `_SENSITIVE_KEYS`)

**Temporary Files:**
- Undo/Redo blob storage (v1.7.0+): Auto-spilled to system temp directory via `tempfile` module
  - Threshold: deltas ≥64KB spilled; <64KB stay in-memory
  - Cleanup: Auto-purged on stack eviction, redo clear, file close, app exit

**File Operations:**
- Local filesystem only (PDF read/write, image import/export)
- No cloud storage or database integration
- Temp files for print operations (Windows PDF printing)

## Authentication & Identity

**API Key Management:**
- Source priority (D-02):
  1. Environment variables (checked first: `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`)
  2. Session memory via `app._session_api_keys` dict (fallback only if env var not set)
  3. **Never** written to `pagefolio_settings.json` (security guard)

**Key Retrieval Functions:**
- `_resolve_api_key(provider_name, session_keys)` in `pagefolio/ocr.py` - Enforces env-var-first lookup
- Exception: `OCRAPIKeyError` raised if both env var and session key missing

## Monitoring & Observability

**Logging:**
- Python standard `logging` module throughout codebase
- Module-level loggers (`logger = logging.getLogger(__name__)`)
- No external log aggregation (local console/file only during dev)

**Error Handling:**
- Custom exception hierarchy for OCR (`OCRAPIKeyError`, `OCRRetryableError`, `OCRContextLengthError`)
- HTTP error mapping: 429/5xx → `OCRRetryableError` (with Retry-After parsing)
- Context length overflow detection via response body markers

**User Feedback:**
- `messagebox.showerror()` for file operation failures
- Status bar via `_set_status(msg)` for operation completion messages
- Progress indication in OCR dialog (`ocr_dialog.py`)

## CI/CD & Deployment

**Hosting:**
- GitHub repository (`https://github.com/mistyura/PageFolio`)
- Releases as .zip archives (onedir + .sha256 checksum)

**Build Process:**
- Local development: `python pagefolio.py` or `python -m pagefolio`
- CI/CD: GitHub Actions (implied by memory notes on immutable releases)
- Build command (user-facing): PyInstaller via `PageFolio.spec`
- Output: `dist/PageFolio/` (onedir format with `PageFolio.exe` and `_internal/`)

**Distribution:**
- GitHub Releases tab
- Asset naming: `PageFolio-v<version>-win64.zip` + `.sha256` file
- Tag naming: Semver (e.g., `v1.7.0`, with `-N` suffix if collision)

## Webhooks & Callbacks

**Incoming:**
- None (no server component)

**Outgoing:**
- None (no webhook delivery)

## Environment Configuration

**Required env vars (Cloud OCR):**
- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` - Google Gemini API key

**Optional env vars (Local OCR):**
- `PATH` - Must include Tesseract binary location (for Tesseract provider)

**Runtime Settings (pagefolio_settings.json):**
```json
{
  "theme": "dark|light|system",
  "font_size": 8-16,
  "lang": "ja|en",
  "lm_studio_url": "http://localhost:1234",
  "lm_studio_model": "string",
  "ollama_url": "http://localhost:11434",
  "ollama_model": "string",
  "runpod_url": "string",
  "runpod_model": "string",
  "ocr_prompt_preset": "text|table|markdown",
  "ocr_scale": 1.5,
  "ocr_timeout": 120,
  "ocr_max_tokens": -1,
  "ocr_temperature": 0.1,
  "ocr_concurrency": 2,
  "ocr_provider": "off|lmstudio|claude|gemini|tesseract|ollama|runpod",
  "claude_model": "claude-sonnet-4-6",
  "ocr_effort": "low|medium|high",
  "gemini_model": "gemini-2.5-flash",
  "thumb_page_size": 20
}
```

## Network Requirements

**Cloud OCR Providers:**
- Claude: Outbound HTTPS to `https://api.anthropic.com/v1/`
- Gemini: Outbound HTTPS to `https://generativelanguage.googleapis.com/v1beta/`
- RunPod: Outbound HTTPS to user-configured RunPod endpoint

**Local OCR Providers:**
- LM Studio: Localhost HTTP to `http://localhost:1234` (configurable)
- Tesseract: Local subprocess (no network)
- Ollama: Localhost HTTP to `http://localhost:11434` (configurable)

## External File Format Support

**Input:**
- PDF (.pdf)
- Images (.png, .jpg, .jpeg, .bmp, .tiff, .tif)
- Multi-format merge: PDFs and images can be combined on open

**Output:**
- PDF (.pdf) - primary output format (via PyMuPDF)
- Images (.png, .jpg) - export via `pagefolio/dialogs/export_images.py`
- Markdown - OCR result export (text-only, no embedded images)
- JSON - Settings file only (not user-facing)

## Third-Party Plugins

**Plugin Architecture:**
- Plugin directory: `plugins/` (alongside `pagefolio.py`)
- Base class: `PDFEditorPlugin` in `pagefolio/plugins.py`
- Lifecycle hooks: `on_load`, `on_unload`, `on_file_open`, `on_file_save`, `on_page_rotate`, etc.
- Registry: `PluginManager` discovers and loads `.py` files from `plugins/`
- Sample: `plugins/page_info.py` (page info viewer plugin)

---

*Integration audit: 2026-07-03*
