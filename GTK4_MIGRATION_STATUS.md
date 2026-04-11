GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-04-11
**Test Results**: 4606 passed, 62 failed, 48 skipped (98.7%)


Quick Summary
-------------

The application runs. Core migration is done. Remaining failures fall into a few categories that need focused work.


Remaining Failures by Category
------------------------------

### GTK4 API updates (easiest — just fix the call sites)
- `Overlay.add()` → `set_child()` / `add_overlay()` — cover.py, image tests, viewlyrics plugin
- `Dialog.vbox` → `get_content_area()` — edittags, replaygain dialog
- `ScrolledWindow.size_request` → `get_size_request()` — data_editors
- `IconTheme.append_search_path()` → `add_search_path()` — test_icons
- `StyleContext.get_color()` signature changed (1 arg, not 2) — image tests
- `border_width` property removed — update dialog (GtkStack)
- `flags` property removed — msg.py (CancelRevertSave)
- `remove_accel_group()` removed — commands test / quodlibetwindow

### Signal / event model changes
- `button-press-event` signal removed — cover.py (use GestureClick)
- `connect_destroy` count mismatch — test_util.py (destroy signal semantics changed)

### Menu system (needs Gio.Menu migration)
- `PlaylistMenu.close()` missing — playlist browser tests (5 failures)
- `Viewport.get_submenu()` missing — ratingsmenu test
- Menu item children / sensible menu checks — songlist, songsmenu tests

### DnD (disabled, needs full rewrite)
- 37 `# TODO GTK4` markers across 15 files
- Playlist drag_data_get test fails
- Queue save/restore affected

### Cursor / display API
- `Gdk.Cursor` constructor changed — image_support test
- Display type mismatch (X11Display vs string) — image_support test

### Ruff lint/format
- 2 quality test failures — likely from recent edits, fix with `ruff format && ruff check --fix`

### Misc
- `test_producer` — KeyError `~mountpoint` (format metadata, not GTK-related)
- `test_mediaserver` — DBus teardown (not GTK-related)
- `test_stock_icons` — references to icons in `_init.py` shim layer
- `test_util_thread::Tcall_async` — async callback count off
- `QuestionBar` visibility — iradio browser


TODO Markers
------------

37 `# TODO GTK4` across 15 files, nearly all DnD-related:

| File | Count | Area |
|------|-------|------|
| `qltk/views.py` | 5 | TreeView DnD |
| `browsers/podcasts.py` | 4 | DnD |
| `browsers/collection/main.py` | 3 | DnD |
| `browsers/covergrid/main.py` | 3 | DnD |
| `browsers/albums/main.py` | 3 | DnD |
| `browsers/filesystem.py` | 3 | DnD |
| `browsers/paned/pane.py` | 3 | DnD |
| `browsers/playlists/main.py` | 3 | DnD |
| `ext/songsmenu/albumart.py` | 3 | DnD |
| `qltk/quodlibetwindow.py` | 2 | DnD + accel |
| `qltk/filesel.py` | 1 | DnD |
| `qltk/controls.py` | 1 | DnD |
| `qltk/queue.py` | 1 | DnD |
| `qltk/exfalsowindow.py` | 1 | accel |
| `qltk/window.py` | 1 | destroy tracking |


Priority Order
--------------

1. **Quick wins**: Fix the simple API call sites (Overlay.add, Dialog.vbox, etc.) — ~15 failures, mechanical changes
2. **Ruff**: Run formatter/linter to clear 2 quality failures
3. **Menu system**: Migrate remaining widget menus to Gio.Menu — ~8 failures
4. **Signal/event migration**: Replace remaining GTK3 signal connections — ~3 failures
5. **DnD rewrite**: Biggest remaining chunk — 37 TODOs, needs DragSource/DropTarget controllers
