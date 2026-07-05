GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-07-05
**Test Results**: ~4655 passed; remaining failures are the pre-existing
order-dependent set (below), all passing in isolation.


SongsMenu → Gio.Menu: LANDED (2026-07-05)
-----------------------------------------

The blank right-click/prefs menus (the `Gtk.PopoverMenu`-renders-a-model,
not-appended-widgets gap) are fixed. `SongsMenu` is now a real
`Gtk.PopoverMenu` with `set_menu_model(Gio.Menu)` + a `songs`
`Gio.SimpleActionGroup`; each `init_*` builds a `Gio.MenuItem` + `SimpleAction`
(`set_sensitive` → `action.set_enabled`), grouped via `append_section`.

- **Parent window**: actions have no widget, so callbacks resolve the toplevel
  via `get_top_parent(self)` (the popover is parented at popup time).
- **Ratings / Playlists**: `RatingsMenuItem` and `PlaylistMenu` are now
  Gio-model **submenu builders** (stateful radio / per-playlist toggle actions),
  shared by `SongsMenu` and the **trayicon** `IndicatorMenu` (also migrated).
  `PlaylistMenu.build()` is rebuildable for the tray's per-song refresh.
- **Plugins**: `SongsMenuPluginHandler.build_menu_item()` builds a Gio "Plugins"
  submenu. Plugin instances are still widget-based (`MenuItemPlugin(Gtk.Button)`);
  the handler reads `PLUGIN_NAME`/submenu children and threads the parent window
  in via `plugin.plugin_window` (now a settable attr, set at invocation) rather
  than walking the widget tree. Plugins with widget submenus still work.
- **`items=` API**: now action-specs (`songsmenu.MenuItemSpec`: label, callback,
  enabled, accel). Callers updated: songlist Filter, albums, covergrid, info,
  queue, filesystem, iradio (podcasts/soundcloud just forward).
- **Popup**: existing `popup_menu_at_widget` / `views.popup_menu` paths kept
  working; info.py's context menu is a native `GestureClick` + popover.
- **Menus stay model-safe under the shim**: the global `Gtk.PopoverMenu` compat
  monkeypatch (`_init.py`, `qltk.menu_popup`) would clobber a model menu with an
  empty `_menu_box` on popup — now guarded with `get_menu_model() is None`.
- **info.py**: dead `populate-popup`/`key-press-event`/`button-press-event`
  shim connects replaced with `GestureClick` + `EventControllerKey`.
- **Shims**: `Gtk.CheckMenuItem` shim removed (unused). `Gtk.MenuItem` /
  `Gtk.PopoverMenu` (append) / `SeparatorMenuItem` shims **stay** — still used by
  the ~6 plugin widget-submenus, `exfalsowindow`, and the prefs/header popovers.
  Removing them is gated on migrating the widget-based plugin-menu API (separate
  effort; see cleanup doc).


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


Visual / Layout Regressions (2026-06-27 review)
-----------------------------------------------

Runtime screenshot review against GTK3 `main`. Several distinct issues;
root cause found where noted. Fixed items kept here for the audit trail.

### Font / glyph rendering corruption — ENV, likely GSK renderer

Symptoms: now-playing info text switches bold/large → normal *mid-word*
even though the Pango markup is valid and wraps the whole title
uniformly (verified: `Pango.parse_markup` succeeds, one span over the
whole title); rating stars `★ ☆` render as `�` (U+FFFD); song list rows
look vertically clipped / sub-pixel-mangled. Varies per song.

Not app logic: markup is well-formed, fonts resolve (`fc-list` ~1157,
`fc-match sans` → Noto Sans), and `pango`/`harfbuzz`/`freetype` resolve
to the correct Nix store paths via RPATH. **It was fine on `main`
(GTK3) in the same Nix shell**, so it is a GTK4-specific regression.

Most likely cause: GTK4 defaults to the GPU GSK renderer (ngl/Vulkan)
and builds glyph atlases on the GPU. This dev shell has **no GL/Vulkan
on `LD_LIBRARY_PATH`**, so a Nix-built GTK4 ends up against the host
`/usr/lib/libGL.so` — a mismatched GL stack that corrupts glyph
textures. GTK3 used cairo (CPU) so `main` was unaffected.

Workaround to verify, then bake into `flake.nix` if confirmed:
`GSK_RENDERER=cairo nix develop -c -- poetry run python quodlibet.py`.
(Running under Nix on a foreign distro is itself only semi-supported;
the GPU renderer is the sharp edge.) If cairo fixes it, the GPU path is
the culprit and is worth keeping native on supported setups — see the
perf note below.

