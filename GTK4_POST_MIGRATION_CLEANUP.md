GTK4 Post-Migration Cleanup Backlog
===================================

Things to improve / normalise / declutter **once the GTK4 migration has landed**.
Append to this as we go; don't act on these mid-migration unless they're blocking.
Companion to `GTK4_MIGRATION_STATUS.md` (current state) — this file is the "later" list.


Shims to remove (`quodlibet/_init.py`)
--------------------------------------

Each shim is technical debt; remove it once **all** call sites use the native API,
so the tree stays runnable throughout.

- `Gtk.PopoverMenu` `append`/`__init__`/`popup` shims — `SongsMenu` + trayicon
  are off them (model-based), but they **stay** until the widget-based
  plugin-menu API is migrated (see below); ~6 plugins + `exfalsowindow` + prefs
  popovers still `Gtk.PopoverMenu().append(widget)`. The shims are now guarded to
  not clobber model menus (`get_menu_model() is None`).
- `Gtk.MenuItem = Button`, `Gtk.ImageMenuItem` dummy — same plugin-API blocker.
  `Gtk.CheckMenuItem = CheckButton` shim is **removed** (was unused).
- `Gtk.Box.prepend`/`append` arg-swallowing compat — **removed**. No call site
  passed the old `expand/fill/padding` args (verified statically), so it was dead.
  The separate `pack_start` → `prepend` *ordering* sweep below is unaffected.
- `GObject.Object.connect`/`connect_after` compat that silently drops removed
  event signals (`button-press-event`, `key-press-event`, …) — remove once all
  call sites use `Gtk.EventController*`. This shim hides real breakage, so it's a
  priority to retire.
- `Gtk.Alignment`, `Gtk.Widget.show_all`/`set_no_show_all` no-ops, and the various
  `add()`→`set_child()`/`append()` container shims — remove as call sites migrate.


Systematic sweeps
-----------------

- **Dropped `expand` from `pack_start(w, True, …)`.** With the arg-swallowing
  `Gtk.Box` shim now gone, the real breakage is call sites that translated
  `pack_start(w, True, True, 0)` to a bare `append(w)` and never set
  `set_hexpand`/`set_vexpand(True)`. The child then sits at natural size and its
  container's slack looks like empty space. Confirmed + fixed: `SongListPaned`
  (queue looked oversized). Sweep every `git show main:<file>` `pack_start`/
  `pack_end` with `expand=True` and confirm the GTK4 side sets the matching
  expand.
- **`pack_start` → `prepend` mistranslation.** The canonical GTK4 mapping is
  `pack_start` → `append`; a lot of the migration used `prepend`, which reverses
  sequential packs. ~133 `.prepend(` sites to audit (cross-check each against
  `git show main:<file>`). Confirmed reversed and fixed: Album/CoverGrid browsers;
  still suspect: `qltk/tagsfrompath.py`, `qltk/renamefiles.py` (hbox/sw swap), and
  intra-hbox prepends elsewhere.
- **`do_draw` / GTK3 size vfuncs.** Audit for any remaining widgets implementing
  `do_draw` / `do_get_preferred_*` (GTK4 never calls them). Fixed: `ResizeImage`
  (`qltk/cover.py`). Check for others.


Idiomatic rewrites still pending
--------------------------------

- **`Gio.Menu` migration.** DONE for `SongsMenu`, `RatingsMenuItem`,
  `PlaylistMenu`, the trayicon `IndicatorMenu`, and `info.py`'s context menu
  (2026-07-05). **Remaining: the widget-based plugin-menu API** — `MenuItemPlugin`
  is a `Gtk.Button` and ~6 plugins build submenus via `Gtk.PopoverMenu().append(
  Gtk.MenuItem(...))`. The `SongsMenu` handler currently bridges these (reads
  `PLUGIN_NAME`/submenu-child labels, fires `child.emit("activate")`). Fully
  native would redesign the plugin menu as declarative data (label/icon/callback/
  submenu specs) and migrate the plugins; that's what still blocks removing the
  `MenuItem` / `PopoverMenu.append` / `SeparatorMenuItem` shims. Also still on the
  shim: `exfalsowindow` app menu and the covergrid/albums/queue prefs popovers.
  Inline star-rating row is still a deferred enhancement (below).
- **`Gtk.Image` subclasses that show arbitrary images** — `WebImage`
  (`qltk/x.py`) and `ResizeWebImage` (`ext/songsmenu/cover_download.py`) hit the
  same tiny-render trap as CoverGrid; port to `Gtk.Picture`/snapshot.
- **`TreeViewHints.__motion`** is unwired (truncated-cell hover tooltips gone) —
  needs a `Gtk.EventControllerMotion` with widget-coord translation.


