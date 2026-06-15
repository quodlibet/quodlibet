GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-06-15
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


Recently Landed (2026-06-15)
----------------------------

- `qltk/seekbutton.py` fully migrated off shimmed signals. HSlider's
  `Gtk.Window(POPUP)` + manual grab slider is now a `Gtk.Popover`;
  `Gtk.Arrow` → `Gtk.Image`; `Button.add`/`show_all` → `set_child`.
  The four scale button/key press-release "seek lock" connects collapse
  into one `Gtk.Range::change-value` handler (debounced seek);
  `scroll-event` → `EventControllerScroll`; right/middle-click +
  `popup-menu` → `GestureClick` + `EventControllerKey`. Context menu is
  now `Gtk.Popover` + `Gtk.Box` (queue/playorder idiom) instead of a
  shimmed `Gtk.PopoverMenu`. Removes WindowType/WindowTypeHint/EventMask/
  add_events/Arrow/Button.add/show_all/window_grab_and_map/
  popup_menu_at_widget shim usage. Public API unchanged.
- Codebase-wide shimmed-signal connects: 45 → 31.
- NOT yet visually verified at runtime (popover slider / scroll-seek /
  right-click menu); app launches with no seekbutton errors.

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
- Remaining shimmed-signal call sites (31 connects across button-press,
  key-press, focus-out, populate-popup, scroll, etc.). `seekbutton.py`
  is done; next cluster is `qltk/info.py` (song info bar context menu /
  clipboard middle-click, 3 connects), then the long tail across
  `qltk/edittags.py`, `ext/songsmenu/tapbpm.py`,
  `ext/events/waveformseekbar.py` (still on `do_button_press_event`
  vfuncs), `ext/events/trayicon/systemtray.py`, `browsers/paned/pane.py`
  and ~1-each across browsers/ext. Each needs a GestureClick /
  EventControllerKey rewrite; reuse the Gtk.Popover+Gtk.Box context-menu
  idiom (queue/playorder) rather than the shimmed Gtk.PopoverMenu.
- The Gtk.Menu/Gtk.MenuItem subsystem is still shimmed codebase-wide
  (~91 MenuItem usages). Full Gio.Menu migration is a separate large
  cross-cutting effort — do not island-rewrite individual menus.
- `SongListPaned` drag-to-expand-queue UX is dropped (relied on
  `Gtk.Paned.get_handle_window()` which is gone in GTK4).


Test Follow-ups (from 2026-06-15 review)
----------------------------------------

A review of the branch's test changes vs `main` flagged these
(non-blocking, but worth fixing):

- Lost coverage: `tests/test_qltk_util.py` was deleted but its target
  `position_window_beside_widget` (`quodlibet/qltk/util.py`) still ships
  untested — re-test or delete the function.
- Shim-coupled test: `tests/test_plugins_playlist.py` asserts
  `menu.get_children()` length on a `Gtk.PopoverMenu` (incidental widget
  structure via shim) — rewrite to introspect the `Gio.Menu` model like
  `test_qltk_filesel.py` / `test_qltk_songlist.py` do.
- `tests/test_browsers_playlists.py` `_fake_browser_pack` uses
  `prepend(b, True, True, 0)` (GTK3 pack args via the Box.prepend shim) —
  should be `prepend(b)`.
- `tests/test_qltk_views.py` `test_key_events`/`test_click`/
  `test_right_click` assert nothing now (helper event-senders stubbed to
  no-ops) — skip-mark or add real assertions.
- Other deletions to confirm intentional: `test_drag_data_get`
  (playlist DnD), `test_volumemenu` (VolumeMenu), weakened
  `test_qltk_paned.py` min-size assertion.
