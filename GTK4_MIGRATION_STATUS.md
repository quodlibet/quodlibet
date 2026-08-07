GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-08-07
**Test Results**: 4664 passed, 3 failed. Two are `tests/plugin/test_mediaserver.py`,
whose tearDown asserts the D-Bus name is released on `disabled()` — a D-Bus
lifecycle issue, not a GTK4 one. The third, `test_qltk_cover.test_big_window`,
is the long-standing order-dependent one and passes in isolation.

Run the suite with the app closed: a running Quod Libet owns
`org.mpris.MediaPlayer2.quodlibet` and `net.sacredchao.QuodLibet`, and
`test_mpris` / `test_mediaserver` then fail on the name being taken. That looks
like six new regressions and is nothing of the sort.


DRY: when to extract, and when to leave it
------------------------------------------

There is a lot of copy-and-paste in this codebase and so a lot of room for
extraction — but that pulls against keeping the diff against `main` small, and
against not disturbing rarely trodden UI paths. The working rule:

**Extract when the repetition is new.** If a migration introduces a pattern that
now has to be written out in three places, and a simple helper removes it, do it
then — the diff is already being touched, and a single copy is one place to get
it right rather than three to get it wrong. `qltk.popup_menu_at()` came from
exactly this: three near-identical popover setups, one of which had silently
missed the idle deferral and mis-sized itself.

**Leave pre-existing duplication alone** unless a bug forces you into it.
De-duplicating code that `main` also has buys nothing for the migration and
costs review surface.

Candidates noted for *after* the migration lands, when the diff no longer
matters:

- The `init_*` methods in `songsmenu.py` are near-identical section builders.
- Every browser repeats the same key-handler / context-menu / filter plumbing
  (`browsers/albums`, `collection`, `covergrid`, `paned`, `playlists` all have
  matching `__key_pressed` and popup code).
- The `WaitLoadWindow` / `WritingWindow` create-step-destroy dance is written out
  at each call site (`tracknumbers`, `tagsfrompath`, `renamefiles`, `edittags`,
  `embedded`, `ifp`) and wants a context manager.
- `qltk/x.py` has several near-duplicate small-button classes differing only in
  padding and size.


Keep the diff against `main` small
----------------------------------

An explicit goal of this migration: **minimise the diff against `main`**. Quod
Libet has a lot of rarely trodden UI paths, and bugs in them are hard to find,
so gratuitous rewrites cost more than they look. Before changing something,
check what `main` does (`git show main:<file>`) and prefer restoring its
behaviour over inventing new behaviour. Less is more.

This is not just style: the two worst regressions found in manual testing —
dialogs that never close, and menu items with no labels — were both introduced
by rewriting working code rather than porting it.


Resize warning storm: fixed, 2026-08-07
---------------------------------------

The top bar's cover is a constant 80px (`TopBar.COVER_SIZE`) instead of
resizing. A resizing cover measures width-for-height and the song info label
next to it wraps, so measures height-for-width; a box cannot reconcile the two,
which is what the hundreds of warnings on every resize were. With the cover
fixed, the box is uniformly height-for-width and reports min == natural at every
width. Needs confirming in the real app — the offscreen harness emits no
warnings either way.

**Ellipsizing the label was the tempting fix and it does not work.** It would
have restored `main`'s constant-size label exactly, and `ELLIPSIZE_END` looks
clean where `ELLIPSIZE_MIDDLE` visibly mangles the markup. But in the running
app END mangles it too: the title went xx-large for eleven characters and then
dropped to normal mid-word, and the album line lost its italics. None of this
reproduces standalone — the same pattern, rendered through a real `Gtk.Label`
and the GSK renderer at widths from 120px to 1350px, comes out correct every
time. So the label keeps wrapping, and **no ellipsize fix should be believed
until someone reproduces the corruption outside the app.**

Also removed: the `Gtk.IconTheme.get_default` shim. Its last caller was
`get_no_cover_pixbuf`, which raised inside `do_measure` when the shim was not
loaded — leaving the cover measuring 0×0 and warning about a horizontal
baseline.


Manual-test round, 2026-08-02
-----------------------------

