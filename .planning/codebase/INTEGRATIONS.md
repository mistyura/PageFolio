# External Integrations

**Analysis Date:** 2026-06-10

## APIs & External Services

**OCR Backends:**
- LM Studio Vision API - Local OCR via OpenAI-compatible `/v1/chat/completions` endpoint
  - SDK/Client: `urllib.request` (built-in)
  - Config: `lm_studio_url` (default: `http://localhost:1234`), `lm_studio_model`
  - Provider: `LMStudioProvider` (`pagefolio/ocr_providers.py`)
  - Default concurrency: 2 (max: 8)

- Anthropic Claude - Cloud OCR via `/v1/messages` API
  - SDK/Client: `urllib.request` (built-in)
  - Auth: Environment variable `ANTHROPIC_API_KEY` (never stored in settings)
  - Config: `claude_model` (default: `claude-sonnet-4-6`), `ocr_effort` (default: `low`)
  - Provider: `ClaudeProvider` (`pagefolio/ocr_providers.py`)
  - Models supported: `claude-haiku-4-5`, `claude-sonnet-4-6`, `claude-opus-4-8` (+ others)
  - Default concurrency: 2 (max: 2)
  - Temperature support: haiku only
  - Effort support: sonnet/opus models (output_config.effort parameter)

- Google Gemini - Cloud OCR via `generateContent` API
  - SDK/Client: `urllib.request` (built-in)
  - Auth: Environment variables `GEMINI_API_KEY` (primary) or `GOOGLE_API_KEY` (fallback)
  - Auth method: HTTP header `x-goog-api-key` (not URL query param)
  - Config: `gemini_model` (default: `gemini-2.5-flash`), temperature support
  - Provider: `GeminiProvider` (`pagefolio/ocr_providers.py`)
  - Models supported: `gemini-2.5-flash`, `gemini-2.5-pro` (+ others)
  - Default concurrency: 1 (max: 1) - Free Tier rate limit 10 RPM
  - Special handling: thinkingConfig disabled for flash models; omitted for pro models (stability)

- Tesseract OCR - Local/offline OCR via subprocess
  - SDK/Client: `subprocess` (built-in)
  - CLI invocation: `tesseract stdin stdout -l {lang} --psm 3`
  - Config: `lang` (auto-detects jpn/eng availability, fallback: eng)
  - Provider: `TesseractProvider` (`pagefolio/ocr_providers.py`)
  - Default concurrency: 1 (max: 2) - CPU bound
  - Supported languages: Japanese (jpn), English (eng), jpn+eng (default)

## Data Storage

**Settings Storage:**
- Local filesystem only
- File: `pagefolio_settings.json` (same directory as executable)
- Format: JSON
- Persistence: Theme, font size, language, window geometry, OCR provider config, plugin disable list
- Security: API keys **never** written (structural guard: `_SENSITIVE_KEYS` in `pagefolio/settings.py`)

**PDF Document State:**
- In-memory only during session (`fitz.Document`)
- Undo/Redo: Binary snapshots in memory (max 20 snapshots, `MAX_UNDO = 20`)
- No external database required

**Session-Only Data:**
- API keys: Stored in `app._session_api_keys` dict (memory, process-scoped)
- Read from environment variables: `os.environ.get()`
- Never written to disk or environment
- Destroyed on process exit

**File Storage:**
- None - Outputs are written directly to PDF files on disk via `doc.save()`
- No cloud storage integration
- No temporary file dependencies (except PIL/fitz internal buffers)

**Caching:**
- Thumbnail cache: In-memory dict `self.thumb_cache` (keyed by page index)
- Generation counter pattern: `_preview_gen`, `_thumb_gen` to prevent stale renders
- No persistent cache

## Authentication & Identity

**Auth Provider:**
- None (application has no user authentication)
- API keys managed per-service via environment variables
- Session-memory only for runtime use
- Settings file explicitly excludes sensitive keys

**API Key Management:**
- Read-only from environment: `os.environ.get("ANTHROPIC_API_KEY")`, etc.
- Alternative: Session prompts (`LLMConfigDialog` allows runtime key entry)
- Input validation: `OCRAPIKeyError` exception if key missing at OCR time
- Security: No logging of key values, only key names in error logs

## Monitoring & Observability

**Error Tracking:**
- None configured

**Logs:**
- Python `logging` module (standard library)
- Default level: `WARNING` (set in `PDFEditorApp.__init__`)
- Format: `%(levelname)s:%(name)s:%(message)s`
- Examples: provider connection errors, plugin failures, settings load errors
- No centralized logging service

