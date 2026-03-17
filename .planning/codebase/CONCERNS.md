# Codebase Concerns

**Analysis Date:** 2026-03-17

## Tech Debt

**Broad Exception Handling with Silent Failures:**
- Issue: Multiple locations use bare `except Exception:` followed by `pass`, silently swallowing all errors without logging or user feedback. Makes debugging difficult.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 374-375, 384-385, 552-554, 1115-1118, 1817-1818, 2060-2061, 2250-2251)
- Impact: Plugin loading failures, settings save failures, UI update failures go undetected. Users have no visibility into what went wrong.
- Fix approach: Replace silent exception handlers with at minimum `traceback.print_exc()` for debugging, or better: log to console or display user-friendly error messages where appropriate. Distinguish between expected/ignorable errors (e.g., optional windnd import) and unexpected failures (e.g., PDF operations).

**Global Mutable State:**
- Issue: Global `C` dictionary (theme colors) and global `_current_font_size` variable are modified at runtime via `_apply_theme()` and `_apply_settings()`. This makes the code less testable and harder to reason about state.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 59, 620-621, 1900-1901)
- Impact: Color and font changes are applied globally but only some dialogs are aware of updates. Race conditions if settings are applied while dialogs are rendering.
- Fix approach: Inject theme and font configuration as explicit parameters to classes rather than relying on global `C` dict. Pass theme dict to dialog constructors.

**Version Mismatch:**
- Issue: About dialog hardcodes version as `v0.9.2` (line 1953) but `CLAUDE.md` and project indicate `v0.9.4` is current. This will grow stale.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (line 1953)
- Impact: Users see outdated version in About dialog, misleading about actual application version.
- Fix approach: Define version string once at module level (e.g., `__version__ = "0.9.4"`), use in About dialog and elsewhere.

**Undo/Redo Memory Usage:**
- Issue: `_save_undo()` calls `self.doc.tobytes()` which serializes the entire PDF to memory. With `MAX_UNDO = 20`, this can consume significant RAM for large PDFs.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 985-996)
- Impact: Large PDFs (100+ MB) can cause excessive memory usage if user performs many operations. No cleanup when undo stack exceeds max.
- Fix approach: Consider implementing delta-based undo (storing only changes) or using temporary files for large PDFs. Add memory usage warnings for large files.

**D&D Specific State Variables Not Initialized:**
- Issue: `_dnd_dragging` is set in `on_motion` closure but only initialized when `on_press` is called. If motion occurs before press, `_dnd_dragging` is undefined.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1557, 1564-1565)
- Impact: Unlikely but possible race condition in rapid clicking scenarios.
- Fix approach: Initialize `self._dnd_dragging = False` in `__init__` alongside other D&D state vars.

**Plugin Module Name Aliasing:**
- Issue: Plugin system registers `sys.modules["pdf_editor"]` as alias to pagefolio module to work around import name mismatch. This is a workaround for inconsistent naming (`pagefolio.py` vs `pdf_editor` import).
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 526-530)
- Impact: Plugins that directly import `pagefolio` will fail. Plugins must use legacy `pdf_editor` import name.
- Fix approach: Either rename file to `pdf_editor.py` and update all references, or update plugin documentation to use `import pagefolio` and update base class import path.

## Known Bugs

**Rotated Pages Don't Reflect in Immediate Preview:**
- Symptoms: After rotating a page with buttons, the preview canvas shows the old unrotated version until user navigates to another page and back.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1144-1155)
- Trigger: Click rotation button (left/right/180), observe preview unchanged until page navigation
- Root cause: `_rotate_selected()` calls `_refresh_all()` which updates thumbnails and page label but `_show_preview()` is called as part of refresh, using `self.current_page` which hasn't changed. The cached rotation isn't immediately visible because `fitz` applies rotation as metadata.
- Workaround: Navigate to another page and back to see rotated version
- Fix approach: Ensure `_show_preview()` invalidates any cached pixmap for rotated pages or explicitly refresh rotation state before rendering

