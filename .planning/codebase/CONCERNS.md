# Codebase Concerns

**Analysis Date:** 2026-06-10

## Tech Debt

**Undo/Redo memory overhead with large PDFs:**
- Issue: Each undo snapshot stores complete PDF binary (`doc.tobytes()` returns full PDF bytes)
- Files: `pagefolio/app.py` (line 35, `MAX_UNDO = 20`), `pagefolio/file_ops.py` (lines 23-63)
- Impact: With 20 snapshots and large PDFs (50MB+), heap usage can exceed 1GB. Users of large documents will experience slow Undo/Redo and potential OOM crashes
- Fix approach: Implement delta-based undo (store only page-level changes, not full PDF) or reduce `MAX_UNDO` limit with warning UI; add memory pressure detection to prevent heap overflow

**Tkinter main thread blocking during OCR rendering:**
- Issue: `page_to_png_b64()` calls `page.get_pixmap()` on main thread, blocking UI during base64 encoding
- Files: `pagefolio/ocr.py` (lines 139-147), called from OCRDialog `_on_run` before worker threads launch
- Impact: UI freezes for 1-3 seconds on large PDFs while rendering all page images to base64 simultaneously
- Fix approach: Dispatch base64 rendering to background thread pool with generation counter guard, or lazy-render pages as they're queued

**Global mutable singleton C (theme dict) with no locking:**
- Issue: Module-level `C = dict(THEMES["dark"])` in `pagefolio/constants.py` is mutated by `_apply_theme()` without synchronization
- Files: `pagefolio/constants.py`, `pagefolio/settings.py` (line 128), `pagefolio/app.py` (line 51)
- Impact: If UI rebuild occurs while background thread reads `C["BG_DARK"]`, color may be inconsistent or cause reference errors
- Fix approach: Add threading.Lock around `C` mutations, or use immutable color lookups by theme name

**Module-level font size singleton without locking:**
- Issue: `_current_font_size` in `pagefolio/settings.py` (line 140) is global mutable state updated by settings dialog without locks
- Files: `pagefolio/settings.py` (lines 140-151)
- Impact: If widget creation races with font size change, fonts may render at wrong sizes
- Fix approach: Use thread-safe setter/getter with Lock, or pass font size as parameter instead of relying on global

## Known Bugs

**OCR dialog stale callback crashes after dialog close:**
- Symptoms: If OCR dialog is closed and reopened quickly, daemon threads from previous run may call `on_done` callback on destroyed dialog widget, raising RuntimeError
- Files: `pagefolio/ocr_dialog.py` (lines 118-120, generation counter), `pagefolio/ocr.py` (lines 278-282, on_done callback)
- Trigger: Close OCR dialog mid-operation (before all workers complete), reopen same dialog
- Workaround: Check `winfo_exists()` before updating widgets in on_done callback (partially done at line 119 with `_run_gen` but callback invokes may still reference destroyed canvas/labels)

**CropBox silently fails on invalid rects without fallback:**
- Symptoms: Bulk crop on pages with wildly different aspect ratios may silently skip pages if computed rect falls below 1pt
- Files: `pagefolio/page_ops.py` (lines 258-268)
- Trigger: Crop a large landscape page and small portrait page together using relative coordinates
- Workaround: Bulk crop now logs but doesn't warn user when pages are skipped due to size validation

**Thumbnail cache never evicted in long sessions:**
- Symptoms: Memory grows unbounded as user opens many PDFs; old thumbnails persist in `self.thumb_cache`
- Files: `pagefolio/viewer.py` (lines 133-142, `_get_thumb_photo`)
- Trigger: Load 50+ PDFs sequentially in one session; heap grows to 200MB+
- Workaround: Cache is cleared only on file close or UI rebuild, not when switching between documents

