Start a focused GTK4 migration work session.

## Instructions

1. **Check current status**:
   - Read "Remaining shim fronts" in `GTK4_MIGRATION_STATUS.md`,
     but trust fresh greps over the doc when they disagree.
   - Count patched attributes in `quodlibet/_init.py`:
     `grep -cE "^\s+(Gtk|Gdk|GObject|GLib|Gio|Pango)\.[A-Za-z_.]+ = " quodlibet/_init.py`
   - Count `# TODO GTK4` markers in `quodlibet/`.

2. **Show the priority queue** (largest shim fronts first):
   - `Gtk.Menu*` + `Gtk.PopoverMenu` compat patches → `Gio.Menu` (one pass, not per menu)
   - `Gtk.Dialog.run` / `NativeDialog.run` and the main-loop shims
   - `Gtk.Table` → `Gtk.Grid`, `Gtk.HScale` / `VScale` → `Gtk.Scale`
   - Small one-attribute shims

3. **Ask the user** which front to tackle, using AskUserQuestion.

4. **Finding call sites**: instrument the shim to log its callers, then run the suite;
   static greps miss dynamic callers.
   Diff against `main` before removing a no-op shim: guarded calls to it may carry real logic.

5. **Reference**: `GTK4_MIGRATION_STATUS.md`, `GTK4_POST_MIGRATION_CLEANUP.md`,
   https://docs.gtk.org/gtk4/migrating-3to4.html
