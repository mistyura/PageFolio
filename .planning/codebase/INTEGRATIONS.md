# External Integrations

**Analysis Date:** 2026-07-22

## APIs & External Services

**OCR Providers (Cloud):**
- **Claude (Anthropic)** - Messages API for vision-based OCR
  - SDK/Client: urllib (standard library, direct HTTP requests)
  - Endpoint: `https://api.anthropic.com/v1/messages`
  - Auth: `x-api-key` header
  - Environment variable: `ANTHROPIC_API_KEY`
  - Implementation: `pagefolio/ocr_providers/claude.py` (`ClaudeProvider` class)
  - Models: claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-8 (recommended)
  - Features: Supports effort parameter (sonnet/opus), temperature parameter (haiku), vision API, text-only completion for summaries
  - Concurrency: default 2, max 2

- **Gemini (Google)** - generateContent API for vision-based OCR
  - SDK/Client: urllib (standard library, direct HTTP requests)
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  - Auth: `x-goog-api-key` header
  - Environment variables: `GEMINI_API_KEY` (primary), `GOOGLE_API_KEY` (fallback)
  - Implementation: `pagefolio/ocr_providers/gemini.py` (`GeminiProvider` class)
  - Models: gemini-3.6-flash, gemini-3.5-flash, gemini-3.5-flash-lite, gemini-2.5-flash, gemini-2.5-pro (recommended)
  - Features: Supports thinkingConfig (flash models only), vision API, text-only completion for summaries
  - Note: gemini-3.x generation (v1.8.1+) does not support temperature/thinkingConfig parameters (safe fallback)
  - Concurrency: default 1, max 1 (Free Tier 10 RPM limit)

- **RunPod** - OpenAI-compatible Serverless Vision API
  - SDK/Client: urllib (standard library, direct HTTP requests)
  - Endpoint: User-configured URL (e.g., `https://api.runpod.io/...`)
  - Auth: `authorization` header with API key
  - Environment variable: `RUNPOD_API_KEY`
  - Settings field: `runpod_url`, `runpod_model`
  - Implementation: `pagefolio/ocr_providers/runpod.py` (`RunPodProvider` class)
  - Protocol: OpenAI-compatible `/v1/chat/completions` (Chat Completions API)
  - Features: Vision API, text-only completion, customizable endpoint
  - Timeout: 90 seconds (includes cold start for serverless)
  - Concurrency: default 2, max 4

**OCR Providers (Local):**
- **Tesseract** - Local OCR engine (subprocess)
  - CLI invocation: `tesseract` command-line tool
  - No API key required (local installation)
  - Implementation: `pagefolio/ocr_providers/tesseract.py` (`TesseractProvider` class)
  - Configuration: Language packs (detected via `--list-langs`), PSM mode
  - Availability detection: Subprocess-based (tried on each provider instantiation, not cached)
  - Supported languages: Configurable via `lang` parameter (e.g., "jpn+eng")
  - Concurrency: default 1, max 2 (CPU-bound)

- **LM Studio** - Local OpenAI-compatible Vision API
  - SDK/Client: urllib (standard library, direct HTTP requests)
  - Endpoint: User-configured URL (default: `http://localhost:1234`)
  - No API key required (local server)
  - Settings field: `lm_studio_url`, `lm_studio_model`
  - Implementation: `pagefolio/ocr_providers/lmstudio.py` (`LMStudioProvider` class)
  - Protocol: OpenAI-compatible `/v1/chat/completions` (Chat Completions API)
  - Features: Vision API, text-only completion, customizable endpoint
  - Concurrency: default 2, max 8

- **Ollama** - Local OpenAI-compatible Vision API
  - SDK/Client: urllib (standard library, direct HTTP requests)
  - Endpoint: User-configured URL (default: `http://localhost:11434`)
  - No API key required (local server)
  - Settings field: `ollama_url`, `ollama_model`
  - Implementation: `pagefolio/ocr_providers/ollama.py` (`OllamaProvider` class)
  - Protocol: OpenAI-compatible `/v1/chat/completions` (Chat Completions API)
  - Features: Vision API, text-only completion, customizable endpoint
  - Concurrency: default 2, max 8

## Data Storage

**Databases:**
- None used. Application is fully local-file based.