**D&D multi-page move order computation fragile to edge cases:**
- Symptoms: Moving selected pages to the end of document may place them incorrectly if destination is exactly at doc length
- Files: `pagefolio/dnd.py` (lines 94-117, `_dnd_drop`)
- Trigger: Select pages 0-5 in 10-page doc, drag to end (position 10)
- Workaround: Logic at line 104 tries to adjust for offset, but computation is brittle; should use explicit `doc.select([reordered_indices])`

## Security Considerations

**API keys stored in session memory only, but no session timeout:**
- Risk: `app._session_api_keys` dict holds plaintext Claude/Gemini keys in memory; no automatic clearing on inactivity
- Files: `pagefolio/app.py` (line 71), `pagefolio/ocr.py` (lines 89-136, `_resolve_api_key`)
- Current mitigation: Keys not saved to disk (`_SENSITIVE_KEYS` guard in `pagefolio/settings.py`), but process keeps them until exit
- Recommendations: Add 30-minute inactivity timeout to clear `_session_api_keys`, or prompt user to re-enter API key on each OCR session

**base64 PDF page encoding sent unencrypted to Claude/Gemini:**
- Risk: Page images (base64 PNG) transmitted over HTTPS, but Anthropic/Google can see page content
- Files: `pagefolio/ocr.py` (line 147, `base64.b64encode`), `pagefolio/ocr_providers.py` (Claude/Gemini provider implementations)
- Current mitigation: HTTPS encryption in transit, cloud providers' privacy policies
- Recommendations: Document this clearly in OCR setup dialog; add warning checkbox before first OCR to private documents

**No validation of OCR provider URL (LM Studio):**
- Risk: User can set LM Studio URL to malicious endpoint; app will send all page images there
- Files: `pagefolio/dialogs/llm_config.py` (LM Studio URL entry field), `pagefolio/ocr_providers.py` (line 86+, LMStudioProvider)
- Current mitigation: None; localhost is default but user can change
- Recommendations: Add URL validation (localhost/127.0.0.1 allowed by default), or show host warning dialog

**Retry-After cap prevents DOS but caps legitimate long waits:**
- Risk: Server sends legitimate Retry-After=120s, clamped to 60s; OCR resumes before server ready
- Files: `pagefolio/ocr.py` (lines 54-55, `RETRY_AFTER_CAP = 60.0`), (lines 293-298, clamp applied)
- Current mitigation: Hard cap at 60s prevents infinite wait DoS
- Recommendations: Log when cap is applied so users know OCR may fail; add UI setting to adjust cap per provider

## Performance Bottlenecks

**Thumbnail rendering on every page change:**
- Problem: Each page navigation calls `_build_thumbnails()` which renders ALL visible thumbnails even if only 1 page changed
- Files: `pagefolio/viewer.py` (lines 145-147, `_refresh_all`), `pagefolio/ui_builder.py` (thumbnail building)
- Cause: No dirty-tracking; always full rebuild
- Improvement path: Cache which thumbnails are visible, only render new ones on page change; mark others as stale

**OCR producer-consumer buffer may hold all page base64s if consumers slow:**
- Problem: Even with `maxsize=workers+1` bounded buffer, if OCR API is slow, producer may still pre-render many pages to base64 before consumers drain queue
- Files: `pagefolio/ocr.py` (lines 215-220, buffer setup), (lines 226-255, producer loop)
- Cause: Buffer size only prevents producer blocking, not total base64 memory
- Improvement path: Render pages on-demand per queue slot (render only when slot is empty), or use callback-based backpressure

**Language dict lookup O(n) on every _t() call:**
- Problem: `_t("key")` does `LANG[self.lang].get(key, LANG["ja"].get(key, key))` each call
- Files: `pagefolio/app.py` (lines 308-310, `_t` method)
- Cause: No caching of current language dict reference
- Improvement path: Cache `self._current_lang_dict = LANG[self.lang]` on init and lang change

**PDF merge without deduplication of fonts/resources:**
- Problem: When merging PDFs, PyMuPDF copies all font objects and resources separately; no optimization
- Files: `pagefolio/page_ops.py` (line 340, `self.doc.insert_pdf(src)`), `pagefolio/file_ops.py` (line 42, `tmp.insert_pdf(self.doc)`)
- Cause: PyMuPDF limitation; no high-level API for resource merging
- Improvement path: Use PyMuPDF's low-level stream manipulation, or warn users that merged PDFs may be larger than sum of parts

