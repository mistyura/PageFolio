---
status: issues_found
files_reviewed: 12
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
---

# Code Review: Phase 04 (ui-ux)

## Summary

Reviewed the 04-01〜04-04 diff (`app.py` shortcut pure-functions, new `dialogs/shortcuts.py`
`ShortcutsDialog`, `SettingsDialog`/`LLMConfigDialog` reorganization, `viewer.py`/`page_ops.py`
i18n/messagebox fixes, and `lang.py` key cleanup) against `git diff af0968f~1 dc20c80`. No
security issues were introduced — the diff does not touch API-key handling, credential storage,
or any cloud-request construction logic in `llm_config.py`/`ocr_providers.py`; those paths are
unchanged. CLAUDE.md conventions (C[] theme dict, `self._font()`, no bare `except:`, LANG ja/en
parity) are followed correctly in all new code, and all 193 relevant tests pass. Two real
(non-critical) bugs were found in the new `ShortcutsDialog` key-capture flow, plus two minor
code-quality notes.

## Findings

### WR-01: ShortcutsDialog leaves stale "press a key" label when switching capture target

**File:** `pagefolio/dialogs/shortcuts.py`, `_start_capture` (lines 189–197)

```python
def _start_capture(self, cmd_name):
    if self._capturing_cmd is not None:
        self._end_capture()
    self._capturing_cmd = cmd_name
    label = self._key_labels.get(cmd_name)
    if label is not None:
        label.configure(text=self._L["shortcuts_capture_waiting"])
    self.bind("<KeyPress>", self._on_capture_keypress)
    self.focus_set()
```

If the user clicks "変更" (Change) on row A (label now shows `shortcuts_capture_waiting`,
e.g. "キーを押してください…"), then clicks "変更" on row B *before* pressing a key or Escape
for A, `_end_capture()` clears `_capturing_cmd` and unbinds `<KeyPress>` but never calls
`self._refresh_row(<old cmd_name>)`. Row A's label is left permanently stuck on the
"waiting for key" placeholder text instead of reverting to its actual assigned keysym, until
the user hits Save, Reset-to-defaults, or otherwise triggers a full-row refresh.

Every other exit path from capture mode (`Escape`, successful capture, duplicate-key
rejection, `_clear_cmd`, `_on_reset_all`, `_on_save`) correctly calls `_refresh_row`/
`_refresh_all_rows` after `_end_capture()`. Only this one call site is missing it. The
underlying `self._shortcuts[A]` data is untouched (no data loss), but the on-screen state is
misleading during the session.

**Suggested fix:** capture the previous cmd name before ending capture and refresh it:
```python
def _start_capture(self, cmd_name):
    if self._capturing_cmd is not None:
        prev_cmd = self._capturing_cmd
        self._end_capture()
        self._refresh_row(prev_cmd)
    ...
```

### WR-02: Key capture accepts unmodified keys, which can collide with normal typing elsewhere in the app

**File:** `pagefolio/dialogs/shortcuts.py`, `_on_capture_keypress` (lines 206–235); also
`pagefolio/app.py` `_bind_shortcuts` (binds to `self.root`, i.e. globally within the main window)

`_on_capture_keypress` only rejects `Escape` and the modifier keysyms in `_MODIFIER_KEYSYMS`
(`Control_L/R`, `Alt_L/R`, `Shift_L/R`, `Caps_Lock`, `Num_Lock`). Any other single keypress —
including a bare printable key with **no** Control/Alt/Shift held — is accepted and saved as a
valid shortcut (e.g. a user could bind the `toggle_mode` command to plain `5`).

Because `_bind_shortcuts()` binds shortcuts on `self.root` (the main window itself, not a
modal `Toplevel`), and Tk's default bindtags propagate an event from a focused child widget up
to its containing toplevel unless something calls `break`, a bare-key shortcut will also fire
while the user is typing in any in-window widget that lives directly under `root` — for
example the page-size `ttk.Spinbox` built in `ui_builder.py` (line 265). Typing a digit that
happens to match a user-assigned bare-key shortcut would both insert the digit **and** run the
bound command, which is confusing and hard to diagnose. This risk was previously only
theoretical (shortcuts could only be hand-edited in `pagefolio_settings.json`); the new GUI
capture flow makes it trivially easy to create such a binding by accident (a user might simply
press a letter, not realizing a modifier was expected).

This isn't a data-loss bug, but it's a real, newly-exposed usability/robustness gap with no
warning or restriction. Consider requiring at least one modifier (Control/Alt) for GUI-captured
bindings, or warning the user when a modifier-less key is about to be assigned.

### IN-01: Dead constant `_SHORTCUT_MOD_ORDER` in app.py

**File:** `pagefolio/app.py`, line 53

```python
_SHORTCUT_MOD_ORDER = ("Control", "Alt", "Shift")
```

Defined immediately above `build_keysym_from_event`, whose docstring says "修飾は Control,
Alt, Shift の順で連結し" — but the function hardcodes the same three `if` checks in that
order rather than iterating `_SHORTCUT_MOD_ORDER`. The constant is never read anywhere in the
codebase (confirmed via repo-wide grep). It's effectively dead code and a latent source of
drift: if the modifier order in `build_keysym_from_event` is ever changed, this constant
wouldn't be updated in tandem since nothing depends on it. Either wire it into
`build_keysym_from_event` (`for mod_name, mask in zip(_SHORTCUT_MOD_ORDER, (control_mask,
alt_mask, shift_mask)): ...`) or remove it.

### IN-02: page_ops.py has pre-existing hardcoded ja-only strings not covered by this phase's i18n sweep

**File:** `pagefolio/page_ops.py` — `_add_watermark_text` (line ~227), `_add_watermark_text`
status (line 255), `_add_watermark_image` status (line 297), `_add_page_numbers` status
(line 334), and the hacky `_insert_blank_page` status built via `.replace(...)` on
`status_duplicated` (lines 212–216)

04-04 explicitly moved `viewer.py` popup text to LANG keys and removed 11 confirmed-unused
LANG keys, but a handful of pre-existing hardcoded Japanese strings in `page_ops.py` (not part
of this phase's diff) remain outside the LANG dict, e.g.:
```python
self._set_status(f"透かしを追加しました ({len(targets)} ページ)")
```
These predate Phase 04 (added in earlier watermark/page-number work) and are out of scope for
this diff, but they're the same class of issue this phase was actively cleaning up elsewhere,
so flagging for awareness/follow-up rather than as a phase-04 regression.
