# Codebase Concerns

**Analysis Date:** 2026-07-22

## Tech Debt

**OCR Dialog Module Size:**
- Issue: `pagefolio/ocr_dialog.py` remains 2537 lines despite OCRRunEngine extraction (Phase 3 of v1.8.0)
- Files: `pagefolio/ocr_dialog.py`
- Impact: 
  - High cognitive complexity for maintenance and testing
  - Multiple responsibilities (UI rendering, progress tracking, result export, Markdown formatting)
  - Risk of unintended side effects when modifying progress flow or result handling
  - Test parallelization hindered by fixture setup complexity
- Fix approach: 
  - Consider extracting Markdown rendering (`_insert_markdown`) into separate module
  - Extract result export/save logic (`_on_export`) into dedicated class
  - Move preset note generation (`_update_preset_note`) to shared utility
  - Potential follow-up: Extract OCR result formatting/rendering as standalone component (post-v1.8.0)

**Sample Prompt Files Distribution Instability:**
- Issue: `ocr_custom_prompt_sample.md` and `ocr_summary_prompt_sample.md` are only git-managed in `dist/PageFolio/` directory
- Files: `dist/PageFolio/ocr_custom_prompt_sample.md`, `dist/PageFolio/ocr_summary_prompt_sample.md`
- Impact:
  - PyInstaller `--noconfirm` rebuild wipes `dist/PageFolio` and loses both prompt files
  - Each release requires manual save/restore workaround (260722-rel-v181-merge-release)
  - Inconsistency: source samples not in version control, only distribution artifacts tracked
  - Regression risk: New developers unaware of this will lose files on first build
  - Build script is not self-documenting about this requirement
- Fix approach:
  - Move prompt samples to source tree (e.g., `pagefolio/samples/`)
  - Update PyInstaller spec (`pyinstaller.spec` or build script) to `--add-data` include samples
  - Alternatively: Add post-build script to copy from source → dist/PageFolio
  - Document in CLAUDE.md build section the expected location and preservation approach
  - Add git pre-commit hook or CI check to verify samples are present in dist/

## Known Bugs

**Tkinter Test Suite Flakiness (Environment Dependent):**
- Symptoms: 
  - Running full pytest suite (1101 tests) occasionally produces 2 random failures with `tk.TclError`
  - Example error: `couldn't read file "...ttk/clamTheme.tcl"` (file exists but Tcl reader fails)
  - Single test runs always pass; only manifests in batch mode
  - Affects: `tests/test_batch_ocr_dialog.py`, `tests/test_ocr_dialog_center.py` and others
- Files: `tests/conftest.py`, `tests/test_batch_ocr_dialog.py` (and similar Tk test files)
- Cause: Tk resource exhaustion from repeated `tk.Tk()` generation/destruction in single pytest process
  - 1100+ `root.destroy()` calls deplete Tcl/Tk interpreter resources
  - Tcl theme file cache or similar internal state becomes corrupted
  - Not a defect in application logic, but test infrastructure limitation
- Workaround: Single-test execution works; developers typically verify with small test subsets
- Mitigation: 
  - Tests already use `pytest.fixture()` with session/module scope where possible
  - `test_batch_ocr_dialog.py` uses module-level `tk_root` fixture to share one Tk() instance
  - Proper `try/except tk.TclError` wrapping in teardown paths
- Future fixes (deferred):
  - Run pytest with `pytest-xdist` for process-level parallelization (separate Tcl/Tk per process)
  - Strengthen `conftest.py` fixture teardown to force garbage collection between tests
  - Investigate Tk mainloop() state cleanup between test functions

**Gemini Generation Gating for 400 Error (v1.8.1, Regression Risk):**
- Symptoms: Gemini API returns 400 INVALID_ARGUMENT when temperature / sampling parameters are sent to gemini-3.x models
- Files: `pagefolio/ocr_providers/gemini.py` (`_is_legacy_gemini`, `_build_generation_config`, `_model_generation`)
- Current Mitigation (v1.8.1): 
  - Introduced `_model_generation()` regex to detect model generation from ID
  - `_is_legacy_gemini()` gates temperature / thinkingConfig parameters to gemini-2.x and below only
  - Pattern: `gemini-(\d+)` extracts leading digit; if not found (e.g., `gemini-flash-latest`), defaults to new generation (safe-side)
  - RECOMMENDED_MODELS updated to include `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`
