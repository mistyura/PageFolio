# Codebase Concerns

**Analysis Date:** 2026-07-03

## Tech Debt

### Large File Complexity

**OCR Dialog Module:**
- Issue: `pagefolio/ocr_dialog.py` is 2154 lines, combining UI rendering, threading coordination, progress tracking, and multiple OCR workflows (image OCR + text-only summarization) in a single class
- Files: `pagefolio/ocr_dialog.py` (lines 1-2154)
- Impact: Difficult to test individual workflow paths; high cognitive load for future modifications; threading bugs harder to isolate
- Fix approach: Consider extracting threading/worker coordination (`_worker`, `_render_queue`, `_done_lock`, `_summary_worker`) into a separate `OCRWorkerCoordinator` class, and UI rendering (`_build`, event handlers) into an `OCRDialogUI` mixin

**OCR Providers Module:**
- Issue: `pagefolio/ocr_providers.py` is 1424 lines with 5 provider implementations (LMStudio, Claude, Gemini, Tesseract, Ollama/RunPod) sharing exception handling, retry logic, and base64 encoding/decoding
- Files: `pagefolio/ocr_providers.py` (lines 1-1424)
- Impact: Adding a new provider requires reading/understanding all 1400+ lines; common patterns (e.g., `ocr_image_ex` truncation detection, `complete_text_ex` implementation) not factored out
- Fix approach: Extract common provider utilities (base64 handling, HTTP error mapping, stop_reason parsing) into helper functions; consider template method pattern for `ocr_image` implementation

**LLM Config Dialog:**
- Issue: `pagefolio/dialogs/llm_config.py` is 1204 lines, handling provider-specific UI generation, validation, cost estimation, and nested settings dialog with multiple entry points
- Files: `pagefolio/dialogs/llm_config.py` (lines 1-1204)
- Impact: UI control sync paths (spinner updates triggering cost recalc, model selection cascading) are fragile and error-prone
- Fix approach: Decouple data validation (`_validate_*`) from UI feedback; use observer pattern for model/timeout changes that require cost/UI updates

### Blob Lifecycle Management (v1.7.0)

**Undo/Redo Disk Offloading Fragility:**
- Issue: New `UndoBlobStore` with `FileBlob`/`MemBlob` duality introduced in v1.7.0. Blob release is distributed across multiple deque eviction points (`_push_evicting`, `_clear_redo_stack`, `_undo`, `_redo`, `_clear_undo_stacks`) and atexit. Identity comparison (`data is data`) used to skip double-release in insert_undo→insert_redo chains, but subtle edge cases possible
- Files: `pagefolio/undo_store.py`, `pagefolio/file_ops.py` (Blob lifecycle methods)
- Impact: Memory leaks if a code path misses a release; Windows file locking during temp cleanup; atexit order dependency with application shutdown hooks
- Fix approach: Implement `__del__` with logging on `FileBlob` to detect leaked instances; add `weakref`-based Blob tracking set to detect double-releases; unit test Windows AV scan collision (mock `os.unlink` to raise `PermissionError`)

### API Key Secrecy Guard Implementation