**Crop Mode Toggle Leaves Overlay Visible on Page Change:**
- Symptoms: If crop mode is ON and user clicks next/prev page, the crop overlay (dark mask) persists but is associated with wrong page
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1454-1464)
- Trigger: Enable crop mode, drag selection, click next page button
- Root cause: `_prev_page()` and `_next_page()` don't reset crop state before calling `_refresh_all()`
- Workaround: Click crop mode OFF button before navigating pages
- Fix approach: Reset `self.crop_mode = False` and call `self._clear_crop_overlay()` in navigation methods

**Drag-and-Drop Destination Index Calculation Off-by-One:**
- Symptoms: When dragging page 3 to position after page 1, it sometimes ends up at wrong position due to `dest` vs `actual_dest` mismatch
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1789-1801)
- Trigger: Drag page from lower index up to before its position (e.g., move page 5 to position 2)
- Root cause: Logic at line 1800 (`actual_dest = dest if dest < src else dest - 1`) attempts to compensate for `fitz.move_page` semantics but is complex and error-prone
- Workaround: Drag to adjacent positions or navigate menu option
- Fix approach: Simplify D&D logic by using `fitz.delete_page()` + `fitz.insert_pdf()` pattern for clearer semantics, or add comprehensive test cases for all D&D scenarios

## Security Considerations

**No Input Validation for Crop Coordinates:**
- Risk: User-supplied drag coordinates converted to PDF coordinates without bounds checking until `set_cropbox` is called. Malformed coordinates could trigger pymupdf errors.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1267-1302)
- Current mitigation: `CropBox` is clamped to `MediaBox` with epsilon margin (line 1288-1293). Validation catches invalid rects (line 1294).
- Recommendations: Add pre-validation of drag coordinates; log/audit crop operations; consider adding undo prompt for large crop changes

**No Validation of Inserted PDF Paths:**
- Risk: File paths from file dialogs are passed directly to `fitz.open()` without checking file existence or permissions.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1345-1369, 1382-1396)
- Current mitigation: Exception handling wraps file operations; errors show to user.
- Recommendations: Validate that paths are readable before opening; check file size to warn on extremely large PDFs; consider sandboxing PDF parsing

**Plugin Code Execution Without Sandboxing:**
- Risk: Plugin system directly executes user Python code via `spec.loader.exec_module()` without any sandboxing or code inspection.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 517-554)
- Current mitigation: Plugins are loaded from local `plugins/` folder only (not downloaded). User must intentionally place `.py` files.
- Recommendations: Add plugin signing/checksum verification; log plugin code execution; add explicit user confirmation before loading new plugins; consider restricting plugin API surface

**Settings File Contains User Preferences (Low Risk):**
- Risk: `pagefolio_settings.json` is stored unencrypted in user directory, but contains only theme/font/lang settings (no sensitive data).
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 357-385)
- Current mitigation: Settings are non-critical; lost or corrupted settings simply revert to defaults.
- Recommendations: Continue current approach; if future versions store auth tokens or paths, implement encryption.

## Performance Bottlenecks

**Thumbnail Generation on Every Refresh:**
- Problem: `_build_thumbnails()` destroys all thumbnails and regenerates them even if only one page changed. For 100-page PDFs, this regenerates 99 unchanged thumbnails.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1528-1535)
- Cause: `_refresh_all()` always calls `_build_thumbnails()` to update selection/current page highlighting
- Current mitigation: `_refresh_thumbs_selection_only()` (line 1507) avoids regeneration for selection changes
- Improvement path: Call `_refresh_thumbs_selection_only()` more often; only call `_build_thumbnails()` when page count changes or doc is newly opened. Measure impact on 500+ page PDFs.

**Undo/Redo Serialization Overhead:**
- Problem: Each undo checkpoint serializes entire PDF to bytes (`self.doc.tobytes()` at line 989). For a 50 MB PDF, 20 checkpoints = 1 GB memory consumed.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 985-1033)
- Cause: Deep-copy approach necessary to preserve exact PDF state, but prohibitively expensive
- Improvement path: Limit undo stack to smaller default (e.g., 5 for large docs); add warning when PDF > 20 MB; consider per-operation undo (only remember last operation) for large files

