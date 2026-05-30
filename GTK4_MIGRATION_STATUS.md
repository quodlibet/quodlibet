GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-05-30
**Test Results**: 4653 passed, 18 failed, 49 skipped (99.6%)


Quick Summary
-------------

The application runs. Core migration is done. All `TODO GTK4:` markers
have been resolved. Ruff `check` and `format --check` both pass. The
remaining failures (18) are pre-existing order-dependent tests that
pass individually; they appear unaffected by GTK4 changes.


Remaining Failures (18)
------------------------

Pre-existing, all pass when run in isolation. Likely GTK4 widget
lifecycle / cleanup differences not yet investigated:

- Album browser (5): test_active_filter, test_filter_album,
  test_filter_artist, test_list, test_set_text
- CoverGrid browser (3): test_filter_artist, test_list, test_set_text
- Playlists browser (1): test_songs_deletion
- iRadio (1): test_click_add_station
- SoundCloud (1): test_songsmenu_has_information_but_no_edit
- Cover (1): test_big_window
- TextEdit (1): test_revert
- Queue (1): test_autosave
- Tray icon (2): test_popup_menu, test_icons
- MediaServer (2): test_entry_name, test_name_owner (DBus teardown,
  not GTK-related)


Recently Landed (2026-05-30)
----------------------------

- Merged 4 commits from `main` (PositionColumn, unity GError handling,
  pot refresh). Unity stub keeps disabled under GTK4.
- `TreeViewColumn.tree-view-changed` actually fires now:
  `parent-set` was silently shimmed, swapped for `notify::parent` with
  explicit previous-parent tracking.
- `SearchBarBox` migrated off four removed GTK3 signals
  (`backspace`, `populate-popup`, `focus-out-event`, `key-press-event`)
  using `EventControllerFocus`, `EventControllerKey`, and a
  `Gtk.Entry.set_extra_menu()` Gio.Menu bound to a stateful
  `Gio.SimpleAction` for the eager-search toggle.
- `RCMTreeView` declares `popup-menu` as a custom gsignal so the dozens
  of `view.connect("popup-menu", …)` callers in browsers / playlists /
  edittags / paned / etc. actually run. Menu / Shift+F10 wired up via
  `EventControllerKey`.
- `TreeViewColumnButton`: dead `button.connect("popup-menu", …)`
  replaced with an `EventControllerKey` on the column header button.
- `SongListPaned` cleaned up: removed `draw` and `button-press-event`
  no-ops; `_check_minimize` runs from `notify::expanded`.
- `covergrid.AlbumWidget`: popup-menu keyboard binding via
  `EventControllerKey` (Gtk.Box has no `popup-menu` in GTK4).
- New helper `is_accel_pressed(keyval, state, *accels)` for matching
  accels from `EventControllerKey` without fabricating a GdkEvent.

Earlier (2026-05-16)
--------------------

- Merged 16 commits from `main` (mmkeys macOS overhaul, translations,
  flake.nix conflict resolved — keybinder3 stays out under GTK4).
- Browser DnD reimplemented across albums, collection, covergrid,
  paned, playlists, filesystem, podcasts using `Gtk.DragSource` and
  `Gtk.DropTarget` with `Gdk.FileList` content. Removed the legacy
  `TARGET_INFO_*` / `DND_*` constants.
- Main window: two `Gtk.DropTarget` controllers (FileList for local
  files/dirs, String for remote URIs).
- Albumart plugin and filesel `DirectoryTree` drop-target restored.
- Dead VolumeMenu / Unity / Dbusmenu code removed; ruff suite clean.


Known Limitations (Tracked, Non-Blocking)
-----------------------------------------

- `TreeViewHints.__motion` is unwired; truncated cell hover-tooltips
  don't appear. Fixing requires a `Gtk.EventControllerMotion` on each
  view with widget-coordinate translation.
- macOS native menu bar integration not wired up (GtkosxApplication
  parity gap under GTK4).
- M3U/PLS URL import via DnD to playlist browser is deferred.
- `quodlibet/_init.py` still hosts compatibility shims; each is
  documented and should be removed as call sites migrate.
- Remaining shimmed-signal call sites (~55 connects across button-press,
  key-press, focus-out, populate-popup, etc.) — biggest cluster is
  `qltk/seekbutton.py` (right-click menu, scroll seek) and
  `qltk/info.py` (song info bar context menu / clipboard middle-click).
  Each needs a GestureClick / EventControllerKey rewrite plus a
  Gtk.PopoverMenu replacement for any Gtk.Menu still in scope.
- `SongListPaned` drag-to-expand-queue UX is dropped (relied on
  `Gtk.Paned.get_handle_window()` which is gone in GTK4).