**Dual Environment Variable Names:**
- Issue: Settings module must guard against `claude_api_key`, `gemini_api_key`, `google_api_key` (snake_case), plus `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, etc. (uppercase) due to Gemini dual-key fallback (D-06 / WR-03). List is manual and duplicated across `settings.py`
- Files: `pagefolio/settings.py` (lines 17-28, `_SENSITIVE_KEYS`)
- Impact: Risk of adding a new key format and forgetting to add it to the guard list; no central registry
- Fix approach: Generate `_SENSITIVE_KEYS` from a provider-to-env-var mapping dict; centralize in `constants.py` or new `pagefolio/security.py`

## Known Bugs

### undo = no-op for insert_blank, watermark, page_numbers (v1.7.0 Fixed)

**Pre-v1.7.0 Issue (Resolved):**
- Symptoms: Undo after these operations did nothing
- Files: `pagefolio/page_ops.py` (now uses `insert` op for blank, `page_edit` op for watermark/numbers)
- Cause: `_save_undo`/`_restore_state` had no branch to capture page state before operation
- Workaround: Not applicable; fixed in v1.7.0 by switching to page-capturing operations
- Current Status: **FIXED** — but verify through `test_undo_stress.py` (120-page stress test) and retroactive changelog audit

### Watermark rotate=45 ValueError (v1.7.0 Fixed)

**Pre-v1.7.0 Issue (Resolved):**
- Symptoms: `insert_text(rotate=45)` raises ValueError during watermark creation
- Files: `pagefolio/page_ops.py` (around watermark implementation)
- Cause: PyMuPDF `insert_text` only accepts 0°, 90°, 180°, 270°; 45° must use `morph=(pivot, fitz.Matrix(45))`
- Workaround: Not applicable; fixed in v1.7.0 by changing rotation matrix approach
- Current Status: **FIXED** — but only discovered in new test; suspect similar 45° usage elsewhere

### Preview Serialization (TEST-02 / BUG-03, v1.3.0 Fixed)

**Pre-v1.3.0 Issue (Resolved):**
- Symptoms: `_render_preview_pixmap` was calling `doc.tobytes()` unnecessarily, inflating memory for large PDFs
- Files: `pagefolio/viewer.py` (regression test: `tests/test_viewer.py` lines 1-80)
- Current Status: **FIXED** in v1.3.0 — test confirms `doc.tobytes()` is never called

## Security Considerations

### API Key Exposure in Session Memory

**Risk:** 
- API keys are held in `app._session_api_keys` dict (in-memory) and passed as `api_key=` parameter to providers. Memory dump or debugger could expose keys.
- Files: `pagefolio/app.py` (session dict initialization), `pagefolio/ocr_dialog.py` (key resolution), `pagefolio/ocr.py` (`build_provider`)
- Current Mitigation: Keys never written to disk; environment variables preferred; settings file has `_SENSITIVE_KEYS` guard that logs warnings if a key somehow reaches it
- Recommendations:
  1. Clear session keys from memory after each OCR dialog closes (`_summary_worker` cleanup)
  2. Use `secrets` module to avoid key string logging in exceptions
  3. Add automated scan (`test_source_keyguard.py` + `test_settings_keyguard.py`) for literal key patterns in source — currently in place but verify monthly

### Base64 Image Data in Network Transmission

**Risk:**
- Pages are rendered to PNG, base64-encoded, and sent to cloud OCR (Claude/Gemini/Ollama/RunPod) via HTTP(S). Plaintext in network if not HTTPS.
- Files: `pagefolio/ocr.py` (`page_to_png_b64`), OCR providers (HTTP calls)
- Current Mitigation: HTTPS enforced by provider SDKs (Anthropic, Google AI); LM Studio / Ollama / RunPod typically localhost
- Recommendations:
  1. Verify provider SDKs force HTTPS (audit LM Studio / Ollama URL constructors)
  2. Add schema validation in settings to reject `http://` for cloud providers (Anthropic/Gemini)
  3. Document security implications in README for Ollama/RunPod (localhost only) and user-provided URLs

### tkinterdnd2 Import Failure Graceful Degradation

**Risk:**
- If `tkinterdnd2` fails to import, file D&D is silently skipped (`_setup_file_drop` returns early if `_HAS_TKDND=False`)
- Files: `pagefolio/file_drop.py` (lines 6-11)
- Current Mitigation: No error message shown; graceful fallback to non-D&D workflow (file→open menu or keyboard)
- Recommendations:
  1. Log a DEBUG message when D&D is disabled (not a blocker, but user context helpful)
  2. Consider adding status bar indicator "D&D disabled (tkinterdnd2 unavailable)" on non-Windows or if import failed

## Performance Bottlenecks

### OCR Threading Producer-Consumer Queue Bottleneck

**Problem:**
- `pagefolio/ocr_dialog.py` uses producer-consumer pattern with `queue.Queue(maxsize=concurrency+1)` for rendering pages into base64
- Files: `pagefolio/ocr_dialog.py` (lines 1353, producer thread at line 1352-1364, consumer worker loop)
- Cause: Producer (page rendering) and consumer (OCR API call) run on same thread (main thread for rendering, worker thread for API), creating potential idle time if rendering is slow
- Current Capacity: ~2 default concurrency; max 8 workers; single producer thread
- Improvement Path:
  1. Profile rendering vs API call times for typical PDFs (test with 20-page, 100-page, 1000-page)
  2. If rendering is bottleneck (>100ms per page), parallelize rendering with a second producer pool or pre-render all pages before OCR
  3. If API call is bottleneck, concurrency increase is already possible via UI slider