**Telemetry:**
- None

## CI/CD & Deployment

**Hosting:**
- Desktop application (Windows 11 native `.exe`)
- No cloud deployment

**Build:**
- PyInstaller 6.19.0 (`PageFolio.spec`)
- Output: Single-directory bundle with executable
- Console: Disabled (windowed app only)
- Icon: `pagefolio.ico`

**Distribution:**
- Manual `.exe` download/installation
- No auto-update mechanism

## Environment Configuration

**Required Environment Variables:**
- None for basic functionality

**Optional Environment Variables:**
- `ANTHROPIC_API_KEY` - Required only if using Claude OCR provider
- `GEMINI_API_KEY` - Required only if using Gemini OCR provider (preferred)
- `GOOGLE_API_KEY` - Fallback if `GEMINI_API_KEY` not set
- `TESSERACT_CMD` - Path to tesseract executable (Windows only, if not in PATH)

**Settings File Keys (Non-Secret):**
| Key | Default | Purpose |
|-----|---------|---------|
| `theme` | "dark" | UI theme (dark/light/system) |
| `font_size` | 12 | Base font size (8-16) |
| `lang` | "ja" | Language (ja/en) |
| `lm_studio_url` | http://localhost:1234 | LM Studio endpoint |
| `lm_studio_model` | "" (empty) | Model name for LM Studio |
| `ocr_provider` | "off" | Active OCR provider (off/lmstudio/claude/gemini/tesseract) |
| `claude_model` | claude-sonnet-4-6 | Claude model selection |
| `gemini_model` | gemini-2.5-flash | Gemini model selection |
| `ocr_effort` | "low" | Effort level (low/medium/high/xhigh/max) for compatible models |
| `ocr_scale` | 1.5 | Page image scaling for OCR (1.0-3.0) |
| `ocr_timeout` | 120 | OCR API timeout (seconds) |
| `ocr_max_tokens` | -1 | Max output tokens (-1 = model default) |
| `ocr_temperature` | 0.1 | Temperature parameter (0.0-2.0) |
| `ocr_concurrency` | 2 | Parallel OCR threads (1-8) |
| `ocr_prompt_preset` | text | Prompt template (text/table/markdown) |
| `edit_mode` | false | Start in edit mode (true/false) |
| `window_geometry` | "" | Previous window size/position |
| `disabled_plugins` | [] | Plugin IDs to disable on startup |

**Secrets Location:**
- Environment variables only (read-only)
- Never committed to `.env` or settings files
- Session memory in `app._session_api_keys` (process-scoped, ephemeral)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None (application does not initiate external callbacks)

## API Rate Limits & Quotas

**Anthropic Claude:**
- Standard rate limits apply per API key tier
- Retry-After handling: Clamped to 60 seconds max (DoS prevention, `RETRY_AFTER_CAP`)
- Automatic exponential backoff with retry loop (max 3 attempts)
- Interruptible sleep: User can cancel mid-retry via UI

**Google Gemini:**
- Free Tier: 10 requests per minute (RPM)
- Concurrency limited to 1 to respect quota
- Retry-After handling: Same as Claude (clamped 60s)
- Same exponential backoff + cancellation support

**LM Studio:**
- No inherent rate limits (local server)
- Timeout: 120 seconds (configurable)
- Connection failure handling: Reports connection error

**Tesseract:**
- No network rate limits (local CLI tool)
- Timeout: 60 seconds (configurable)
- Concurrent execution: Limited to 2 max (CPU bound)

## Network & Transport

**Protocol:**
- HTTPS for all cloud APIs (Claude, Gemini)
- HTTP for local services (LM Studio)
- urllib.request only - no external HTTP library

**Image Transmission:**
- Base64 encoded PNG data in request body
- PDF page rendered to PNG at specified scale (`ocr_scale`, default 1.5x)
- Size: Typically 0.5-5 MB per page (depends on page content and scale)
- Transmission path: Tkinter UI thread → PNG encode → Base64 → HTTP POST → Remote API
- Local OCR (Tesseract, LM Studio): No transmission; local subprocess/localhost

**Error Handling:**
- `ConnectionError` - Network unreachable, server not running
- `TimeoutError` - Response not received within timeout window
- `OCRRetryableError` - HTTP 429/5xx (automatic retry with backoff)
- `RuntimeError` - HTTP 4xx (non-retryable), API response format error
- `OCRAPIKeyError` - API key missing from environment

---

*Integration audit: 2026-06-10*