- Potential Risk: 
  - If Google introduces model IDs like `gemini-exp-*` (experimental) or date-suffixed variants, regex may misidentify generation
  - Fallback of "unknown = new generation (parameters omitted)" is safe but loses temperature control for experimental models
  - Temperature parameter absence is undetectable to UI; users won't know it's being ignored for new models
- Deferred Mitigations (next milestone):
  - Add UI warning in LLM Config dialog: "New Gemini models (3.x+) do not support temperature control"
  - Measure actual response time / token consumption for new Gemini models with thinking mode enabled
  - Consider explicit model-version allowlist instead of regex (more maintainable but requires updates per new model)

## Security Considerations

**API Key Storage in Session Memory:**
- Risk: `app._session_api_keys` dictionary holds live API keys in memory (not persisted, but accessible)
- Files: `pagefolio/dialogs/llm_config/dialog.py`, `pagefolio/ocr.py`
- Current Mitigation: 
  - Settings file never persists keys (registry.py / settings.py `_SENSITIVE_KEYS` guard)
  - Keys only stored in `_session_api_keys` (in-process memory) or environment variables
  - Environment variables read at startup, not displayed in settings UI
  - Sensitive key names defined centrally in `pagefolio/ocr_providers/registry.py`
- Remaining Exposure:
  - Process memory dumping could expose keys (e.g., debugger, process dump)
  - No encryption of in-memory storage (keys are plaintext strings)
  - Keys logged at error level (with values redacted, but names logged)
- Recommendations:
  - Document in CLAUDE.md that API keys should not be committed to settings files
  - Consider OS keystore integration for future versions (currently out of scope per Deferred Items)
  - Add warning in UI: "API keys stored in this session only; not saved to disk"

**Environment Variable Exposure in Process Context:**
- Risk: Environment variables (ANTHROPIC_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, RUNPOD_API_KEY) visible to child processes
- Files: `pagefolio/ocr_providers/registry.py` (env var resolution), `pagefolio/ocr.py` (build_provider)
- Impact: Child processes (e.g., print handler, subprocess calls) inherit environment
- Mitigation: PageFolio doesn't spawn subprocesses with user-controlled arguments; print uses OS-level file print
- Recommendation: Document that users should not source shell session with API keys when running PageFolio

**Circular Import Prevention Constraints:**
- Risk: `pagefolio/ocr_providers/registry.py` strictly limited to stdlib-only imports to prevent circular dependency
- Files: `pagefolio/ocr_providers/registry.py` (1 file), `pagefolio/settings.py` (consumer)
- Constraint: Future changes to registry.py cannot import pagefolio internal modules (settings, UI, etc.)
- Impact: 
  - New provider additions must update two files (registry.py + provider class)
  - Architectural constraint makes some refactorings infeasible
- Mitigation: Constraint documented in registry.py module docstring and CLAUDE.md
- Risk: If maintainer is unaware, may accidentally break the constraint, causing import failures

## Performance Bottlenecks

**OCR Result Text Accumulation:**
- Problem: `ocr_dialog.py` progressively appends OCR results to a Tk Text widget (`self._result_text.insert(...)`)
- Files: `pagefolio/ocr_dialog.py` (result display section, ~2100-2300 lines)
- Impact:
  - Each page result insert triggers Text widget re-rendering
  - Very large PDFs (500+ pages) with long OCR results cause UI slowdown during OCR
  - Text buffer can grow unbounded (though typically truncated for display)
- Current Mitigation:
  - Results displayed in scrollable Text widget (Tkinter native, reasonably efficient)
  - Summary tab separated from result tab (lazy rendering)