### Thumbnail Cache No Eviction

**Problem:**
- `self.thumb_cache` (dict[int, ImageTk.PhotoImage]) grows unbounded as user scrolls through large PDFs
- Files: `pagefolio/viewer.py` (thumbnail rendering and cache), `pagefolio/pagination.py` (page window logic)
- Current Capacity: No limit; 100-page PDF = ~100 thumbnails cached (~5-10 MB uncompressed PIL images)
- Improvement Path:
  1. Implement LRU cache with max size (e.g., 50 thumbnails = ~2.5 MB)
  2. Trim cache when new page window is shown and old window falls outside visible range
  3. Add cache stats to settings for transparency

### PNG Rendering Scale Factor Static

**Problem:**
- Thumbnail scale is hardcoded `fitz.Matrix(0.22, 0.22)` (`pagefolio/viewer.py`); preview scale is `self.zoom * 1.5`
- Files: `pagefolio/viewer.py` (lines for thumb/preview rendering)
- Impact: Low-DPI displays may see small thumbnails; high-DPI (4K) displays waste GPU time upscaling
- Improvement Path: Detect system DPI and adjust scale proportionally; add scale factor setting

## Fragile Areas

### Dialog-Level Settings Synchronization

**Component:** `SettingsDialog` ↔ `LLMConfigDialog` ↔ `OCRDialog`

**Why Fragile:**
- `SettingsDialog` opens `LLMConfigDialog` for OCR provider config
- Changing settings in nested dialog does NOT persist until outer dialog is closed and "OK" clicked
- User can apply a change in LLM config, close the dialog, then cancel the outer settings dialog—change is lost
- v1.6.3 fixed the "apply doesn't persist" issue, but change isn't visible to user until outer dialog closes
- Files: `pagefolio/dialogs/settings.py` (LLM config dialog launch), `pagefolio/dialogs/llm_config.py` (nested dialog)
- Safe Modification:
  1. Test closing nested dialog without "OK", then reopening—verify old values restored
  2. Test canceling outer dialog after nested apply—verify change reverted
  3. Add temporary confirmation ("Settings unsaved") before outer cancel

### D&D Multi-Page Reordering with Window Scroll

**Component:** `DnDMixin` (thumbnail D&D) ↔ `pagination.py` (window calculation)

**Why Fragile:**
- `selected_pages` held as global indices, but D&D drop index is **local** to visible window
- Conversion via `to_global_index()` in pagination; if window scrolls mid-drag, local→global mapping changes
- Files: `pagefolio/dnd.py` (drop event handler), `pagefolio/pagination.py` (index conversion), `pagefolio/viewer.py` (thumbnail render)
- Safe Modification:
  1. Test: select pages 5-10 (visible in window 1-20), scroll to window 21-40, drop—pages should move to original position not current window
  2. Unit test `pagination.to_global_index()` with edge cases (window edge drops)
  3. Add comment in dnd.py: "Window cannot change during drag" (one-thread assumption)

### Undo State Delta Edge Cases

**Component:** `FileOpsMixin` (undo/redo state delta save/restore)

**Why Fragile:**
- Each operation defines its own delta structure (e.g., rotate stores `{"degrees": [0, 90, -90]}`, delete stores `{"deleted_at": 2, "pages_bytes": MemBlob}`)
- No schema validation; if code updates delta structure, old saved deltas become incompatible
- `_restore_state` must handle all op types and all fields; missing branch = silent failure (operation ignored on undo)
- Files: `pagefolio/file_ops.py` (delta save/restore per operation), `pagefolio/page_ops.py` (operation-specific deltas)
- Safe Modification:
  1. Add `assert` or type check at start of `_restore_state` to catch typos in delta keys
  2. Write test for each op: save undo → undo → redo → verify result matches original
  3. Document delta schema for each operation type (table in CLAUDE.md)

## Scaling Limits

### Undo Stack Hard Limit

**Resource:** Undo/Redo deques with `maxlen=MAX_UNDO` (currently 20 in `pagefolio/app.py`)