**Canvas Scrollregion Update on Every Draw:**
- Problem: `_show_preview()` calls `self.preview_canvas.configure(scrollregion=...)` every time page is rendered, even if canvas size unchanged.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (line 1448-1449)
- Impact: Minor, but noticeable on slow machines; canvas recalculates scrollbars unnecessarily
- Improvement path: Cache previous scrollregion value; only update if dimensions changed

**Plugin UI Rebuild on Settings Change:**
- Problem: `_rebuild_ui()` destroys all widgets including plugin UIs, then rebuilds. For complex plugins, this is expensive and may lose plugin state.
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1907-1926)
- Cause: Theme/font change requires full rebuild due to hardcoded color references in every widget
- Improvement path: Implement dynamic theme updates without destroying widgets; pass theme as dict through widget tree so recoloring doesn't require rebuild

## Fragile Areas

**MergeOrderDialog Tight Coupling to MergeOrderDialog:**
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 2230-2372)
- Why fragile: Dialog directly modifies `self.paths` list (line 2348) which is the source of truth. If callback is cancelled, paths have been mutated. D&D reordering during dialog causes race condition if doc is modified.
- Safe modification: Treat `paths` as immutable; create new list for reordered paths; pass reordered copy to callback
- Test coverage: No unit tests for list reordering operations (up/down/remove)

**Crop Coordinate Conversion Between Canvas and PDF Space:**
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1241-1247, 1274-1293)
- Why fragile: Conversion uses magic constants `scale = self.zoom * 1.5` and `img_offset = 10`. If preview rendering changes, these offsets become incorrect and crops are misaligned.
- Safe modification: Store offset as instance variable set during `_show_preview()`; document scale factor choice
- Test coverage: No test for crop accuracy across different zoom levels

**Plugin Event Firing with No Error Isolation:**
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 592-600)
- Why fragile: If one plugin raises exception during event, remaining plugins don't fire. Exception bubbles up to calling code.
- Safe modification: Wrap each plugin callback in try-except within `fire_event()` to ensure all plugins execute regardless of failures
- Test coverage: No test for plugin error handling

**D&D State Machine with No Explicit State:**
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1537-1598)
- Why fragile: D&D state tracked via implicit variables `_dnd_src_idx`, `_dnd_dragging`, `_dnd_ghost`. Rapid clicks can leave state inconsistent (e.g., `_dnd_ghost` not destroyed if release event missed).
- Safe modification: Implement explicit state enum (IDLE, DRAGGING, etc.); guard state transitions
- Test coverage: No test for rapid click sequences or edge cases in D&D

## Scaling Limits

**Single-Page UI Document Structure:**
- Current capacity: Application works well up to ~500 pages; thumbnail generation becomes slow (10+ seconds)
- Limit: Beyond 1000 pages, thumbnail scrolling becomes noticeably sluggish due to Tkinter canvas limitations
- Scaling path: Implement virtual scrolling for thumbnails (render only visible thumbs); use background thread for thumbnail generation; consider replacing Tkinter with web-based UI for 5000+ page documents

**Memory for Large PDFs:**
- Current capacity: Handles 200 MB PDFs on machines with 4 GB RAM
- Limit: 500+ MB PDFs with undo enabled will cause memory pressure and slowdown
- Scaling path: Add option to disable undo for large files; implement streaming PDF parsing (if pymupdf supports it); add memory usage indicator/warning

**Color Theme Switching Performance:**
- Current capacity: Theme switch redraws ~2000 widgets instantly on typical 500-page document
- Limit: Beyond 10,000 widgets, full rebuild becomes noticeable (>1 second)
- Scaling path: Implement dynamic recoloring without widget destruction; batch style updates

## Dependencies at Risk