- Potential Improvement:
  - Consider virtualizing result display (render only visible portion)
  - Or pre-render markdown to simpler text format (current _insert_markdown already does this)
  - Limit result display to last N results (bounded history)

**ThreadPoolExecutor Concurrency with fitz Document Rendering:**
- Problem: OCR parallelization via ThreadPoolExecutor passes only base64-encoded image bytes to workers (fitz Document never leaves main thread)
- Files: `pagefolio/ocr.py` (run_parallel function), `pagefolio/ocr_dialog.py` (producer flow)
- Impact:
  - Main thread is single-bottleneck for all PDF rendering to PNG (even when OCR ← workers are idle)
  - Effective parallelism limited by main thread PNG generation rate
  - Concurrent workers often blocked waiting for next batch
- Constraint: fitz.Document is not thread-safe, so all rendering must stay on main thread
- Current Design: Producer (_render_next_page) runs on main thread via root.after() chaining; consumer (workers) process only bytes
- Mitigation: This is an architectural constraint, not a bug; design choice prioritizes safety over throughput
- Observation: For typical use (small PDFs), this is not noticeable; only very large batches or slow network would bottleneck

**Thumbnail Virtualization Limits:**
- Problem: Thumbnail cache holds up to 300 entries (THUMB_CACHE_MAX); large PDFs (500+ pages) require cache misses
- Files: `pagefolio/thumb_cache.py`, `pagefolio/pagination.py` (window computation)
- Impact:
  - Visible pagination window scrolling may trigger thumbnail regeneration
  - Subsequent scroll back triggers re-generation again (cache miss)
  - For 1000+ page PDFs, frequent cache thrashing expected
- Current Mitigation:
  - LRU cache (keep_warm parameter) prioritizes visible range
  - Windows computed by pagination.py pure functions (fast)
  - Thumbnail generation spawned as background task (no UI blocking)
- User Impact: Minimal for typical workflows; only noticeable for continuous rapid scrolling in massive PDFs
- Future: Mentioned in Deferred Items as v2 candidate for react-window-style advanced virtualization

## Fragile Areas

**Undo/Redo Blob Lifecycle Management:**
- Files: `pagefolio/undo_store.py`, `pagefolio/file_ops.py`
- Why Fragile:
  - UndoBlobStore manages tempfile lifecycle (create, load, release, purge)
  - Incorrect dispose sequence can leak temporary files or cause memory leaks
  - MemBlob/FileBlob release() calls must match put() calls
  - undo/redo stack deque eviction must invoke release() before discarding
- Current Safeguards:
  - __del__ methods provide fallback cleanup for unreleased Blobs (logs warning)
  - atexit handler forces purge() at interpreter shutdown
  - sys.is_finalizing() prevents double-cleanup during shutdown
  - Double-release detection (warning log only, no crash)
  - Tests include leak detection fixtures
- Risk: Future changes to undo stack manipulation (e.g., skipping _push_evicting) could bypass release logic
- Safe Modification: 
  - Always use FileOpsMixin methods (_push_evicting, _clear_redo_stack, etc.) for stack manipulation
  - Never call deque.append/clear directly
  - Never call blob.load() after release()
  - Run tests with blob leak detection enabled (fixture checks file_count() before/after)