## Fragile Areas

**Crop coordinate transformation between canvas pixels and PDF coordinates:**
- Files: `pagefolio/page_ops.py` (lines 186-206, single crop), (lines 223-257, bulk crop)
- Why fragile: Calculation is spread across multiple scale factors (`zoom * 1.5`, `img_offset=10`, relative ratios), prone to off-by-one errors if zoom or offset changes
- Safe modification: Add `_crop_page_to_canvas()` and `_canvas_to_page_crop()` pure functions with unit tests; use them consistently
- Test coverage: `tests/test_pdf_ops.py` has basic crop tests but no edge cases (boundary pixels, very small crops)

**OCR dialog thread lifecycle with generation counters:**
- Files: `pagefolio/ocr_dialog.py` (lines 105-120, threading setup), (lines 341-355, callback wrapping)
- Why fragile: Multiple daemon threads check `_run_gen` and `winfo_exists()` but generation is incremented on dialog close; race condition possible if thread sleeps in Retry-After while gen increments
- Safe modification: Use explicit threading.Event() for cancellation; don't rely on generation counter alone
- Test coverage: `tests/test_provider_ui.py` mocks some threading but doesn't test stale callback scenario

**Plugin UI injection with dynamic frame destruction:**
- Files: `pagefolio/app.py` (lines 322-341, `_build_plugin_ui`)
- Why fragile: Calls `plugin.build_ui(self, pf)` where `pf` is a plain tk.Frame; if plugin stores reference to `pf`, then UI rebuild destroys it without notification
- Safe modification: Add plugin lifecycle hook `on_ui_rebuild`, or wrap plugin frame in try/except with error recovery
- Test coverage: `tests/test_plugins.py` loads plugins but doesn't test UI rebuild scenario

**Undo/Redo state machine with missing edge cases:**
- Files: `pagefolio/file_ops.py` (lines 65-82, undo/redo), (lines 226-350, state restoration)
- Why fragile: Complex state transitions; merge/merge_resize have multiple op types (merge/merge_undo/merge_redo); inverse computation is not formally verified
- Safe modification: Add invariant checks (e.g., after restore, `len(doc) + len(redo_stack)` should be predictable), or formalize state machine as enum
- Test coverage: `tests/test_pdf_ops.py` tests basic undo but not complex chains (crop→merge→undo→redo→crop)

## Scaling Limits

**Undo stack hardcoded to 20 snapshots:**
- Current capacity: Max 20 PDF snapshots in deque
- Limit: User with 100MB PDF can only undo 20 operations before oldest is discarded; with 50MB PDFs, max ~1GB heap used
- Scaling path: Implement configurable limit UI (5/20/50 snapshots), or switch to delta-based undo (no size limit)

**Thumbnail grid renders in single pass:**
- Current capacity: On modern GPU, ~100 thumbnails per second; 1000-page doc takes ~10 seconds to scroll fully
- Limit: Users with 2000+ page PDFs will experience janky thumbnail scrolling
- Scaling path: Implement lazy thumbnail rendering (only render visible + adjacent), or use thread pool with generation counters

**OCR batch size unbounded:**
- Current capacity: Can submit 1000+ pages to OCR in one dialog; producer enqueues all base64s before any consumer reads
- Limit: Memory usage grows to document size * OCR_SCALE (e.g., 500MB for 100MB PDF at 1.5x scale)
- Scaling path: Limit batch to max 50-100 pages per dialog invocation, or implement streaming OCR with per-page callbacks

## Dependencies at Risk