**Current Capacity:** 20 operations × 2 stacks = 40 entries max; each entry holds 0-N page Blobs
- Low-resolution PDFs: ~10 KB/page → 20 MB per full stack (acceptable)
- High-resolution (scanned) PDFs: ~5 MB/page → 200 MB per full stack (disk offload required)
- Limit: v1.7.0 offloads FileBlobs at 64 KiB threshold; stress test validates 120-page PDF

**Scaling Path:**
1. Make `MAX_UNDO` configurable in settings (currently not exposed)
2. Monitor Blob directory size (`UndoBlobStore.dir`) and warn if >500 MB
3. Consider adaptive eviction (evict oldest if tempdir >1 GB)

### OCR Concurrency Hard Ceiling

**Resource:** `max_concurrency = 8` workers in `OCRProvider` base class

**Current Capacity:** 8 parallel API calls; rate-limited by provider (Claude: 50k TPM, Gemini: varies, LM Studio: unlimited local)
- 20-page PDF at 8 workers → ~250 ms API latency per page × 20 / 8 = ~625 ms (ideal)
- Actual: likely 2-5 seconds per page due to image rendering, base64 encode, API overhead
- Limit: Reaching 8 workers increases thread spawn overhead; UI becomes unresponsive if main thread blocked

**Scaling Path:**
1. Profile actual throughput (pages/sec) at different concurrency levels
2. Set sensible default (2-4) and advertise max 8 as experimental
3. For bulk OCR, recommend batch processing with progress breaks

## Dependencies at Risk

### PyMuPDF 1.27.2.2

**Risk:**
- Version 1.27.x is relatively recent (released 2026); breaking changes may occur in 1.28 or later
- PDF redaction (`apply_redactions()`) is PyMuPDF-specific; upgrading may change behavior
- CropBox manipulation is version-tested but boundary conditions (MediaBox clamp) may change
- Files: Heavy usage in `pagefolio/page_ops.py`, `pagefolio/viewer.py`, `pagefolio/redact_ops.py`, OCR providers
- Current Mitigation: Version pinned in `requirements.txt`
- Migration Plan:
  1. Test `requirements.txt` candidates (1.28, 1.29) annually
  2. Maintain upgrade branch for each major PyMuPDF release
  3. Document any CropBox, redaction, or rendering API changes

### tkinterdnd2 0.4.3

**Risk:**
- Inactive upstream; last release 2021; no Python 3.13 support guaranteed
- tk.PanedWindow interaction (dnd_bind on Canvas children) may be fragile
- Only tested on Windows; Linux/macOS untested (graceful degrade expected)
- Files: `pagefolio/file_drop.py`, D&D bindings in `pagefolio/app.py`
- Current Mitigation: Try/except import; feature is optional (non-blocking)
- Migration Plan:
  1. Monitor Python 3.13 support; fallback to manual file open if dnd2 breaks
  2. Consider platform-specific drag-drop (Windows: WinAPI, Linux: GTK3)

### Pillow 12.2.0

**Risk:**
- Regular security updates required; deprecated JPEG codec in older Pillow may be dropped
- PNG→Tk.PhotoImage conversion (`ImageTk.PhotoImage`) may break in future Pillow versions (non-standard interface)
- Files: `pagefolio/viewer.py` (thumbnail/preview render), OCR image export
- Current Mitigation: Version pinned; usage is straightforward (`Image.open`, `convert('RGB')`, etc.)
- Migration Plan:
  1. Test Pillow 13 annually
  2. Have fallback PNG rendering (e.g., use Tkinter Canvas with PIL draw if ImageTk breaks)

## Test Coverage Gaps

### File D&D Path

**Untested Area:** tkinterdnd2 integration when module unavailable

- What's Not Tested: Behavior of `_setup_file_drop` when `_HAS_TKDND=False`; UI fallback paths (no error message)
- Files: `pagefolio/file_drop.py`, test coverage in `tests/`
- Risk: User on Linux without tkinterdnd2 binary gets silent D&D failure with no explanation
- Priority: **Low** — graceful degrade acceptable; add log message to confirm
- Test Coverage Path:
  1. Mock `tkinterdnd2` import failure in pytest; verify `_setup_file_drop` returns early
  2. Verify file open still works via menu (non-D&D path)
  3. Add integration test on Windows with D&D enabled

### Multi-Dialog Cascade Interactions

**Untested Area:** SettingsDialog → LLMConfigDialog → OCRDialog state propagation