**Batch OCR File-by-File Sequential Constraint:**
- Files: `pagefolio/dialogs/batch_ocr.py`, `pagefolio/batch_ocr_state.py`, `pagefolio/ocr_engine.py`
- Why Fragile:
  - Multiple fitz.Document instances cannot coexist across thread boundaries
  - Batch queue processes files strictly sequentially (one file's pages entirely before next file)
  - If parallelization is added, page-level producer and file-level producer must not overlap
- Current Safeguards:
  - Architecture explicitly single-file-at-a-time (no multi-file parallelization)
  - file_ops.py open/close/reopen guards prevent Document sharing
  - Tests enforce sequential assumption
- Risk: Future optimization to parallelize across files (e.g., 3 files in parallel) would break fitz constraint
- Safe Modification: Document constraint clearly in batch_ocr.py, refer to CLAUDE.md existing note

**Registry Module Isolation:**
- Files: `pagefolio/ocr_providers/registry.py`
- Why Fragile:
  - registry.py must remain stdlib-only to prevent circular imports
  - Any import of pagefolio.settings or UI modules breaks the constraint
  - Violation would cause import failure at startup (settings.py calls sensitive_keys() at module level)
- Current Safeguards:
  - Constraint documented in module docstring and CLAUDE.md
  - No internal imports present
  - Code review should catch violations
- Risk: Maintainer may accidentally import settings.py or theme.py thinking it's safe
- Safe Modification: 
  - Before adding any import, verify it's stdlib-only (os, re, sys, logging, threading, queue, etc.)
  - Never reference pagefolio.* modules

**OCRDialog LLM Settings Callback Consistency:**
- Files: `pagefolio/dialogs/llm_config/sections.py`, `pagefolio/ocr_dialog.py`
- Why Fragile:
  - LLMConfigDialog._apply_llm_settings modifies app.settings but doesn't call app._update_ocr_buttons_state()
  - If user opens LLMConfigDialog from within OCRDialog and changes provider, OCR button availability may not update
  - Edge case: Happens only if settings dialog is open and provider changes from/to "off"
- Current Safeguards:
  - OCRDialog checks provider availability at run-time (check happens at button click, not at dialog open)
  - Default provider "off" (LM Studio local) is always available
  - Real-world impact: User would need to close/reopen dialog to see button state change
- Observation: v1.4.0 Phase 04 flagged as WARNING (not BLOCKER); existing users work around via dialog close/reopen
- Risk: Future changes to provider availability logic may create inconsistencies
- Safe Modification: 
  - Any settings change that affects button availability should call app._update_ocr_buttons_state()
  - Or refactor to model state changes event-driven (publish-subscribe pattern)

## Scaling Limits

**Undo Stack Size Limit (20 operations):**
- Limit: MAX_UNDO = 20 hard-coded in `pagefolio/app.py`
- Files: `pagefolio/app.py` (line ~270 constant), `pagefolio/file_ops.py` (stack management)
- Impact:
  - Users can only undo 20 operations; older operations are discarded
  - For large batch operations (e.g., 100 page delete), not all can be undone individually
  - High-res image PDFs: 20 operations may consume 100+ MB RAM (mitigated by UndoBlobStore offload)
- Rationale: Memory vs. usability tradeoff; 20 operations typically sufficient for most workflows
- User Experience: Sufficient for typical editing sessions; power users may hit limit
- Current Mitigations:
  - Each undo op captures only necessary delta (not full PDF)
  - UndoBlobStore offloads large pages to tempfile (64KB threshold)
  - Redo stack cleared on new operation (prevents memory growth)
- Future Consideration: Configurable limit via settings (currently out of scope)

**Thumbnail Cache Limit (300 entries):**
- Limit: THUMB_CACHE_MAX = 300 in `pagefolio/thumb_cache.py`
- Files: `pagefolio/thumb_cache.py`, `pagefolio/app.py` (cache initialization)
- Impact:
  - PDFs with 300+ pages trigger cache misses as pagination scrolls
  - Cache hit ratio degrades for rapid scrolling in large documents
- Rationale: Memory constraint (typically ~50-100 MB for 300 entries at default zoom)
- Current Mitigation: LRU eviction, prioritized re-rendering for visible range
- User Impact: Smooth scrolling for up to 300 pages; minor lag for larger PDFs on slower systems
- Observation: Not user-configurable (FrameWork design limitation noted in CLAUDE.md)

**Test Suite Tcl/Tk Resource Exhaustion (1100+ tests):**
- Limit: pytest running full suite (1109 tests) occasionally fails with TclError
- Files: All `tests/test_*.py` files using tk.Tk()
- Impact:
  - ~2 random test failures per full run (flaky, not deterministic)
  - Failure is infrastructure-level (Tcl theme loading), not application logic
  - Blocks CI/CD if strict test passing required
  - Developers forced to run subset of tests locally
- Mitigation: 
  - Tests structured with module-level shared tk.Tk() roots where possible
  - Proper exception handling for tk.TclError in teardown
  - conftest.py provides shared fixtures
- Future Fixes: Mentioned in STATE.md; pytest-xdist process-level parallelization suggested

**PDF Size and Page Count Scalability:**
- Observation: No hard limits enforced; tested up to 120 pages (stress test)
- Performance:
  - Preview rendering: ~1-2 seconds for typical 5 MB PDF
  - OCR: Limited by API rate limits and network, not PageFolio itself
  - Thumbnail generation: Linear scaling ~100 ms per page at default zoom
  - Batch OCR: Tested with multiple PDFs; no regression observed up to 20 files × 50 pages
- Estimated Practical Limits (unverified):
  - Individual PDF: ~1000 pages (before UI becomes noticeably sluggish due to thumbnail cache misses)
  - Batch queue: Tested up to 20 files; probably scales to 100+ with time (sequential, no hard limit)
- Risk: Very large PDFs (500+ pages) or batch jobs (100+ files) not well-tested; recommend conservative use

## Missing Critical Features

**Undo/Redo Test Coverage for Structural Operations:**
- Feature Gap: Four-step redo cycles (undo → redo → undo → undo) not comprehensive for all operations
- Files: `tests/test_pdf_ops.py` (page operation tests)
- What's Tested: delete, insert (both with full 4-step cycle)
- What's Missing: duplicate, merge, merge_resize with full cycle
- Risk: Could hide restoration bugs similar to v1.8.0 Phase 6 insert_redo fix (D-17 in STATE.md)
- Priority: Medium (no active issues reported, but historical precedent suggests risk)
- Recommendation: Add 4-step cycle tests for duplicate / merge / merge_resize operations

**New Gemini Model Awareness UI:**
- Feature Gap: LLM Config dialog temperature field has no warning that new Gemini models ignore it
- Files: `pagefolio/dialogs/llm_config/sections.py` (temperature field rendering)
- Impact: Users selecting gemini-3.x models may expect temperature control that is silently ignored
- Deferred in v1.8.1 (SUMMARY.md, item 3②)
- Implementation: Add note label near temperature field: "Note: New Gemini models (3.x+) do not support temperature control"

**New Gemini Thinking Mode Measurements:**
- Feature Gap: No data on actual response time / token consumption for gemini-3.x with thinking enabled
- Files: N/A (documentation/testing gap, not code)
- Impact: Users cannot predict cost/time impact of enabling thinking mode on new models
- Deferred in v1.8.1 (GSD-AUDIT-DIRECTIVE item 3③, SUMMARY.md)
- Recommendation: Manual testing with real Gemini API + documentation of findings

## Test Coverage Gaps

**OCR Provider Fallback Integration:**
- What's not tested: Full fallback chain (OCR fails on primary → retries → tries secondary provider)
- Files: `pagefolio/ocr_fallback.py`, `pagefolio/dialogs/ocr_dialog.py`
- Risk: Fallback provider selection dialog / actual provider switch not E2E tested with real failures
- Current Tests: Unit tests for `next_fallback_candidate()` logic; E2E tests stub provider failures

**Batch OCR Multi-File Cancellation:**
- What's not tested: User cancels during file N; queue state transitions; unprocessed files still marked runnable
- Files: `pagefolio/dialogs/batch_ocr.py`, `pagefolio/batch_ocr_state.py`
- Risk: Cancelled batch may leave some files in inconsistent state
- Current Tests: Batch state unit tests, but UI cancellation flow is tested with stubs only

**Plugin Lifecycle Edge Cases:**
- What's not tested: Plugin crashes during on_page_rotate callback; UI recovery
- Files: `pagefolio/plugins.py`, `pagefolio/app.py`
- Risk: Buggy plugin could crash OCR thread or main UI loop
- Current Mitigation: Each plugin callback wrapped in try/except (logs error, continues)
- Recommendation: Add E2E test with intentionally-crashing plugin fixture

---

*Concerns audit: 2026-07-22*