**PyMuPDF (fitz) version 1.27.2.2:**
- Risk: Known upstream issues with corrupted PDFs and CropBox validation; new versions may change API
- Impact: If PDF is malformed, `page.get_pixmap()` crashes silently or returns blank; `set_cropbox()` validation may reject valid rects
- Migration plan: Monitor PyMuPDF releases; test upgrading to 1.28.x quarterly; maintain fallback to 1.26.x if critical bugs found

**tkinterdnd2 0.4.3 (undocumented dependency):**
- Risk: Windows-only; requires compilation; may not work with Python 3.12+
- Impact: If DnD breaks after Python upgrade, app loses drag-and-drop functionality
- Migration plan: Evaluate tkdnd fork or fallback to file dialog only; add platform detection to warn macOS/Linux users

**Python 3.8 type hint compatibility:**
- Risk: Code uses `dict[str, tuple[float, float]]` (PEP 604 style) introduced in 3.10
- Impact: Will fail at import on Python 3.8/3.9 with syntax error
- Migration plan: Use `Dict[str, Tuple[float, float]]` from `typing` module in 3.8-compatible code; found in `pagefolio/ocr_dialog.py` line 29

## Missing Critical Features

**No progress indication during large PDF load:**
- Problem: Opening 500MB PDF hangs UI for 10+ seconds with no feedback
- Blocks: Users think app crashed and force-quit
- Recommendations: Show splash screen with "Loading... 45%" during `fitz.open()` and page count detection

**No PDF password/encryption handling:**
- Problem: Encrypted PDFs fail silently at open time
- Blocks: Users cannot edit protected PDFs, no error message
- Recommendations: Detect encrypted PDF, show password dialog before opening; handle `fitz.FileError` with encryption check

**No memory usage monitoring or warnings:**
- Problem: User can load multiple large PDFs + do Undo/Redo without knowing heap is at 90%
- Blocks: No graceful degradation; app just OOMs and crashes
- Recommendations: Monitor `psutil.Process().memory_info()`, warn at 80% heap, auto-clear old undo snapshots at 90%

**No OCR cost calculator before batch submission:**
- Problem: User can submit 1000 pages to Claude OCR at $0.003/page without seeing cost first
- Blocks: Surprise billing
- Recommendations: Calculate estimated cost before showing "Run OCR" button; add dry-run mode or per-page approval

## Test Coverage Gaps

**OCR dialog daemon thread cleanup after dialog close:**
- What's not tested: Closing OCR dialog while workers are mid-request; checking that stale callbacks don't crash
- Files: `pagefolio/ocr_dialog.py` (threading internals)
- Risk: Undetected race condition may cause production crash
- Priority: High

**Undo/Redo complex chains (crop + merge + move + undo + redo):**
- What's not tested: Multi-operation undo sequences; verifying state consistency after complex chains
- Files: `pagefolio/file_ops.py` (_restore_state)
- Risk: Silent state corruption undetected; user loses data
- Priority: High

**CropBox boundary conditions (0-size rects, inverted coords, pages near margin):**
- What's not tested: Edge cases in crop validation; very small crops (1-2 pixels)
- Files: `pagefolio/page_ops.py` (_crop_page)
- Risk: Rare user action crashes or leaves PDF corrupted
- Priority: Medium

**Plugin lifecycle with UI rebuild:**
- What's not tested: Loading plugin, changing theme, verify plugin UI survives rebuild
- Files: `pagefolio/app.py` (_rebuild_ui, _build_plugin_ui)
- Risk: Plugin UI disappears silently after theme change
- Priority: Medium

**D&D multi-page move edge cases (end of doc, before/after self):**
- What's not tested: Drop selected pages at document end; drop between self-selected pages
- Files: `pagefolio/dnd.py` (_dnd_drop)
- Risk: Page order corrupted or pages lost
- Priority: Medium

**Settings file corruption recovery:**
- What's not tested: Corrupt `pagefolio_settings.json` (truncated, invalid JSON); app should fallback gracefully
- Files: `pagefolio/settings.py` (_load_settings)
- Risk: App fails to start if settings corrupted by manual edit or crash during save
- Priority: Low

---

*Concerns audit: 2026-06-10*