**File Storage:**
- Local filesystem only
- Settings file: `pagefolio_settings.json` (JSON, UTF-8)
- Undo/Redo blobs: Tempfile for entries ≥64KiB (`UndoBlobStore` in `pagefolio/undo_store.py`), in-memory for smaller entries
- OCR results: User-exported via UI (no automatic persistence)
- Configuration files: Optional external prompt files (`ocr_custom_prompt.md`, `ocr_summary_prompt.md`)

**Caching:**
- Thumbnail cache: In-memory LRU cache (`pagefolio/thumb_cache.py`, max 300 entries)
- Settings: Loaded once at startup, persisted to JSON on changes

## Authentication & Identity

**Auth Provider:**
- None (not applicable - desktop application, no user accounts)

**API Key Handling:**
- Cloud providers (Claude, Gemini, RunPod) require API keys passed via environment variables
- Keys are **NOT** stored in `pagefolio_settings.json` (guarded by `_SENSITIVE_KEYS` in `pagefolio/settings.py`)
- Keys are stored in session memory (`app._session_api_keys`) during runtime (cleared on exit)
- Registry of sensitive keys: `pagefolio/ocr_providers/registry.py` (`PROVIDER_ENV_KEYS`, `sensitive_keys()`)
- Local providers (Tesseract, LM Studio, Ollama) do not require authentication

**Environment Variables (Cloud OCR):**
```
ANTHROPIC_API_KEY          # Claude provider
GEMINI_API_KEY             # Gemini provider (primary)
GOOGLE_API_KEY             # Gemini provider (fallback)
RUNPOD_API_KEY             # RunPod provider
```

## Monitoring & Observability

**Error Tracking:**
- None (no external error tracking service)
- Logging: Python logging to console/stderr (level: WARNING by default)

**Logs:**
- Console logging via `logging` module
- Logger instances per module (e.g., `logging.getLogger(__name__)`)
- Format: `"%(levelname)s:%(name)s:%(message)s"`

## CI/CD & Deployment

**Hosting:**
- Windows 11 desktop application (not hosted)
- Distributed as standalone `.exe` via PyInstaller

**CI Pipeline:**
- None configured (local development workflow)
- Manual build: `pyinstaller PageFolio.spec`
- Spec file: `PageFolio.spec` (PyInstaller configuration)

**Build Artifacts:**
- Executable: `dist/PageFolio/PageFolio.exe`
- Icon: `pagefolio.ico`

## Environment Configuration

**Required Environment Variables (for cloud OCR):**
- `ANTHROPIC_API_KEY` - For Claude provider (if using)
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` - For Gemini provider (if using)
- `RUNPOD_API_KEY` - For RunPod provider (if using)

**Optional Configuration:**
- `lm_studio_url` - LM Studio server URL (default: `http://localhost:1234`, stored in settings)
- `lm_studio_model` - LM Studio model name (stored in settings)
- `ollama_url` - Ollama server URL (default: `http://localhost:11434`, stored in settings)
- `ollama_model` - Ollama model name (stored in settings)
- `runpod_url` - RunPod serverless endpoint URL (stored in settings)
- `runpod_model` - RunPod model name (stored in settings)

**Secrets Location:**
- Environment variables (not in version control)
- Loaded at runtime from OS environment
- Never persisted to `pagefolio_settings.json`

## Webhooks & Callbacks

**Incoming:**
- None (desktop application, no server)

**Outgoing:**
- None (no external callbacks or webhooks)

**Plugin Hooks:**
- `on_load`, `on_unload` - Plugin lifecycle
- `on_file_open`, `on_file_save` - File operations
- `on_page_rotate`, `on_page_delete`, `on_page_crop` - Page modifications
- `on_page_change` - Navigation
- `on_insert`, `on_merge` - Multi-page operations
- `build_ui` - Custom UI extension
- Implementation: `pagefolio/plugins.py` (`PluginManager` class)

## Provider Fallback Chain

**Feature:** Automatic failover to backup OCR providers (v1.8.0 Phase 2)
- Settings field: `ocr_fallback_enabled` (boolean, default False)
- Settings field: `ocr_fallback_chain` (list of provider names, default empty)
- Implementation: `pagefolio/ocr.py` (fallback logic in `run_parallel`)
- Disabled by default for safety (explicit user configuration required)

---

*Integration audit: 2026-07-22*
