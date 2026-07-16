# Codebase Concerns

**Analysis Date:** 2026-07-16

## Tech Debt

**Large Monolithic Dialog Module:**
- Issue: `pagefolio/ocr_dialog.py` is 2537 lines, combining UI state management, progress tracking, result rendering, export, and cancellation logic in a single file
- Files: `pagefolio/ocr_dialog.py`
- Impact: Difficult to test individual concerns; high cognitive load when debugging; changes to one feature risk affecting others
- Fix approach: Extract UI builder (section construction), result renderer (Markdown parsing/display), and progress state into separate modules; keep OCRDialog as orchestrator

**Module-Level Mutable Globals:**
- Issue: `pagefolio/settings.py` maintains module-level mutable state: `C` (theme dict) and `_current_font_size` updated at runtime
- Files: `pagefolio/settings.py` (lines 381+)
- Impact: Runtime theme/font changes mutate global state; if accessed during concurrent operations, could cause display artifacts; testing requires careful state isolation
- Fix approach: Consider immutable theme selection pattern or explicit state instance passing rather than global mutation

**Undo/Redo Complexity:**
- Issue: Undo/Redo system spans multiple files (`file_ops.py`, `undo_store.py`) with complex blob lifecycle: deque eviction, redo clearing, identity-based disposal, atexit purge
- Files: `pagefolio/file_ops.py`, `pagefolio/undo_store.py` (esp. lines 130-182)
- Impact: High risk of resource leaks if blob disposal hooks are skipped; direct `deque.append()`/`clear()` forbidden, but no runtime enforcement
- Fix approach: Add `_push_evicting()` validation in tests; audit all stack mutations; consider wrapper class that enforces disposal invariant

**OCR Registry Independence Constraint:**
- Issue: `pagefolio/ocr_providers/registry.py` must remain independent (no pagefolio imports except `os`), but this makes it hard to extend without coordinator function duplication
- Files: `pagefolio/ocr_providers/registry.py` (lines 1-13 document the constraint)
- Impact: If constraint is violated, circular imports will break settings.py loading; future maintainers must remember this undocumented rule
- Fix approach: Document constraint in CLAUDE.md (already done); add lint check or import guard test

## Known Bugs

**Insert Undo/Redo Asymmetry (BUG-01):**
- Symptoms: Insert followed by undo removes inserted pages correctly, but redo may restore them with duplicate content or missing pages
- Files: `pagefolio/file_ops.py` (insert undo/redo logic), `tests/test_pdf_ops.py` (lines 529-684 regression tests)
- Trigger: Insert pages → Undo → Redo in sequence; high-page-count PDFs more likely to exhibit
- Status: Regression tests added in v1.2.5 and maintained through v1.8.0; currently passing

**Preview Pixmap Rendering Performance (BUG-03):**
- Symptoms: Large PDF previews could cause UI lag due to inefficient rendering
- Files: `pagefolio/viewer.py` (lines 1-100), `tests/test_viewer.py` (TEST-02 regression)
- Trigger: Opening 100+ page PDFs with frequent page navigation
- Status: Fixed in v1.3.0 by removing `doc.tobytes()` call; regression test confirms `doc.tobytes()` is never invoked (line 35-48 in test_viewer.py)

**Window Navigation Snap-Back (resolved v1.6.0):**
- Symptoms: Manual thumbnail window navigation (◀ ▶ buttons) would snap back to current_page after refresh
- Files: `pagefolio/viewer.py` (lines 188-202)
- Trigger: Navigate window independent of current_page, then trigger `_refresh_all()`
- Status: Resolved in v1.6.0 Phase 02-03 by ensuring `current_page` follows window movement; design document at `.planning/debug/260618-pagination-window-nav-snapback.md`

**Tcl/Tk Test Flakiness (noted in development):**
- Symptoms: pytest suite occasionally experiences spurious failures on Windows due to Tkinter event timing
- Files: Affects all UI tests; known in MEMORY.md: "pytest フルスイートのTcl/Tkフレーキーを記録"
- Trigger: Running full pytest suite under time pressure or on slow machines
- Workaround: Re-run failed tests; add `pytest --tb=short` to diagnose timing issues

## Security Considerations

**API Key Exposure Vectors:**
- Risk: API keys (Claude, Gemini, RunPod) could be persisted to disk if `_SENSITIVE_KEYS` guard is bypassed or settings.json accidentally committed
- Files: `pagefolio/settings.py` (lines 70-80, `_load_settings` and `_save_settings`), `pagefolio/ocr_providers/registry.py` (lines 56-73, `sensitive_keys()`)
- Current mitigation: `_SENSITIVE_KEYS` whitelist prevents saving to settings.json; environment variables and session memory only; `.gitignore` includes `pagefolio_settings.json`
- Recommendations: 
  - Audit all `_save_settings()` calls to ensure no new key types bypass whitelist
  - Add pre-commit hook to scan for accidental API key patterns in committed files
  - Document API key handling in README.md security section