Fixed: song and queue context menus (missing `popup-menu` signal, GTK3 handler
signatures, menus positioned at the view's centre, right-click hitting the row
below), the column header menu doing nothing, prefs keypresses, missing
repeat/shuffle icons, and every `Gtk-CRITICAL` allocation warning at startup.
`is_accel` and the three fake key-event objects that kept it alive are gone.

Still open, in rough priority order:

- **Context menus scroll and clip** — root cause found (`Gio.Menu` sections),
  see `GTK4_POST_MIGRATION_CLEANUP.md`.
- Scrobbler prefs are too wide; its own widget measures only ~312px, so the
  problem is likely how plugin prefs are embedded.
- Plugin list checkboxes all dim together on row selection.
- `Align needs at least 498` for a 285px allocation, in the `PlaylistsBrowser`
  with a real user config; not reproducible on a fresh one.
- `gtk_css_node_insert_after` critical whenever a popover is parented to a
  `Gtk.TreeView`. Reproduces with stock widgets, so likely a GTK complaint
  rather than ours.
- `tests/test_qltk_views.py` and `test_qltk_queue.py` hang when run standalone
  (pre-existing); they only pass as part of the full suite.


Gotchas found while fixing manual-test regressions (2026-08-02)
--------------------------------------------------------------

- **Don't call `set_widget()` on a `qltk.views.TreeViewColumn`.** It already
  installs its own label and hangs the `_button` lookup (and therefore the
  `tree-view-changed` signal and tooltips) off that label's `realize`. Replacing
  the label silently kills all of it: `TextColumn`'s deferred width checks simply
  stop running. Configure `_TreeViewColumnLabel` instead.
- **A GType has one parent.** Signals declared on a class that a widget inherits
  from *via a sibling branch* (e.g. `RCMTreeView` under `AllTreeView`) are not
  visible. Declare them on the shared GType root. GTK3 hid several of these
  because the signal was a built-in `Gtk.Widget` one.
- **Dots in Gio action names** are valid for the action, but a menu item's
  detailed action name won't resolve them, so the item silently does nothing.
- **Pop context menus on `released`, not `pressed`**: a popover that grabs during
  the press treats the release as a click-outside and hides itself.
- **Surviving GTK3 vfuncs are dead code**: `do_draw`, `do_get_preferred_width`,
  `do_get_preferred_height` are never called under GTK4. Grep for them; each one
  is a workaround that is no longer running and may be masking the real fix.
- Widget size requests below the theme's minimum (the old 26x26 button idiom) are
  refused by GTK4 with `Gtk-CRITICAL` allocation warnings, and the child can be
  clipped to nothing. Let the theme size buttons.


Tray icon: no GTK4 backend (2026-08-02)
---------------------------------------

`Gtk.StatusIcon` is gone in GTK4 and AppIndicator3 / AyatanaAppIndicator3 are
GTK3-only, so both backends are unusable. `systemtray.py` and the `Gtk.StatusIcon`
stub in `_init.py` are deleted and the plugin raises `PluginNotSupportedError` at
import. `IndicatorMenu` is ported and kept. Restoring the feature means
implementing `org.kde.StatusNotifierItem` over D-Bus directly — see
`GTK4_POST_MIGRATION_CLEANUP.md`.


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
- Oversized-queue-at-startup bug fixed (two causes):
  - `SongListPaned` was missing `vexpand`, so the paned stayed at its natural
    height inside the browser's box and the slack below it looked like a huge
    queue. Root cause: `pack_start(songpane, True, …)` → bare `append(songpane)`
    dropped `expand`, silently swallowed by the old `Gtk.Box` shim. Now sets
    `vexpand=True`. Other `pack_start(w, True, …)` sites likely lost `expand`
    the same way — see the packing sweep in the cleanup doc.
  - The collapsed-queue minimize is driven by `notify::max-position` (and the
    expander toggling), snapping the handle to `max-position` on an idle so it
    reads settled geometry. Keeps a collapsed queue at its minimum height at
    startup and on resize, without fighting the paned mid-allocation. Replaces
    the removed GTK3 per-`draw` enforcement.
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
