GTK4 Post-Migration Cleanup Backlog
===================================

Things to improve / normalise / declutter **once the GTK4 migration has landed**.
Append to this as we go; don't act on these mid-migration unless they're blocking.
Companion to `GTK4_MIGRATION_STATUS.md` (current state) — this file is the "later" list.


Shims to remove (`quodlibet/_init.py`)
--------------------------------------

Each shim is technical debt; remove it once **all** call sites use the native API,
so the tree stays runnable throughout.

- `Gtk.PopoverMenu` `append`/`__init__`/`popup` shims — die with the `Gio.Menu`
  migration (see below).
- `Gtk.MenuItem = Button`, `Gtk.CheckMenuItem = CheckButton`, `Gtk.ImageMenuItem`
  dummy — same migration.
- `Gtk.Box.prepend`/`append` arg-swallowing compat (they ignore the old
  `expand/fill/padding`) — remove after the `pack_start` sweep below.
- `GObject.Object.connect`/`connect_after` compat that silently drops removed
  event signals (`button-press-event`, `key-press-event`, …) — remove once all
  call sites use `Gtk.EventController*`. This shim hides real breakage, so it's a
  priority to retire.
- `Gtk.Alignment`, `Gtk.Widget.show_all`/`set_no_show_all` no-ops, and the various
  `add()`→`set_child()`/`append()` container shims — remove as call sites migrate.


Systematic sweeps
-----------------

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

- **`Gio.Menu` migration** (the big one, in progress). `SongsMenu` first
  (un-blanks right-click everywhere), then the prefs `Gtk.Menu`s. Ratings +
  Add-to-Playlist become native submenus; custom inline widgets via
  `PopoverMenu.add_child`.
- **`qltk/info.py`** still uses shimmed GTK3 signal connects (`populate-popup`,
  `key-press-event`, `button-press-event`). Migrate to `EventController*` /
  `Gtk.Label` extra-menu once the menu story lands.
- **`Gtk.Image` subclasses that show arbitrary images** — `WebImage`
  (`qltk/x.py`) and `ResizeWebImage` (`ext/songsmenu/cover_download.py`) hit the
  same tiny-render trap as CoverGrid; port to `Gtk.Picture`/snapshot.
- **`TreeViewHints.__motion`** is unwired (truncated-cell hover tooltips gone) —
  needs a `Gtk.EventControllerMotion` with widget-coord translation.


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