**External LLM API Dependency:**
- Risk: Cloud OCR (Claude, Gemini, RunPod) sends page images as base64 to external APIs; if API is compromised or misconfigured, sensitive document content could be exposed
- Files: `pagefolio/ocr.py` (page_to_png_b64), `pagefolio/ocr_providers/claude.py`, `pagefolio/ocr_providers/gemini.py`, `pagefolio/ocr_providers/runpod.py`
- Current mitigation: HTTPS enforced; user selects provider explicitly; warnings in UI for sensitive documents
- Recommendations:
  - Add document sensitivity checkbox in OCR dialog (don't OCR; warn if cloud selected)
  - Log OCR requests with redaction for audit trails
  - Support local-only fallback (Tesseract/LM Studio/Ollama) with no network requirement

**PDF Password Handling:**
- Risk: `_authenticate_doc()` in `file_ops.py` may store password in memory; if process is dumped, password could be recovered
- Files: `pagefolio/file_ops.py` (password handling), `pagefolio/dialogs/password.py` (password input UI)
- Current mitigation: Passwords are requested per-session, not persisted; AES-256 encryption used for password-protected PDFs
- Recommendations:
  - Ensure password variable is explicitly cleared after use (add `password = b'\x00' * len(password)` if possible)
  - Document password handling limitations in CLAUDE.md

## Performance Bottlenecks

**OCR Dialog Markdown Rendering:**
- Problem: `_insert_markdown()` in `ocr_dialog.py` parses and inserts markdown line-by-line into Text widget; large results (100KB+) cause UI lag
- Files: `pagefolio/ocr_dialog.py` (lines 1500+), `pagefolio/md_render.py` (parse_markdown function)
- Cause: No batching; each line creates separate tag/insertion calls to Tk Text widget
- Improvement path: Batch insert operations; use `text.config(state='disabled')` around large insertions; consider offscreen rendering

**Thumbnail Cache LRU:**
- Problem: Thumbnail generation for large PDFs (500+ pages) on first open creates visible pause
- Files: `pagefolio/thumb_cache.py` (LruCache), `pagefolio/viewer.py` (thumbnail rendering)
- Cause: All visible thumbnails rendered in sequence before display; no progressive rendering for first load
- Improvement path: Implement progressive thumbnail rendering (render visible range first, then background workers for others); add visual "loading..." indicator

**Undo Stack Memory with Large PDFs:**
- Problem: Even with blob store, MAX_UNDO=20 can consume gigabytes of disk temp space with large high-res PDFs
- Files: `pagefolio/undo_store.py`, `pagefolio/file_ops.py` (MAX_UNDO = 20 in line 25)
- Cause: Hard-coded limit doesn't scale with file size; each operation may store full page as blob
- Improvement path: Dynamic MAX_UNDO based on available disk space; adaptive blob threshold (increase for large PDFs)

**OCR Concurrent Requests:**
- Problem: `run_parallel()` in `ocr.py` uses ThreadPoolExecutor with DEFAULT_OCR_CONCURRENCY=5; may cause provider rate limits or memory spike
- Files: `pagefolio/ocr.py` (lines 130-180, run_parallel function)
- Cause: No backpressure; all threads may hit rate limiter simultaneously
- Improvement path: Implement exponential backoff with jitter; add provider-specific rate limit detection; reduce concurrency dynamically

## Fragile Areas

**OCR Error Handling and Fallback Chain:**
- Files: `pagefolio/ocr.py` (build_provider, line ~350+), `pagefolio/ocr_dialog.py` (error handlers), `pagefolio/ocr_fallback.py`
- Why fragile: Multiple fallback stages (provider API → timeout retry → fallback provider → error message) with limited test coverage; if one stage throws unexpected exception, user sees generic error
- Safe modification: Add mock/spy tests for each fallback branch; verify no exceptions leak out of error handlers
- Test coverage: `tests/test_ocr.py`, `tests/test_ocr_fallback.py` exist but gaps remain in multi-stage fallback scenarios

**File Operations with State Mutations:**
- Files: `pagefolio/file_ops.py` (esp. lines 650-720, operations that update doc and undo stack in sequence)
- Why fragile: Operations like delete/move/insert must update both `self.doc` and undo stack atomically; if exception occurs mid-operation, doc and stack become inconsistent
- Safe modification: Wrap operation in try/except; use dedicated "rollback" method if exception occurs; test both success and exception paths
- Test coverage: `tests/test_pdf_ops.py` covers happy paths; missing exception recovery tests

**Pagination Window Calculation:**
- Files: `pagefolio/pagination.py` (lines 70-160, window bounds calculation), `pagefolio/viewer.py` (window navigation handlers)
- Why fragile: Window start must stay synchronized with current_page across multiple operations (page delete, move, etc.); off-by-one errors cause visible list corruption
- Safe modification: Add invariant checks in tests (e.g., `assert window_start <= current_page < window_start + page_size`); refactor window/page separation to prevent mixing
- Test coverage: `tests/test_pagination.py` has 100+ tests but regressions still surface during manual UAT

**Plugin Manager Event Firing:**
- Files: `pagefolio/plugins.py` (lines 150-230, fire_event method), `pagefolio/app.py` (plugin event calls)
- Why fragile: Plugins are wrapped individually so one plugin exception doesn't crash others, but if plugin modifies app state (e.g., `app.doc`, `app.current_page`), subsequent plugins see corrupted state
- Safe modification: Snapshot state before plugin callback; detect unexpected state changes; add plugin integration tests
- Test coverage: `tests/test_plugins.py` tests basic lifecycle; missing multi-plugin interaction tests

## Scaling Limits

**Document Size Limit:**
- Current capacity: Successfully tested with 120-page PDFs; thumbnail window fits ~100 pages
- Limit: 500+ page PDFs cause visible lag on thumbnail rendering; 1000+ pages may run out of memory
- Scaling path: Implement lazy thumbnail generation (visible range only + background); add pagination auto-adjust; document recommended limits in README

**Concurrent OCR Requests:**
- Current capacity: DEFAULT_OCR_CONCURRENCY=5 works for typical fast APIs (Gemini); slower APIs (RunPod) may bottleneck
- Limit: More than 5 concurrent threads risk rate limiting on cloud providers; no per-provider tuning
- Scaling path: Per-provider concurrency limits; exponential backoff detector; dynamic adjustment based on 429 responses

**Undo Stack Memory:**
- Current capacity: MAX_UNDO=20 stack entries; ~64MB per entry on large PDFs = 1.3GB max
- Limit: Heavy editing sessions (20+ operations) on 500-page PDFs exhaust disk temp space
- Scaling path: Dynamic MAX_UNDO; provide "clear undo stack" option; warn user when approaching limit

## Dependencies at Risk

**PyMuPDF (fitz) Thread Safety:**
- Risk: fitz.Document is not thread-safe; OCR code must not share doc across threads
- Current handling: Page rendering done on main thread; OCR receives base64 image only
- Migration plan: If async rendering needed, wrap fitz calls in lock or use subprocess isolation

**Tkinter Event Ordering:**
- Risk: Tkinter event loop timing is platform-dependent; callbacks scheduled with `root.after()` can fire in unexpected order on slow machines
- Current handling: Generation counters (`_preview_gen`, `_thumb_gen`) prevent stale results overwriting new ones
- Migration plan: Consider async/await abstraction if timing issues become critical; switch to asyncio event loop if Python 3.10+ baseline reached

**Environment Variable Dependency:**
- Risk: OCR API keys must be set as env vars; missing key causes build_provider to fail silently or with unclear message
- Current handling: `resolve_env_key()` returns None if not found; calling code shows error dialog
- Migration plan: Add `.env` file support with validation on startup; show env var requirements in UI

## Missing Critical Features

**Offline OCR Documentation:**
- Problem: Users expecting cloud-only OCR; local options (Tesseract, LM Studio, Ollama) are undocumented
- Blocks: Users cannot choose local-only workflows without trial/error
- Solution: Add README section with local provider setup instructions; add UI guide in About dialog

**OCR Cancellation Progress:**
- Problem: Batch OCR cancel shows "cancelling..." but doesn't update progress; users unsure if cancel is working
- Blocks: Can't know if app is hung or genuinely cancelling
- Solution: Show remaining jobs count; add "force quit" button after 5s wait

**Performance Profiling Tools:**
- Problem: No built-in profiling; users can't diagnose slow operations
- Blocks: Can't identify whether lag is OCR, rendering, or I/O
- Solution: Add `--profile` CLI flag; dump timing data to JSON on exit

## Test Coverage Gaps

**OCR Multi-Provider Fallback:**
- What's not tested: Sequence where provider 1 fails, falls back to provider 2, provider 2 succeeds
- Files: `pagefolio/ocr.py` (fallback logic), `pagefolio/ocr_fallback.py` (candidate selection)
- Risk: Fallback may skip valid providers or silently fail; no visibility into decision chain
- Priority: High (affects reliability)

**File Corruption Recovery:**
- What's not tested: If PDF file is deleted/corrupted while editor has it open, operations should fail gracefully
- Files: `pagefolio/file_ops.py` (file operations)
- Risk: App could crash or lose unsaved changes
- Priority: Medium (rare but catastrophic)

**Plugin Exception Propagation:**
- What's not tested: If plugin callback raises exception during state-modifying operation (e.g., on_page_delete), does app state remain consistent?
- Files: `pagefolio/plugins.py` (fire_event), affected operations in file_ops.py
- Risk: App state corruption without user awareness
- Priority: High (affects data integrity)

**UI Stress Test (Rapid Input):**
- What's not tested: Rapid clicking (page nav, window nav, selection) while background operations (OCR, thumbnail render) are running
- Files: Affects `viewer.py`, `app.py`, OCR dialog
- Risk: Race conditions in state updates; missing event batching
- Priority: Medium (affects user experience under heavy load)

**Settings File Corruption:**
- What's not tested: If `pagefolio_settings.json` is manually corrupted, does app recover gracefully?
- Files: `pagefolio/settings.py` (_load_settings)
- Risk: App refuses to start
- Priority: Low (user error) but easy to improve with try/except default fallback

---

*Concerns audit: 2026-07-16*