- What's Not Tested: Changing LLM settings in nested dialog, then canceling outer dialog; state consistency after undo/redo across dialog re-entry
- Files: `pagefolio/dialogs/settings.py`, `pagefolio/dialogs/llm_config.py`, `pagefolio/ocr_dialog.py`
- Risk: User confusion if change appears to apply but reverts; Undo state may mismatch if dialog re-entry loads stale cached settings
- Priority: **Medium** — user-facing but low frequency scenario
- Test Coverage Path:
  1. Open settings → change LLM model → cancel settings → verify doc state unchanged
  2. Open OCR dialog → change model in nested LLM config → cancel OCR → change model again → verify consistency
  3. Open settings → change LLM prompt → apply → switch to OCR dialog → verify prompt is reflected (cross-dialog state)

### Watermark/Page Number Rendering Alignment

**Untested Area:** Watermark/page number positioning on rotated pages, scaled pages, or pages with CropBox set

- What's Not Tested: Watermark appears correctly after page rotate, or page number stays aligned on cropped pages
- Files: `pagefolio/page_ops.py` (watermark/page_number methods)
- Risk: Watermark/number placement appears off-center or clipped after crop+rotate sequence
- Priority: **High** — visual/user-visible issue
- Test Coverage Path:
  1. Create test PDF; apply crop, rotate 90°, add watermark; verify visual alignment
  2. Unit test: watermark on page with CropBox != MediaBox (coordinate transform)
  3. Regression test for v1.7.0 fix: verify rotate=45 watermark no longer raises ValueError

### Blob Lifecycle Edge Cases (v1.7.0)

**Untested Area:** FileBlob cleanup on Windows with antivirus/file locks; double-release edge cases in identity-comparison chains

- What's Not Tested: `os.unlink` on FileBlob fails (AV holds handle); identity comparison skips release when two op deltas share same Blob ref
- Files: `pagefolio/undo_store.py`, `pagefolio/file_ops.py` (eviction/cleanup hooks)
- Risk: Memory leak or orphaned temp files; two-phase undo (op1 → op2 → undo op1 → undo op2) may double-release if not careful
- Priority: **High** — affects large-file workflows
- Test Coverage Path:
  1. Mock `os.unlink` to raise `PermissionError`; verify purge still removes via `rmtree`
  2. Test: insert → undo → redo → undo again; verify no double-release (add spy to Blob.release)
  3. Stress test (existing `test_undo_stress.py`): monitor temp dir size; confirm cleanup after each undo

### OCR Dialog Cancel/Restart Lifecycle

**Untested Area:** Canceling OCR mid-render; restarting after cancel; canceling during summarization

- What's Not Tested: Worker threads left alive after cancel; queue not drained; generation counter prevents stale callbacks
- Files: `pagefolio/ocr_dialog.py` (_cancel_flag, _run_gen, _summary_cancel_flag)
- Risk: Orphaned threads; memory leaks if dialog re-entered without proper cleanup
- Priority: **Medium** — edge case but affects user experience
- Test Coverage Path:
  1. Start OCR with 10+ pages; cancel after 3 pages → verify worker threads exit within timeout
  2. Start OCR → cancel → immediate restart → verify no race condition (generation counter prevents callback storms)
  3. Start summarization → cancel → verify _summary_cancel_flag is properly cleared for next summary

## Missing Critical Features

### Batch Processing Mode

**Problem:** Users with 100+ PDFs must open app for each file (no CLI batch processing)

- Files: No CLI entry point; all operations require Tkinter GUI
- Blocks: Automated workflows, server-side processing
- Impact: Enterprise users must script PDF operations or use command-line tool

### PDF Encryption Password Recovery

**Problem:** If user sets password then loses it, PDF is unrecoverable

- Files: `pagefolio/dialogs/password.py` (password UI), `pagefolio/file_ops.py` (_authenticate_doc)
- Blocks: User recovery scenarios; no master password or hint system
- Impact: Data loss risk if password forgotten
- Note: Acceptable limitation for security-conscious app; document in README "No password recovery"

### OCR Result Diff/Merge

**Problem:** No way to compare OCR results across multiple runs or merge corrections

- Files: `pagefolio/ocr_dialog.py` (result display)
- Blocks: Iterative OCR refinement workflows
- Impact: Users must manually track changes across OCR runs

---

*Concerns audit: 2026-07-03*