UX enhancements (post-fidelity)
-------------------------------

- **Boolean settings: menu checks vs switches.** GTK4 `Gio.Menu` boolean items
  show a ✓ only when on (nothing when off) — idiomatic (Nautilus does this), but
  it reads oddly for settings because state is hidden at rest. Modern
  GNOME/libadwaita apps mostly move boolean options *out of menus* into a
  preferences surface with switches (`Adw.SwitchRow`, or a popover of
  `Gtk.Switch` rows) where on/off is always visible. Consider moving the search
  prefs (Limit Results / Allow multiple queries) and similar toggles to a switch
  popover, and use state-oriented labels ("Show …") where a menu check stays.
  The trayicon `IndicatorMenu` toggles (Shuffle / Repeat / Stop After This Song)
  are now Gio boolean menu items and hit exactly this "hidden state at rest"
  issue — candidates for the same switch treatment.
- **libadwaita for the "antiquated UI" problem.** The broader modern-feel /
  retention concern is really an Adwaita question (switch rows, preferences
  windows, view toggles, header bars). Big, strategic, post-migration — but it's
  the lever GNOME apps pull. Worth a deliberate decision rather than drifting.


- **Inline cumulative star rating in the context menu.** Once the menu is on
  `Gio.Menu`, an inline star row (hover-preview, click Nth star = rating N) as a
  `PopoverMenu` custom child removes a click vs the Rating submenu and feels
  modern. Deferred: the migration restores the original submenu first for
  fidelity; this is an enhancement on top. (Spike proved the custom-child slot
  and the cumulative interaction both work.) Low priority, too: the song list
  already has a **ratings column** for click-to-rate without any right-click.


Performance / UX (high priority)
--------------------------------