**pymupdf (fitz) Encryption Limitation:**
- Risk: Library cannot open password-protected PDFs even with correct password in some versions
- Impact: Users cannot edit encrypted PDFs, operation fails silently
- Current mitigation: Exception handling shows error to user
- Migration plan: Document limitation clearly; consider adding password prompt dialog; if needed, switch to PyPDF2 for encrypted PDF support (with performance tradeoff)

**windnd Optional Dependency:**
- Risk: D&D feature silently disabled if `windnd` not installed; no user feedback
- Impact: Windows users expect D&D to work; it fails silently
- Current mitigation: Exception handling at line 2388 silently skips if not available
- Migration plan: Show banner/notification if windnd not available; add documentation for optional feature installation

**Tkinter Platform-Specific Behaviors:**
- Risk: Windows-specific code (e.g., `os.startfile()` at line 2216) fails on non-Windows platforms
- Impact: Cross-platform distribution would require separate builds or code branching
- Current mitigation: Try-except fallback to `xdg-open` (line 2217-2220)
- Migration plan: If cross-platform support planned, abstract platform-specific code into helpers

## Missing Critical Features

**No PDF Encryption/Password Protection for Output:**
- Problem: Cannot save encrypted PDFs; edited documents lose original encryption
- Blocks: Users with sensitive documents cannot preserve confidentiality
- Fix approach: Expose `fitz.Document.save(..., encryption=)` parameters in save dialog; add password field to save-as dialog

**No Page Rotation State Preservation in Metadata:**
- Problem: Rotated pages show as rotated in preview but pymupdf applies rotation as MediaBox annotation, not permanent page transform
- Blocks: Some PDF readers may not honor rotation metadata consistently
- Fix approach: Document behavior; consider option to "flatten" rotation by rendering to images and reinserting; warn user about compatibility

**No Batch Operations Across Multiple Pages:**
- Problem: Cannot rotate, crop, or delete 5 pages at once—only works on one at a time
- Blocks: Editing large documents (reordering 50 pages of scans) is tedious
- Fix approach: Implement multi-page crop (same crop rect to all selected pages); multi-page rotation already works

**No Page Extraction/Export:**
- Problem: Cannot export selected pages as new PDF without using File > Save As and saving entire doc
- Blocks: Cannot extract specific chapters from books easily
- Fix approach: Add "Export Selected Pages" button that saves selection to new file

## Test Coverage Gaps

**No Unit Tests for Coordinate Conversion:**
- What's not tested: Crop drag coordinate → PDF coordinate conversion; canvas offset calculations
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1241-1247, 1274-1293)
- Risk: Zoom level changes or canvas resizing could silently break crop accuracy. Off-by-a-few-pixels errors go undetected until user reports.
- Priority: Medium—crops must be accurate to user expectations

**No Integration Tests for D&D:**
- What's not tested: Drag page 5 up 3 positions; drag page 1 to end; drag during scroll; rapid consecutive drags
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 1709-1806)
- Risk: Off-by-one errors in page index calculations will manifest only in specific drag scenarios. Complex state machine with no test safety net.
- Priority: High—D&D is primary UX feature

**No Plugin Event System Tests:**
- What's not tested: Plugin exception handling during event firing; plugin state isolation; callback ordering
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 592-600)
- Risk: Misbehaving plugin can crash entire app or break other plugins' state. No isolation.
- Priority: Medium-High—affects stability when plugins enabled

**No Undo/Redo State Consistency Tests:**
- What's not tested: Undo after file open; redo after new operation; stack overflow at MAX_UNDO=20
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 985-1033)
- Risk: State corruption if undo/redo order assumptions violated; memory leaks if old states not garbage collected
- Priority: High—data integrity critical

**No Settings Persistence Tests:**
- What's not tested: Settings save/load roundtrip; corrupted JSON recovery; settings migration between versions
- Files: `C:\Users\shdwf\work\project\PageFolio\.claude\worktrees\heuristic-proskuriakova\pagefolio.py` (lines 363-385)
- Risk: Silent settings loss if JSON corrupted; users lose preferences without warning
- Priority: Low—nice-to-have; current exception handling hides problems

---

*Concerns audit: 2026-03-17*
