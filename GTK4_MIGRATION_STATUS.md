GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-05-03
**Test Results**: 4641 passed, 27 failed, 48 skipped (99.4%)


Quick Summary
-------------

The application runs. Core migration is done. Most remaining failures are order-dependent (pass individually, fail in full suite) or ruff lint issues from commented-out DnD code.


Remaining Failures (27)
------------------------

### Ruff lint (1 failure, ~152 violations)
- Mostly commented-out DnD code across browsers/*.py, qltk/views.py, qltk/window.py
- Unused `targets` variables in DnD stubs
- A few line-too-long and undefined names (Unity/Dbusmenu in qltk/unity.py)
- Fix: clean up commented-out code blocks, run `ruff check --fix`

### Order-dependent failures (~18 failures)
These tests pass individually but fail in the full suite. Likely GTK4 widget lifecycle / cleanup differences:
- Album browser (5): test_active_filter, test_filter_album, test_filter_artist, test_list, test_set_text
- CoverGrid browser (3): test_filter_artist, test_list, test_set_text
- Playlists browser (1): test_songs_deletion
- iRadio (1): test_click_add_station
- SoundCloud (1): test_songsmenu_has_information_but_no_edit
- Cover (1): test_big_window
- TextEdit (1): test_revert
- Commands (1): test_set_browser (remove_accel_group — shim added, may now pass)
- Data editors (2): test_defaulting, test_no_strings (size_request fixed, may now pass)
- Image (1): test_add_border_widget (border_radius fixed, may now pass)

### Tray icon plugin (5 failures)
- PlaylistMenu.close() → popdown() — FIXED, needs retest
- get_paused_pixbuf returns None — FIXED (snapshot fallback), needs retest
- test_icons: uses GTK3 `Gtk.ImageMenuItem` isinstance check — needs test update
- SystemTray class still uses many GTK3 APIs (StatusIcon etc.) — masked by shims

### Queue (2 failures)
- test_save_restore, test_autosave — FIXED (destroy() override), needs retest

### MediaServer (2 failures)
- DBus teardown issue (not GTK-related), test_entry_name, test_name_owner


Fixed This Session (2026-05-03)
-------------------------------
- QueueExpander DnD: `Gtk.DropTarget` accepting `Gdk.FileList`, auto-expand on
  motion, append dropped songs to queue model. Removed orphan GTK3 `__motion`
  and `__drag_data_received` callbacks.


Fixed Previously (2026-04-26)
-----------------------------
- Missing GLib imports in data_editors, bookmarks, exfalsowindow, pane, duplicates
- `remove_accel_group` shim added (matching existing `add_accel_group` shim)
- `size_request` → `get_size_request()` in data_editors
- `STYLE_PROPERTY_BORDER_RADIUS` replaced with default (removed in GTK4)
- `PlaylistMenu.close()` → `popdown()` in tray icon menu
- `get_paused_pixbuf` snapshot fallback for non-file-backed icons
- `PlayQueue.destroy()` override to flush queue (GTK4 removed destroy signal)
- Dead `drag_data_received` code cleaned up in podcasts browser


TODO Markers
------------

31 `# TODO GTK4` across 14 files, nearly all DnD-related. Hotspots:
- 8 browsers × 3 each (albums, collection, covergrid, filesystem, paned,
  playlists, podcasts, plus albumart in songsmenu)
- `qltk/quodlibetwindow.py` (2), various single-TODO qltk files


Priority Order (Next Steps)
----------------------------

1. **Retest** the fixes above in full suite to confirm improvement
2. **Ruff cleanup**: Remove commented-out DnD code blocks, fix line lengths — should clear lint failure and reduce noise
3. **Order-dependent failures**: Investigate widget lifecycle / cleanup in test tearDown — likely need explicit destroy() or idle iteration
4. **Tray icon test_icons**: Update test to match GTK4 menu item widget types
5. **DnD rewrite**: 31 TODOs remaining (queue done). Browsers next — each needs DragSource/DropTarget controllers