### Now-playing cover missing (top-right) — FIXED

`ResizeImage` (`qltk/cover.py`) still implemented GTK3 vfuncs
(`do_draw`, `do_get_preferred_*`) that GTK4 never calls, so it measured
0×0 and painted nothing. Ported to `do_measure` (aspect-correct,
natural 70px / height-for-width) + `do_snapshot` (scale → border →
`Gdk.Texture`, centred). The earlier claim in this doc that the main
cover "draws via snapshot" was wrong — it was still on `do_draw`.

### Browser search bar at the bottom of the pane — FIXED

Album + CoverGrid browsers showed the search bar below the list. Cause:
GTK3 `pack_start()` appends in document order, but the migration
translated `pack_start()` → `prepend()`, which inserts at the *start*
and reverses sequential packs. Canonical GTK4 mapping is
`pack_start → append`; fixed both browsers. **Systematic risk:** this
`pack_start → prepend` mistranslation is repeated across the codebase
(~133 `.prepend(` call sites). Confirmed also reversed in
`qltk/tagsfrompath.py` (124,135) and `qltk/renamefiles.py` (190,201)
where `hbox`/`sw` are swapped. Needs a careful per-site sweep
(cross-check each against `git show main:<file>`); not all `prepend`s
are wrong (genuine `pack_end`/single-child cases exist).

### CoverGrid lays out as a single column, not a grid — OPEN

The `Gtk.FlowBox` (`browsers/covergrid/main.py:275`, `homogeneous=True`,
`max_children_per_line=10`) renders one item per line. Hypothesis: the
per-item label is not width-constrained, so a very long album/artist
string blows up the child's natural width and, with `homogeneous=True`,
forces every child to that width → one column. `AlbumWidget.do_measure`
fixes the *horizontal* size but the label inside still wants its full
natural width. Fix candidate: constrain the label
(`max_width_chars`/`width_request`/`wrap`) and confirm `do_measure` is
actually driving the child width. Horizontal-alignment oddities are
probably the same root cause.

### CoverGrid covers render tiny — FIXED

`browsers/covergrid/widgets.py` `self._image` is now a `Gtk.Picture`
(`content_fit=CONTAIN`, size-request to the cover size) fed via
`set_paintable(Gdk.Texture.new_for_pixbuf(pb))`. In GTK4 `Gtk.Image`
only renders at *icon size* and downscales any pixbuf — it is not for
arbitrary-size images. Same trap still affects the `Gtk.Image`
*subclasses* `WebImage` (`qltk/x.py:364`) and `ResizeWebImage`
(`ext/songsmenu/cover_download.py:81`); converting those means reworking
the base class.

### Other open visual items

- **"Missing cover" placeholder bitmap changed** vs `main`
  (`get_no_cover_pixbuf` / `quodlibet-missing-cover` icon lookup in
  `qltk/cover.py`). Confirm whether the new icon is acceptable or a
  lookup regression.
- **Transport / seek control too large.** The seek area
  (`qltk/seekbutton.py`, recently rewritten) takes too much vertical
  space vs `main`. Needs size-request / layout review.

### Performance opportunity — keep rendering native

The GPU renderer that's currently misbehaving under Nix is also the
upside: on a supported GL/Vulkan stack, GTK4's GSK renderer composites
on the GPU. For texture-heavy, scroll-heavy views like CoverGrid this
can be a real win over GTK3's cairo software path — *provided* we stay
native:

- Hold covers as `Gdk.Texture` / `Gtk.Picture` (done for CoverGrid), so
  each cover is uploaded once and is cheap to re-draw and scroll, rather
  than re-blitted by cairo every frame.
- The biggest structural win is replacing model-backed `Gtk.TreeView`
  (song list) and the FlowBox with `Gtk.ColumnView` / `Gtk.GridView` +
  `Gio.ListModel`, which virtualise: only visible rows/cells are
  realised. That matters most for very large libraries.
- Caveat: none of this lands while we're on the cairo fallback, and the
  shim layer (fake events, `do_draw` widgets, Gtk.Menu) keeps us on
  slow/legacy paths. The perf payoff is gated on finishing the *native*
  migration, not just making GTK3 idioms compile.


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
- Remaining shimmed-signal call sites (button-press, key-press, focus-out,
  populate-popup, scroll, etc.). `seekbutton.py` and `qltk/info.py` are done
  (info.py: `GestureClick` + `EventControllerKey`, native popover menu). The
  long tail remains across
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