- **CoverGrid cover caching.** A long-standing user pain point — CoverGrid
  performance (and the dated UI) is a frequent reason people leave QL. Cover
  loading still hits the filesystem on every load ("Searching for local cover"
  spam in the logs); the per-item in-memory `_cover` only helps within a single
  session and only once an item has been bound. Needs a **persistent, shared
  cover/thumbnail cache** (reuse/extend `util.thumbnails`) so covers aren't
  re-searched and re-decoded on every scroll or restart, plus a bounded
  in-memory LRU so huge libraries stay smooth. The GridView virtualisation was
  step one (don't realise 1800 widgets); caching is the other half. Treat this
  as a headline item, not polish.


Visual / rendering
------------------

- **Song list text** looks slightly clipped / sub-pixel-mangled (cell renderer,
  separate from the Pango ellipsize bug) — investigate row height / baseline.
- **Pango ellipsize + mixed-size markup bug** (Pango 1.57). Worked around in
  `info.py` by wrapping instead of ellipsizing. Revisit if Pango fixes it
  upstream. Also ship the same fix to `main` (GTK3) — it'll hit the same bug on
  Pango ≥ 1.57 (tracked as a separate small PR).
- **CoverGrid**: `max_columns=24` is a magic number; consider deriving it.
  Cover-size "zoom" is just the existing magnification config — wire it into the
  prefs menu once menus render.


Tooling
-------

- **uv2nix spike** for the dev shell. The poetry `.venv` pins a specific
  store-path Python, so a `nixpkgs` bump strands it on the old glibc (broke audio
  after the 26.05 bump until `poetry env use`). A Nix-managed env rebuilds with
  the flake. Gate on the Windows/msys2 path (uv-on-msys2 is rough; the installer
  uses poetry).


Tests
-----

- Re-check coverage weakened/removed during the migration (see
  `GTK4_MIGRATION_STATUS.md` "Test Follow-ups"): deleted `test_qltk_util.py`,
  shim-coupled `test_plugins_playlist.py`, stubbed `test_qltk_views.py` event
  senders, weakened `test_qltk_paned.py`, etc.

Tray icon has no GTK4 backend
-----------------------------

`Gtk.StatusIcon` is gone in GTK4 and `AppIndicator3` / `AyatanaAppIndicator3` are
GTK3-only libraries, so both former backends are unusable. `systemtray.py` and the
`Gtk.StatusIcon` stub in `_init.py` are deleted; the plugin now raises
`PluginNotSupportedError` at import. `menu.py` (`IndicatorMenu`) is ported and kept.

To restore the feature, implement the `org.kde.StatusNotifierItem` D-Bus spec
directly — that is what AppIndicator wraps, and it needs no GTK.
`tests/plugin/test_trayicon.py` was removed with the backend and should return
alongside it.


Context menus scroll when they use Gio.Menu sections
----------------------------------------------------

**Open bug, root cause found, not yet fixed** (2026-08-02).

A `Gtk.PopoverMenu` built from a model containing `append_section()` is granted
less height than its content needs, so even a short menu gets a scrollbar and
clips its top items. Measured with a `RCMTreeView` in a 400x700 window:

| menu model                          | granted | wanted |     |
|-------------------------------------|---------|--------|-----|
| 4 flat items                        | 120     | 120    | ok  |
| 4 items + 2 submenus                | 180     | 180    | ok  |
| 4 items + 2 submenus, in sections   | 180     | 193    | scrolls |
| 4 sections of 2 items               | 240     | 279    | scrolls |

The shortfall is one section separator (~13px) per section, which is why the
clipping grows with the number of sections — `SongsMenu` uses several, so it
loses around three rows.

Ruled out: submenu size (a 40-item submenu measures the same as a 3-item one,
and the stack is not vhomogeneous); construction order (`new_from_model` with a
fully built model scrolls identically to `set_menu_model` followed by
`append_section`); the choice of parent widget (view vs toplevel); and
`queue_resize()` after popup, which does not recover the height.

**Confirmed a GTK bug, not our misuse** (GTK 4.22.4). It reproduces with no Quod
Libet code in the picture at all:

```python
win = Gtk.Window(); win.set_default_size(400, 700)
label = Gtk.Label(label="x"); label.set_vexpand(True); label.set_hexpand(True)
win.set_child(label); win.present()

model = Gio.Menu()
for s in range(4):                       # 4 sections of 2 items
    section = Gio.Menu()
    for i in range(2):
        section.append(f"S{s} item {i}", None)
    model.append_section(None, section)

pop = Gtk.PopoverMenu.new_from_model(model)
pop.set_parent(label)
pop.set_has_arrow(False)
pop.set_pointing_to(rect_at(20, 40))     # a 1x1 Gdk.Rectangle
pop.popup()
# inner Gtk.ScrolledWindow: get_height() == 240, natural height == 279
```

240 is exactly 8 items x 30px: the three separators are missing from the
allocation. The window is 700px tall and the menu wants 279px, so this is *not*
about running out of room — GTK derives the popup surface height from a measure
that omits section separators. `set_pointing_to()` is needed only to make the
popover map at all in a headless harness.

Workarounds that do **not** work: `set_size_request()` on the popover or
`set_min_content_height()` on the inner scroller, applied either before or after
`popup()`. GTK ignores both and keeps the items-only height.

**Fixed** in `qltk.menu_popup()` by deferring `popup()` with `GLib.idle_add`.
Popping up synchronously sizes the popover's surface before the separators are
laid out; one main loop iteration later GTK measures correctly. `SongsMenu` goes
from `got=210 nat=262` to `got=262 nat=262`, with its sections intact.

Found by reading how other GTK4 apps do this — sshpilot's `context_menu.py`
defers its popup the same way. Anything calling `Gtk.PopoverMenu.popup()`
directly rather than going through `qltk.menu_popup()` will still mis-size.
Still worth reporting upstream with the snippet above.

Reproduce by popping a menu up on a realized view and comparing the inner
`Gtk.ScrolledWindow`'s `get_height()` against its natural height — note popovers
only allocate their contents once genuinely mapped, so a bare harness that never
maps them reports zeros and tells you nothing.


89 destroy() calls were deleted branch-wide
-------------------------------------------

**Partly fixed, mostly outstanding** (2026-08-02). The migration deleted
`destroy()` calls wholesale, leaving comments like
`# GTK4: destroy() removed - win cleaned up automatically`. The premise is only
half true: `Gtk.Widget.destroy()` went in GTK4, but **`Gtk.Window.destroy()` and
`Gtk.NativeDialog.destroy()` did not**. The visible symptom was dialogs and
progress windows that never closed — the tag editor's save window in particular
could not be dismissed at all.

21 window/dialog calls have been restored, each checked against `main`. Counting
`.destroy()` per file across `main` vs this branch shows **89 lost in total**,
concentrated in:

    6  quodlibet/qltk/quodlibetwindow.py
    5  quodlibet/main.py
    5  quodlibet/errorreport/main.py
    4  quodlibet/ext/events/waveformseekbar.py
    3  quodlibet/qltk/exfalsowindow.py, ext/songsmenu/cover_download.py,
       ext/songsmenu/console.py, qltk/seekbutton.py, ext/events/animosd/main.py

Not all should come back: some were `Gtk.Menu` teardown (menus are Gio models
now) and some were `Gtk.Widget.destroy()` on non-window widgets, which is
genuinely gone and is what `qltk.Destroyable` now covers. Each needs checking
against `main` individually — a plain "restore everything" sweep would be wrong.

Regenerate the list by comparing `.destroy()` counts per file between
`git show main:<file>` and the working tree.
