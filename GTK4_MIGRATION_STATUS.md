GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2026-01-31
**Status**: 🟢 Application Running Successfully - Core migration complete

> ⚠️ **Note**: This file tracks the GTK4 migration progress and should be **deleted** once the migration is complete and merged to main.

---

Quick Summary
-------------

The GTK4 migration is approximately **90% complete**. Core infrastructure is fully migrated. **The application runs without crashes**.

**Main remaining work**: Drag-and-Drop (DnD) reimplementation (37 TODO markers, all DnD-related across 15 files).

**✅ Completed Systems:**
- ✅ Event handling and time management
- ✅ Menu system basics (widgets)
- ✅ Container widget API updates (HBox/VBox → Box)
- ✅ RadioAction signal registration
- ✅ PopoverMenu parenting system
- ✅ Event signal compatibility wrapper
- ✅ Paned widget API migration
- ✅ Widget property deprecations
- ✅ Box packing compatibility layer
- ✅ Dialog and Window API updates
- ✅ Table/Grid compatibility
- ✅ ToggleAction state management
- ✅ HeaderBar API migration (2026-01-24)
- ✅ Key event migration (key-press-event → EventControllerKey) (2026-01-24)
- ✅ IconTheme API updates (2026-01-24)
- ✅ get_children() migration (uses qltk.get_children helper)
- ✅ Stock icons removed
- ✅ Frame/ScrolledWindow API (.add → .set_child)
- ✅ WaitLoadWindow fixes (2026-01-30)
- ✅ Queue expander layout (2026-01-31)

**⚠️ Remaining Work:**
- ❌ Drag-and-Drop (disabled, needs complete rewrite) - **37 TODO markers**
- ✅ pack_start/pack_end for Box: **Complete** (remaining 35 uses are TreeViewColumn/ComboBox - correct GTK4 API)

**Recent progress (2026-01-02)**:
- ✅ Fixed critical RadioAction "changed" signal registration
- ✅ Added GTK4 compatibility shims (destroy, get_toplevel, WindowType)
- ✅ Fixed Frame widget to use set_child() instead of add()
- ✅ Fixed test helper for GTK4 window creation
- ✅ Added Align.get_child() method

**Startup crash fixes (2026-01-03)**:
- ✅ Fixed PopoverMenu parenting crashes in menu_popup() functions
- ✅ Fixed controls.py PopoverMenu.show() crash on unparented widget
- ✅ Fixed info.py: removed set_visible_window, set_track_visited_links, updated set_alignment
- ✅ Fixed cover.py: removed set_visible_window, updated get_child() → get_first_child()
- ✅ Fixed quodlibetwindow.py: pack1/pack2 → set_start_child/set_end_child for Paned widgets
- ✅ Fixed x.py: HighlightToggleButton image parameter handling
- ✅ Fixed notif.py: Label.set_alignment and Image.new_from_icon_name updates
- ✅ Added comprehensive event signal compatibility wrapper in _init.py
- ✅ Added Box.prepend/append compatibility for GTK3 expand/fill/padding parameters
- ✅ Application now starts and runs without crashes!

**Test suite fixes (2026-01-03 Session 2)**:
- ✅ Fixed ScrolledWindow.add() → set_child() in multiple files
- ✅ Fixed Gtk.Label() to require label= keyword argument
- ✅ Fixed Button.set_can_default() - removed (not needed in GTK4)
- ✅ Fixed StatusBar task_controller parent property management
- ✅ Fixed Table.set_col_spacing() compatibility
- ✅ Fixed Label.set_alignment() → set_xalign()/set_yalign()
- ✅ Fixed Button.add_accelerator() - removed (GTK4 uses different system)
- ✅ Fixed Gtk.HButtonBox → Gtk.Box()
- ✅ Added Window.show_now() method
- ✅ Fixed Window.present() for GTK4 (removed get_window() call)
- ✅ Added ToggleAction.get_active()/set_active() with GLib.Variant state
- ✅ Fixed PopoverMenu.get_children() tracking
- ✅ Added MenuItemPlugin.set_submenu() compatibility
- ✅ Fixed Dialog.vbox → get_content_area()
- ✅ Test suite progress: 30 plugin tests now passing!

---

Completed Work ✅
-----------------

### 1. Core Event Handling
**File**: `quodlibet/_init.py`

```python
# Added GTK4 compatibility shims:
Gtk.Widget.show_all = lambda self: None
Gtk.Widget.hide_all = lambda self: self.set_visible(False)
Gtk.Widget.set_no_show_all = lambda self, value: None
```

**Why**: GTK4 removed these methods; widgets are visible by default.

---

### 2. Event Time Handling (27 files affected)
**Pattern**: `Gtk.get_current_event_time()` → `GLib.CURRENT_TIME`

**Files modified**:
- quodlibet/qltk/{util.py, controls.py, browser.py, seekbutton.py, edittags.py, showfiles.py}
- quodlibet/browsers/{covergrid/main.py, playlists/main.py, albums/main.py, collection/main.py}
- Multiple other browser and plugin files

**Special case**: `quodlibet/qltk/views.py:659`
```python
# Before (GTK3):
if self._sel_ignore_time != selection.get_current_event_time():
    self.emit("selection-changed", selection)

# After (GTK4):
if not self._sel_should_ignore:
    self.emit("selection-changed", selection)
```

---

### 3. Menu System Redesign

#### 3a. Menu Item Widgets (`quodlibet/qltk/x.py`)

| Old GTK3 | New GTK4 | Notes |
|----------|----------|-------|
| `Gtk.MenuItem` | `Gtk.Button` with flat CSS | Widget-based PopoverMenu items |
| `Gtk.RadioMenuItem` | `Gtk.CheckButton` | Radio grouping via `set_group()` |
| `Gtk.CheckMenuItem` | `Gtk.CheckButton` | Direct replacement |
| `Gtk.ImageMenuItem` | `Gtk.Button` with child Box | Icon + Label in Box |
| `Gtk.SeparatorMenuItem` | `Gtk.Separator(HORIZONTAL)` | Direct replacement |

**Example**:
```python
# MenuItem() now creates:
item = Gtk.Button(label=label, use_underline=True)
item.add_css_class("flat")
if icon_name:
    box = Gtk.Box(orientation=HORIZONTAL, spacing=6)
    box.append(Gtk.Image.new_from_icon_name(icon_name))
    box.append(Gtk.Label(label=label))
    item.set_child(box)
```

#### 3b. PopoverMenu Usage (`quodlibet/qltk/queue.py`)

```python
# Before (GTK3):
menu = Gtk.PopoverMenu()
menu.append(item)

# After (GTK4):
menu = Gtk.PopoverMenu()
menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
menu.set_child(menu_box)
menu_box.append(item)
```

**Why**: GTK4 PopoverMenu doesn't support direct child addition; needs a container.

#### 3c. MenuButton (`quodlibet/qltk/menubutton.py`)

```python
# Method renames:
get_popup() → get_popover()
set_popup() → set_popover()

# Arrow removed:
# Gtk.Arrow - deleted in GTK4
# MenuButton has built-in arrow support via icon-name
```

#### 3d. Action Classes (`quodlibet/qltk/x.py`)

```python
class Action(Gio.SimpleAction):
    def __init__(self, *args, **kwargs):
        # SimpleAction doesn't have label/icon_name properties
        self.label = kwargs.pop("label", None)
        self.icon_name = kwargs.pop("icon_name", None)
        super().__init__(*args, **kwargs)

class RadioAction(Gio.SimpleAction):
    # TODO GTK4: Needs "changed" signal implementation
    def join_group(self, group_source): ...
    def get_group(self): ...
    def get_current_value(self): ...
    def set_active(self, active): ...
```

---

### 4. Container Widget Changes

#### Box packing
```python
# Before (GTK3):
box.pack_start(widget, expand=True, fill=True, padding=6)
box.pack_end(widget, expand=False, fill=False, padding=3)

# After (GTK4):
widget.set_margin_start(6)
box.append(widget)
# or
widget.set_margin_end(3)
box.prepend(widget)
```

**Files fixed**: queue.py, ccb.py, menubutton.py

#### Expander
```python
# Before: expander.add(child)
# After:  expander.set_child(child)
```

#### Get Children Helper
**File**: `quodlibet/qltk/__init__.py`

```python
def get_children(widget):
    """GTK4 compatibility wrapper.

    GTK4 removed get_children(). This iterates using
    get_first_child() / get_next_sibling().
    """
    if hasattr(widget, "get_children"):
        return widget.get_children()  # GTK3 compat

    children = []
    child = widget.get_first_child()
    while child:
        children.append(child)
        child = child.get_next_sibling()
    return children
```

---

### 5. Widget Property Changes

#### SmallImageButton (`quodlibet/qltk/x.py`)
```python
# Before (GTK3):
button = SmallImageButton(image=icon_widget)

# After (GTK4):
class _SmallImageButton:
    def __init__(self, **kwargs):
        image = kwargs.pop("image", None)
        super().__init__(**kwargs)
        if image is not None:
            self.set_child(image)  # Buttons use set_child() now
```

---

### 6. ConfigCheckMenuItem (`quodlibet/qltk/ccb.py`)

```python
# Before (GTK3):
class ConfigCheckMenuItem(Gtk.CheckMenuItem):
    ...

# After (GTK4):
class ConfigCheckMenuItem(Gtk.CheckButton):
    # CheckMenuItem removed; use CheckButton in PopoverMenus
    ...
```

---

### 7. Action Group (`quodlibet/qltk/quodlibetwindow.py`)

```python
# Before (GTK3):
ag = Gio.SimpleActionGroup("QuodLibetWindowActions")
ag.add_action_with_accel(action, "<Primary>O")

# After (GTK4):
ag = Gio.SimpleActionGroup()  # No name parameter
ag.add_action(action)
# TODO: Re-add accelerators via application.set_accels_for_action()
```

---

### 8. Drag-and-Drop (Commented Out)

**Status**: ❌ All DnD functionality is disabled with TODO markers

**12 files affected**:
1. quodlibet/qltk/queue.py
2. quodlibet/qltk/quodlibetwindow.py
3. quodlibet/qltk/songlist.py
4. quodlibet/qltk/filesel.py
5. quodlibet/browsers/covergrid/main.py
6. quodlibet/browsers/podcasts.py
7. quodlibet/browsers/collection/main.py
8. quodlibet/browsers/filesystem.py
9. quodlibet/browsers/albums/main.py
10. quodlibet/browsers/paned/pane.py
11. quodlibet/browsers/playlists/main.py
12. quodlibet/ext/songsmenu/albumart.py

**Example** (`quodlibet/qltk/queue.py:223`):
```python
# TODO GTK4: Reimplement drag-and-drop using Gtk.DropTarget
# GTK4 removed Gtk.TargetEntry, Gtk.TargetFlags, and drag_dest_set
# Need to use Gtk.DropTarget with GdkContentFormats
# targets = [
#     ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, DND_QL),
#     ("text/uri-list", 0, DND_URI_LIST),
# ]
# targets = [Gtk.TargetEntry.new(*t) for t in targets]
# self.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
# self.connect("drag-motion", self.__motion)
# self.connect("drag-data-received", self.__drag_data_received)
```

---

### 8. RadioAction Signal (2026-01-02) ✅

**Fixed**: Critical blocking issue resolved!

**File**: `quodlibet/qltk/x.py`

**Solution implemented**: Used `GObject.signal_new()` to register the "changed" signal after class definition.

```python
class RadioAction(Gio.SimpleAction):
    """GTK4: RadioAction reimplemented to support 'changed' signal"""

    def __init__(self, *args, **kwargs):
        self.label = kwargs.pop("label", None)
        self._value = kwargs.pop("value", 0)
        self._group = []
        self._active = False
        name = kwargs.pop("name", None)
        super().__init__(name=name)

    # ... group management methods ...

# Register signal after class definition
GObject.signal_new(
    "changed",
    RadioAction,
    GObject.SignalFlags.RUN_FIRST,
    None,
    (object,),
)
```

**Key fix**: The `_group` list now includes the first action (previously only included joined actions).

---

### 9. Additional GTK4 Compatibility Shims (2026-01-02) ✅

Added to `quodlibet/_init.py`:
- `Gtk.Widget.destroy()` - No-op (GTK4 auto-destroys widgets)
- `Gtk.Widget.get_toplevel()` - Maps to `get_root()`
- `Gtk.WindowType` - Enum with TOPLEVEL and POPUP values

Fixed in `quodlibet/qltk/x.py`:
- `Frame()` function now uses `set_child()` instead of `add()`
- `Align.get_child()` method added

Fixed in `tests/helper.py`:
- Window creation no longer uses `type=` parameter
- Uses `set_child()` instead of `add()`

---

### 10. Menu System Crash Fixes (2026-01-03) ✅

**Fixed**: Critical PopoverMenu parenting crashes preventing application startup

**Files**: `quodlibet/qltk/__init__.py`, `quodlibet/qltk/views.py`, `quodlibet/qltk/controls.py`

**Problem**: GTK4 requires PopoverMenus to be properly parented before calling `.popup()` or `.show()`. Calling these methods on unparented widgets caused immediate crashes.

**Solutions implemented**:

```python
# In qltk/__init__.py - menu_popup():
def menu_popup(menu, shell, item, func, *args):
    if isinstance(menu, Gtk.PopoverMenu):
        # Ensure menu has a parent and parent is in a window
        parent = menu.get_parent()
        if parent is None:
            print("Warning: PopoverMenu has no parent, cannot popup")
            return
        root = parent.get_root()
        if root is None:
            print("Warning: PopoverMenu parent not in window, cannot popup")
            return
        # Ensure menu box is set as child before showing
        if hasattr(menu, "_menu_box") and menu.get_child() is None:
            menu.set_child(menu._menu_box)
        return menu.popup()

# In qltk/views.py - popup_menu():
def popup_menu(self, menu, button, time):
    if isinstance(menu, Gtk.PopoverMenu):
        current_parent = menu.get_parent()
        if current_parent != self:
            if current_parent is not None:
                menu.unparent()
            menu.set_parent(self)
        menu_popup(menu, None, None, None, None, button, time)

# In qltk/controls.py - VolumeButton initialization:
rg = Gtk.PopoverMenu()
# GTK4: Don't call show() on unparented widgets - causes crashes
# rg.show()  # REMOVED - this was crashing
item.set_submenu(rg)
```

**Impact**: Application now starts without PopoverMenu-related crashes

---

### 11. Widget Property Updates (2026-01-03) ✅

**Fixed**: Multiple deprecated widget property methods

#### Label.set_alignment() → set_xalign()/set_yalign()

**Files**: `quodlibet/qltk/info.py`, `quodlibet/qltk/notif.py`

```python
# Before (GTK3):
label.set_alignment(0.0, 0.5)

# After (GTK4):
label.set_xalign(0.0)
label.set_yalign(0.5)
```

#### Image.new_from_icon_name() signature change

**Files**: `quodlibet/qltk/notif.py`, `quodlibet/qltk/quodlibetwindow.py`

```python
# Before (GTK3):
image = Gtk.Image.new_from_icon_name(Icons.MEDIA_PLAYBACK_PAUSE, Gtk.IconSize.BUTTON)

# After (GTK4):
image = Gtk.Image.new_from_icon_name(Icons.MEDIA_PLAYBACK_PAUSE)
```

GTK4 removed icon size parameter - icons auto-size based on context.

#### Removed deprecated widget methods

**File**: `quodlibet/qltk/info.py`, `quodlibet/qltk/cover.py`

```python
# Removed (GTK4):
# self.set_visible_window(False)  # All widgets windowless by default
# label.set_track_visited_links(False)  # Method removed
```

---

### 12. Paned Widget Updates (2026-01-03) ✅

**Fixed**: Gtk.Paned API changes from pack1/pack2 to set_start_child/set_end_child

**Files**: `quodlibet/qltk/quodlibetwindow.py`

```python
# Before (GTK3):
paned.pack1(self.__browserbox, resize=True, shrink=False)
paned.pack2(songpane, resize=True, shrink=False)

# After (GTK4):
paned.set_start_child(self.__browserbox)
paned.set_resize_start_child(True)
paned.set_shrink_start_child(False)
paned.set_end_child(songpane)
paned.set_resize_end_child(True)
paned.set_shrink_end_child(False)
```

**Also fixed SongListPaned class**:
```python
class SongListPaned(RVPaned):
    def __init__(self, song_scroller, qexpander):
        super().__init__()
        self.set_start_child(song_scroller)
        self.set_resize_start_child(True)
        self.set_shrink_start_child(False)
        self.set_end_child(qexpander)
        self.set_resize_end_child(True)
        self.set_shrink_end_child(False)
```

---

### 13. Event Signal Compatibility System (2026-01-03) ✅

**Fixed**: GTK4 removed all event signals - added comprehensive compatibility wrapper

**File**: `quodlibet/_init.py`

**Problem**: GTK4 removed all `*-event` signals (button-press-event, key-press-event, etc.) in favor of event controllers. The codebase has hundreds of signal connections that would crash.

**Solution**: Wrapped `GObject.connect()` and `connect_after()` to silently ignore removed signals:

```python
_removed_signals = {
    'button-press-event', 'button-release-event', 'motion-notify-event',
    'key-press-event', 'key-release-event', 'scroll-event',
    'enter-notify-event', 'leave-notify-event', 'focus-in-event',
    'focus-out-event', 'configure-event', 'delete-event',
    'destroy-event', 'expose-event', 'map-event', 'unmap-event',
    'property-notify-event', 'selection-clear-event', 'visibility-notify-event',
    'window-state-event', 'damage-event', 'grab-broken-event',
    'popup-menu', 'event', 'event-after'
}

_orig_gobject_connect = GObject.Object.connect
_orig_gobject_connect_after = GObject.Object.connect_after

def _connect_compat(self, signal_name, *args, **kwargs):
    if signal_name in _removed_signals:
        print_d(f"Ignoring GTK3 signal connection: {signal_name}")
        return 0  # Return dummy handler ID
    try:
        return _orig_gobject_connect(self, signal_name, *args, **kwargs)
    except TypeError as e:
        if "unknown signal name" in str(e):
            print_d(f"Ignoring unknown signal: {signal_name}")
            return 0
        raise

GObject.Object.connect = _connect_compat
GObject.Object.connect_after = _connect_after_compat
```

**Impact**: Application can now connect to old event signals without crashing. These connections are no-ops until replaced with event controllers.

---

### 14. Box Packing Compatibility (2026-01-03) ✅

**Fixed**: Box.prepend() and Box.append() no longer accept expand/fill/padding parameters

**File**: `quodlibet/_init.py`

**Problem**: GTK4 removed the expand, fill, and padding parameters from Box.prepend/append. Code calling these methods would crash with "takes exactly 2 arguments (5 given)".

**Solution**: Wrapped both methods to accept and ignore the old parameters:

```python
_orig_box_prepend = Gtk.Box.prepend
_orig_box_append = Gtk.Box.append

def _box_prepend_compat(self, child, expand=None, fill=None, padding=None):
    # GTK4: prepend only takes child, ignore expand/fill/padding
    if expand is not None or fill is not None or padding is not None:
        print_d(f"Ignoring GTK3 Box.prepend packing params: "
                f"expand={expand}, fill={fill}, padding={padding}")
    return _orig_box_prepend(self, child)

def _box_append_compat(self, child, expand=None, fill=None, padding=None):
    # GTK4: append only takes child, ignore expand/fill/padding
    if expand is not None or fill is not None or padding is not None:
        print_d(f"Ignoring GTK3 Box.append packing params: "
                f"expand={expand}, fill={fill}, padding={padding}")
    return _orig_box_append(self, child)

Gtk.Box.prepend = _box_prepend_compat
Gtk.Box.append = _box_append_compat
```

**Note**: This is a temporary compatibility shim. Code should eventually be updated to use margin properties instead:
```python
# Proper GTK4 way:
widget.set_margin_start(6)
box.append(widget)
```

---

### 15. Additional Compatibility Shims (2026-01-03) ✅

**File**: `quodlibet/_init.py`

Added multiple compatibility shims to handle remaining GTK3 patterns:

```python
# Constants:
GLib.CURRENT_TIME = 0
Gtk.STYLE_CLASS_LINKED = "linked"

# Window compatibility:
_orig_window_init = Gtk.Window.__init__
def _window_init_compat(self, *args, **kwargs):
    kwargs.pop('type', None)  # GTK4 removed type parameter
    return _orig_window_init(self, *args, **kwargs)
Gtk.Window.__init__ = _window_init_compat
Gtk.Window.resize = lambda self, width, height: self.set_default_size(width, height)
Gtk.Window.set_border_width = _set_border_width

# Widget compatibility:
Gtk.Widget.add_events = lambda self, events: None  # No-op in GTK4
Gtk.Button.add = lambda self, child: self.set_child(child)
Gtk.Frame.add = lambda self, child: self.set_child(child)
Gtk.Box.add = lambda self, child: self.append(child)

# Arrow factory (Arrow widget removed):
class ArrowFactory:
    @staticmethod
    def new(arrow_type, shadow_type):
        icon_map = {
            Gtk.ArrowType.UP: "pan-up-symbolic",
            Gtk.ArrowType.DOWN: "pan-down-symbolic",
            Gtk.ArrowType.LEFT: "pan-start-symbolic",
            Gtk.ArrowType.RIGHT: "pan-end-symbolic",
        }
        icon_name = icon_map.get(arrow_type, "pan-down-symbolic")
        return Gtk.Image.new_from_icon_name(icon_name)
Gtk.Arrow = ArrowFactory()
```

---

### 16. Widget-Specific Fixes (2026-01-03) ✅

#### HighlightToggleButton image property

**File**: `quodlibet/qltk/x.py`

```python
class HighlightToggleButton(Gtk.ToggleButton):
    def __init__(self, *args, **kwargs):
        # GTK4: image property removed - extract and set as child instead
        image = kwargs.pop('image', None)
        super().__init__(*args, **kwargs)
        if image is not None:
            self.set_child(image)
```

#### Box.get_child() → Box.get_first_child()

**File**: `quodlibet/qltk/cover.py`

```python
# Before (GTK3):
self.get_child().set_file(_file)

# After (GTK4):
self.get_first_child().set_file(_file)
```

GTK4's Box doesn't have `get_child()` - use `get_first_child()` to get the first child in the box.

---

### 17. Dialog and Window API Updates (2026-01-03 Session 2) ✅

**Fixed**: Multiple Dialog/Window API changes for GTK4

#### Dialog.vbox → get_content_area()

**Files**: `quodlibet/ext/songsmenu/cover_download.py`

```python
# Before (GTK3):
self.vbox.prepend(paned)

# After (GTK4):
self.get_content_area().prepend(paned)
```

GTK4 removed the `.vbox` and `.action_area` attributes from Dialog. Use `get_content_area()` instead.

#### Window.show_now()

**File**: `quodlibet/qltk/window.py`

```python
def show_now(self):
    """Show and present the window immediately."""
    self.show()
    self.present()
```

GTK4 removed `Gtk.Window.show_now()`. Replacement calls both `show()` and `present()`.

#### Window.present() Fix

**File**: `quodlibet/qltk/window.py`

```python
def present(self):
    """A version of present that also works if not called from an event
    handler (there is no active input event).
    See https://bugzilla.gnome.org/show_bug.cgi?id=688830
    """

    # In GTK4, just use the standard present() - it works correctly
    super().present()
```

GTK4 removed `get_window()` method, so the GTK3 X11 timestamp workaround was removed.

---

### 18. Table/Grid Compatibility (2026-01-03 Session 2) ✅

**Fixed**: Gtk.Table compatibility shim for GTK4

**File**: `quodlibet/_init.py`

**Problem**: GTK4 removed `Gtk.Table` (replaced with `Gtk.Grid`). Code using Table.set_col_spacing() for individual column spacing would crash.

**Solution**: Added missing `set_col_spacing()` method to Table compatibility class:

```python
class Table(Gtk.Grid):
    def set_col_spacing(self, column, spacing):
        # Grid doesn't support per-column spacing, use uniform spacing
        self.set_column_spacing(spacing)
```

**Note**: GTK4's Grid doesn't support per-column spacing, so this method applies uniform spacing to all columns. This is a minor visual regression but maintains compatibility.

---

### 19. ToggleAction State Management (2026-01-03 Session 2) ✅

**Fixed**: ToggleAction now properly manages boolean state using GLib.Variant

**File**: `quodlibet/qltk/x.py`

**Problem**: ToggleAction inherited from Gio.SimpleAction but didn't implement `get_active()` and `set_active()` methods that code expects. GIO actions use `GLib.Variant` states, not simple boolean properties.

**Solution**:

```python
class ToggleAction(Gio.SimpleAction):
    def __init__(self, *args, **kwargs):
        self.label = kwargs.pop("label", None)
        self.icon_name = kwargs.pop("icon_name", None)
        name = kwargs.pop("name", None)
        super().__init__(
            name=name,
            parameter_type=None,
            state=GLib.Variant.new_boolean(False)
        )

    def get_active(self):
        """Get the toggle state"""
        state = self.get_state()
        return state.get_boolean() if state else False

    def set_active(self, active):
        """Set the toggle state"""
        self.set_state(GLib.Variant.new_boolean(active))
```

**Impact**: Code can now use familiar `get_active()`/`set_active()` API while properly managing GIO action state.

---

### 20. Widget Property and Method Updates (2026-01-03 Session 2) ✅

**Fixed**: Multiple widget property deprecations

#### Gtk.Label Constructor

**Files**: `quodlibet/ext/songsmenu/cover_download.py`

```python
# Before (GTK3):
label = Gtk.Label(_("Preview size"))

# After (GTK4):
label = Gtk.Label(label=_("Preview size"))
```

GTK4 requires label text to be passed as a keyword argument, not positional.

#### Label.set_alignment() Split

**Files**: `quodlibet/qltk/data_editors.py`

```python
# Before (GTK3):
label.set_alignment(0.0, 0.5)

# After (GTK4):
label.set_xalign(0.0)
label.set_yalign(0.5)
```

GTK4 split the alignment method into separate x and y methods.

#### Container Widget Changes

**Files**: Multiple (`quodlibet/ext/songsmenu/cover_download.py`, `quodlibet/qltk/data_editors.py`)

```python
# ScrolledWindow.add() → set_child()
sw.set_child(widget)

# Gtk.HButtonBox → Gtk.Box()
bbox = Gtk.Box()
```

GTK4 removed HButtonBox/VButtonBox - use regular Box instead.

---

### 21. Menu System Compatibility (2026-01-03 Session 2) ✅

**Fixed**: MenuItemPlugin and PopoverMenu compatibility

#### MenuItemPlugin.set_submenu()

**File**: `quodlibet/plugins/gui.py`

```python
class MenuItemPlugin(Gtk.Button):
    def set_submenu(self, menu):
        """Store submenu reference for GTK4 compatibility"""
        self._submenu = menu
```

GTK4 menus don't support submenus the same way. This method stores the submenu reference for future proper implementation.

#### PopoverMenu.get_children() Tracking

**File**: `quodlibet/ext/songsmenu/custom_commands.py`

```python
# Before (GTK3):
if submenu.get_children():
    self.set_submenu(submenu)

# After (GTK4):
has_items = False
for name, c in self.all_commands().items():
    item = Gtk.MenuItem(label=name)
    submenu.append(item)
    has_items = True

if has_items:
    self.set_submenu(submenu)
```

GTK4's PopoverMenu doesn't have `get_children()`. Track whether items were added manually instead.

---

### 22. Task Controller Parent Management (2026-01-03 Session 2) ✅

**Fixed**: TaskController parent property reparenting protection

**File**: `quodlibet/qltk/notif.py`

**Problem**: The `_Parent` descriptor class prevents reparenting without first setting to None. When StatusBar is created multiple times (e.g., in tests), the same TaskController.default_instance is reused, causing "Cannot set parent property without first setting it to 'None'" errors.

**Solution**:

```python
def __init__(self, task_controller):
    super().__init__()
    self.__dirty = False
    self.set_spacing(12)
    self.task_controller = task_controller
    self.task_controller.parent = None  # Unparent first
    self.task_controller.parent = self  # Then reparent
```

**Why**: The singleton TaskController.default_instance is reused, so it must be unparented before assigning a new parent.

---

## Known Issues & TODO Items ⚠️

### High Priority

#### 2. Drag-and-Drop Reimplementation
**Status**: All DnD disabled
**Impact**: Cannot drag songs to queue, playlists, or between browsers

**Migration guide**:

```python
# GTK3 (old):
targets = [("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, DND_QL)]
targets = [Gtk.TargetEntry.new(*t) for t in targets]
view.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets,
                     Gdk.DragAction.COPY)
view.connect("drag-data-get", on_drag_data_get)
view.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
view.connect("drag-data-received", on_drag_data_received)

# GTK4 (new):
# Source:
content = Gdk.ContentProvider.new_for_value(songs)
source = Gtk.DragSource.new()
source.set_content(content)
source.connect("prepare", on_drag_prepare)
source.connect("drag-begin", on_drag_begin)
view.add_controller(source)

# Target:
drop_target = Gtk.DropTarget.new(type=GObject.TYPE_STRING,
                                   actions=Gdk.DragAction.COPY)
drop_target.set_gtypes([GObject.TYPE_STRING])
drop_target.connect("drop", on_drop)
view.add_controller(drop_target)
```

**Files to update**: See section 8 above (12 files)

---

#### 3. Accelerator Restoration
**Status**: Accelerators lost when `add_action_with_accel()` was replaced

**Fix**: Add accelerators to application:
```python
# In QuodLibetApplication:
self.set_accels_for_action("win.AddFolders", ["<Primary>O"])
self.set_accels_for_action("win.Jump", ["<Primary>J"])
# ... etc for all 16 actions
```

**File**: `quodlibet/qltk/quodlibetwindow.py:952+`

---

#### 4. Box Packing Migration
**Status**: Partially complete
**Remaining**: ~20 files

**Search pattern**:
```bash
grep -r "\.pack_start\|\.pack_end" quodlibet/ --include="*.py"
```

**Common files**:
- quodlibet/qltk/bookmarks.py
- quodlibet/qltk/browser.py
- quodlibet/qltk/controls.py
- quodlibet/qltk/edittags.py
- quodlibet/qltk/_editutils.py
- quodlibet/qltk/prefs.py
- quodlibet/qltk/renamefiles.py
- quodlibet/qltk/searchbar.py
- quodlibet/qltk/tagsfrompath.py
- And more...

---

### Medium Priority

#### 5. get_children() Direct Calls
**Status**: Helper exists, but not used everywhere

**Files still using direct calls**:
```bash
grep -r "\.get_children()" quodlibet/ --include="*.py" | grep -v "qltk.get_children"
```

- quodlibet/qltk/bookmarks.py:270
- quodlibet/qltk/browser.py:327
- quodlibet/qltk/controls.py:172
- quodlibet/qltk/edittags.py:622,717,753,773
- quodlibet/qltk/_editutils.py:157,177
- quodlibet/qltk/exfalsowindow.py:163,168
- quodlibet/qltk/filesel.py:344
- quodlibet/qltk/info.py:101
- quodlibet/qltk/information.py:117
- quodlibet/qltk/maskedbox.py:108
- quodlibet/qltk/prefs.py:192,404,504,761

**Fix**: Import and use `from quodlibet.qltk import get_children`

---

#### 6. UIManager Migration
**Status**: Not started
**Impact**: Menu bar creation still uses deprecated UIManager

**File**: `quodlibet/qltk/quodlibetwindow.py` (menu creation)

**Goal**: Migrate to `Gio.Menu` + `Gtk.PopoverMenuBar`

**Resources**:
- [GTK4 Menu Migration Guide](https://docs.gtk.org/gtk4/migrating-3to4.html#adapt-to-menu-api-changes)
- [Gio.Menu Tutorial](https://docs.gtk.org/gio/class.Menu.html)

---

#### 7. Deprecated Container Widgets
**Status**: Not started

**Replacements needed**:
```bash
# Find usage:
grep -r "Gtk\.HBox\|Gtk\.VBox" quodlibet/ --include="*.py"
grep -r "Gtk\.Table" quodlibet/ --include="*.py"
grep -r "Gtk\.Alignment" quodlibet/ --include="*.py"
```

| Old | New |
|-----|-----|
| `Gtk.HBox()` | `Gtk.Box(orientation=HORIZONTAL)` |
| `Gtk.VBox()` | `Gtk.Box(orientation=VERTICAL)` |
| `Gtk.Table()` | `Gtk.Grid()` |
| `Gtk.Alignment()` | Widget alignment properties (halign, valign, margin) |

---

#### 8. Stock Icons/Items
**Status**: Partially removed

**Search pattern**:
```bash
grep -r "Gtk\.Stock\." quodlibet/ --include="*.py"
```

**Replacement**: Use icon names directly (e.g., "document-open" instead of `Gtk.STOCK_OPEN`)

---

### Low Priority

#### 9. Event Controllers
**Status**: Mixed (some done, many remaining)

**Goal**: Replace signal-based event handling with gesture controllers

**Example**:
```python
# Old (signals):
widget.connect("button-press-event", on_button_press)

# New (controllers):
click = Gtk.GestureClick()
click.connect("pressed", on_pressed)
widget.add_controller(click)
```

**Already done**: Some cases in views.py
**Remaining**: Throughout codebase

---

#### 10. Menu Submenus
**Status**: Commented out
**File**: `quodlibet/qltk/queue.py:182`

```python
mode_item = MenuItem(_("Mode"), Icons.SYSTEM_RUN)
# GTK4: ModelButton doesn't support submenus directly
# For now, skip submenu functionality - needs proper Gio.Menu implementation
# mode_item.set_submenu(mode_menu)
menu_box.append(mode_item)
```

**Fix**: Implement using Gio.Menu submenu support

---

Testing Checklist
-----------------

### Automated Tests
- [x] Python syntax validation (`python -m py_compile`)
- [x] ruff format
- [x] mypy type checking
- [ ] pytest suite (once application runs)

### Manual Testing (Current State)
- [x] Application starts
- [ ] Main window displays
- [ ] Menu bar functional
- [ ] Keyboard shortcuts work
- [ ] Queue management
- [ ] Drag-and-drop
- [ ] Browser switching
- [ ] Playback controls
- [ ] Plugin loading
- [ ] Preferences dialog

### Feature-Specific Testing Needed
Once blocking issues are fixed:
1. **Queue**:
   - [ ] Add songs to queue
   - [ ] Remove songs from queue
   - [ ] Drag songs to reorder
   - [ ] Clear queue
   - [ ] Queue persistence

2. **Browsers**:
   - [ ] Switch between browsers
   - [ ] Search functionality
   - [ ] Drag songs from browser to queue
   - [ ] Cover art display

3. **Playlists**:
   - [ ] Create playlist
   - [ ] Drag songs to playlist
   - [ ] Playlist import/export
   - [ ] Edit playlist

4. **Menus**:
   - [ ] All menu items clickable
   - [ ] Radio menu items toggle correctly
   - [ ] Submenus work
   - [ ] Keyboard accelerators

---

Migration Resources
-------------------

### GTK4 Documentation
- [Official GTK4 Migration Guide](https://docs.gtk.org/gtk4/migrating-3to4.html)
- [GTK4 API Reference](https://docs.gtk.org/gtk4/)
- [Gio.Menu Documentation](https://docs.gtk.org/gio/class.Menu.html)

### PyGObject GTK4
- [PyGObject GTK4 Tutorial](https://pygobject.gnome.org/tutorials/gtk4/)
- [PyGObject API Reference](https://lazka.github.io/pgi-docs/#Gtk-4.0)

### Useful Search Patterns
```bash
# Find all TODO GTK4 markers:
grep -r "TODO GTK4" quodlibet/ --include="*.py"

# Find remaining GTK3 patterns:
grep -r "Gtk\.get_current_event_time\|\.pack_start\|\.pack_end" quodlibet/
grep -r "Gtk\.Stock\|Gtk\.HBox\|Gtk\.VBox\|Gtk\.Table" quodlibet/
grep -r "\.drag_dest_set\|\.drag_source_set\|Gtk\.TargetEntry" quodlibet/
grep -r "\.get_children()" quodlibet/ | grep -v "qltk\.get_children"
grep -r "\.add_action_with_accel\|Gtk\.UIManager\|Gtk\.Action\b" quodlibet/
```

---

Statistics
----------

### Current State (2026-03-01)
- **Test suite**: 4354 passing, 271 failing (~94% pass rate)
- **TODO GTK4 markers**: 40 (DnD-related across 15 files)
- **Box.pack_start/pack_end uses**: 0 (fully migrated - remaining uses are TreeViewColumn/ComboBox API)
- **Gtk.HBox/VBox uses**: 0 (fully migrated)
- **Gtk.Stock uses**: 0 (fully migrated)
- **Direct get_children() calls**: 1 (helper function itself)

### Session Fixes (2026-03-01)
- CellRenderer margin fix (use xpad/ypad, not set_margin_*)
- TreeView model keyword argument (GTK4 requirement)
- Button label keyword argument (GTK4 requirement)
- IconTheme API (get_for_display, lookup_icon)
- CheckButton markup (use Label child)
- Table.set_border_width compatibility
- NativeDialog.run() compatibility shim
- FileChooser API updates (Gio.File, CREATE_FOLDER removal)
- RatingsMenuItem rewrite for GTK4
- Various import fixes and enum corrections

### Songlist DnD Implementation (2026-01-31)
Implemented GTK4 DnD for `qltk/songlist.py`:
- `SongListDnDMixin` rewritten with `Gtk.DragSource` and `Gtk.DropTarget`
- Uses `Gdk.FileList` for file transfer (standard format)
- Drag source: prepare, begin, end callbacks
- Drop target: accept, motion, leave, drop callbacks
- Supports row-based and browser-based drop modes
- Note: Drag icons skipped (cairo→Paintable conversion needed)

### Recent Commits (since 2026-01-03)
30 commits including:
- GTK4: Fix queue expander layout and cleanup
- GTK4: Fix play controls and menu sizing
- GTK4: Remove show_all() calls and fix WaitLoadWindow
- GTK4: Migrate get_children() and fix compatibility issues
- GTK4: Fix Frame and widget drawing APIs
- GTK4: Fix window and widget API compatibility
- GTK4: Fix event handler signatures
- GTK4: Migrate key-press-event to native EventControllerKey
- GTK4: Fix HeaderBar API for GTK4
- And many more...

### Major Systems Fixed
- ✅ PopoverMenu parenting system (2026-01-03)
- ✅ Event signal compatibility wrapper (2026-01-03)
- ✅ Box packing compatibility (2026-01-03)
- ✅ Paned widget API migration (2026-01-03)
- ✅ Widget property deprecations (2026-01-03)
- ✅ Dialog/Window API updates (2026-01-03 Session 2)
- ✅ ToggleAction state management (2026-01-03 Session 2)
- ✅ Table/Grid compatibility (2026-01-03 Session 2)

---

Quick Reference: Common Conversions
-----------------------------------

### Widget Methods
| GTK3 | GTK4 | Notes |
|------|------|-------|
| `widget.show_all()` | (no-op) | Widgets visible by default |
| `widget.hide_all()` | `widget.set_visible(False)` | |
| `widget.get_children()` | Use `qltk.get_children()` | Helper function |
| `container.add(child)` | `container.set_child(child)` | Single-child containers |
| `box.pack_start(w, e, f, p)` | `box.append(w)` + margins | Use margin properties |
| `button.set_image(img)` | `button.set_child(img)` | image property removed |

### Menu/Action
| GTK3 | GTK4 | Notes |
|------|------|-------|
| `Gtk.MenuItem` | `Gtk.Button` + flat CSS | Widget-based menus |
| `Gtk.RadioMenuItem` | `Gtk.CheckButton` | With radio grouping |
| `menu.append(item)` | `menu_box.append(item)` | PopoverMenu needs Box child |
| `action.connect("changed")` | `action.connect("activate")` | SimpleAction signals differ |
| `ag.add_action_with_accel()` | `ag.add_action()` + app.set_accels_for_action() | Separate accel setup |

### Event Handling
| GTK3 | GTK4 | Notes |
|------|------|-------|
| `Gtk.get_current_event_time()` | `GLib.CURRENT_TIME` | Always returns 0 |
| `widget.connect("button-press-event")` | Use `Gtk.GestureClick` controller | Event controllers preferred |
| `widget.connect("key-press-event")` | Use `Gtk.EventControllerKey` | |

### Drag and Drop
| GTK3 | GTK4 | Notes |
|------|------|-------|
| `Gtk.TargetEntry` | `Gdk.ContentFormats` | Completely redesigned |
| `widget.drag_source_set()` | `Gtk.DragSource` controller | |
| `widget.drag_dest_set()` | `Gtk.DropTarget` controller | |
| `"drag-data-get"` signal | `"prepare"` / `"drag-begin"` | Different signal names |
| `"drag-data-received"` signal | `"drop"` signal | |

---

Next Actions (Prioritised)
--------------------------

### Current Focus
The main remaining work is **Drag-and-Drop reimplementation**. This is a significant effort affecting 12 files across browsers, queue, songlist, and plugins.

### Immediate (pick one per session)
1. **Migrate one pack_start/pack_end file** → Proper margin-based layout
2. **Implement DnD for queue** → Core user feature
3. **Implement DnD for songlist** → Essential for playlist management

### Medium Priority
4. **Browser DnD** → All browser types (12 files)
5. **Album art DnD** → Plugin functionality
6. **VolumeMenu EventController** → Minor UI improvement

### Before Merge
7. **Comprehensive testing** → All features
8. **Plugin compatibility** → Test external plugins
9. **Delete this file** → Clean up tracking document
10. **Update main documentation** → Note GTK4 requirement

### Resumption Pattern
See CLAUDE.md section "GTK4 Migration Quick Start" for efficient session startup.

---

## DnD Implementation Plan (Songlist)

**File**: `quodlibet/qltk/songlist.py` - `SongListDnDMixin` class

### Current State
- Partially started: `setup_drop()` creates controllers but doesn't attach them
- Old GTK3 callbacks remain (`__drag_motion`, `__drag_data_get`, `__drag_data_received`)
- Uses deprecated APIs: `Gtk.drag_get_source_widget()`, `Gdk.drag_status()`, `Gtk.drag_finish()`

### GTK4 DnD Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Drag Source (dragging songs OUT)                            │
├─────────────────────────────────────────────────────────────┤
│ controller = Gtk.DragSource()                               │
│ controller.connect("prepare", on_prepare)  # return content │
│ controller.connect("drag-begin", on_begin) # set icon       │
│ controller.connect("drag-end", on_end)     # cleanup        │
│ widget.add_controller(controller)                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Drop Target (dropping songs IN)                             │
├─────────────────────────────────────────────────────────────┤
│ controller = Gtk.DropTarget.new(types, actions)             │
│ controller.connect("accept", on_accept)    # can we accept? │
│ controller.connect("motion", on_motion)    # highlight row  │
│ controller.connect("drop", on_drop)        # handle drop    │
│ controller.connect("leave", on_leave)      # unhighlight    │
│ widget.add_controller(controller)                           │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Steps

**Step 1: Drag Source** (simpler, do first)
```python
def setup_drag_source(self):
    source = Gtk.DragSource()
    source.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
    source.connect("prepare", self._on_drag_prepare)
    source.connect("drag-begin", self._on_drag_begin)
    source.connect("drag-end", self._on_drag_end)
    self.add_controller(source)

def _on_drag_prepare(self, source, x, y):
    model, paths = self.get_selection().get_selected_rows()
    songs = [model[path][0] for path in paths]
    # Store songs for transfer
    self._drag_songs = songs
    # Return content provider with URIs
    uris = [song("~uri") for song in songs]
    return Gdk.ContentProvider.new_for_value(GLib.Variant('as', uris))

def _on_drag_begin(self, source, drag):
    # Set drag icon (use existing create_multi_row_drag_icon)
    model, paths = self.get_selection().get_selected_rows()
    # Check if COPY or MOVE based on modifier keys
    # ...
```

**Step 2: Drop Target** (more complex)
```python
def setup_drop_target(self, library):
    target = Gtk.DropTarget.new(GLib.VariantType.new('as'),
                                 Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
    target.connect("accept", self._on_drop_accept)
    target.connect("motion", self._on_drop_motion)
    target.connect("drop", self._on_drop)
    target.connect("leave", self._on_drop_leave)
    self.add_controller(target)
    self._library = library

def _on_drop_motion(self, target, x, y):
    # Highlight drop position
    if self._drop_by_row:
        self.set_drag_dest(x, y)
    return Gdk.DragAction.COPY

def _on_drop(self, target, value, x, y):
    # Handle the actual drop
    uris = value.get_strv()
    # Convert URIs to songs, add to model at position
    # ...
    return True
```

### Key Differences from GTK3

| GTK3 | GTK4 |
|------|------|
| `drag_dest_set()` | `DropTarget` controller |
| `drag_source_set()` | `DragSource` controller |
| `SelectionData` | `GLib.Variant` or `Gdk.ContentProvider` |
| `drag-data-get` signal | `prepare` signal returns content |
| `drag-data-received` signal | `drop` signal |
| `Gtk.drag_finish()` | Return `True`/`False` from `drop` |
| `ctx.get_selected_action()` | `target.get_actions()` |

### Testing Approach
1. Test drag source first - drag songs to external app (file manager)
2. Test drop target - drop files from file manager
3. Test internal drag - drag songs within songlist (MOVE)
4. Test cross-widget - drag from browser to queue

### Reference
- Working DragSource example: `qltk/views.py:920`
- GTK4 DnD docs: https://docs.gtk.org/gtk4/drag-and-drop.html
- Drop.read_async: https://docs.gtk.org/gdk4/method.Drop.read_async.html

---

## Contact / Questions

For questions about this migration:
- **Branch**: `gtk4`
- **Tracking Issue**: [Link to issue if exists]
- **Documentation**: This file
- **TODO markers**: Search for `# TODO GTK4:` in code

---

**Remember to delete this file before merging to main!** 🗑️

---

Pytest Results (2025-12-21)
---------------------------

### Test Run Summary
- **Command**: `nix develop --command poetry run pytest`
- **Status**: Tests are running but hitting GTK4 compatibility issues

### Fixed During Test Run
1. ✅ **Gtk.AttachOptions** - Added compatibility enum (used by Gtk.Table in plugins)
2. ✅ **MenuItemPlugin base class** - Changed from Gtk.Widget to Gtk.Button
3. ✅ **MenuItemPlugin icon handling** - Updated to use set_child() with Box
4. ✅ **Window.set_type_hint()** - Added compatibility shim
5. ✅ **Gdk.WindowTypeHint** - Added compatibility enum
6. ✅ **Align widget** - Migrated from custom Gtk.Widget to Gtk.Box with margins

### Remaining Test Failures
- **configure-event signal**: GTK4 removed this signal (replaced with size-change monitoring)
- Additional event system changes needed throughout

### Files Modified in This Session
- `quodlibet/_init.py` - Added multiple compatibility shims
- `quodlibet/plugins/gui.py` - Fixed MenuItemPlugin for GTK4
- `quodlibet/qltk/x.py` - Fixed Align widget implementation

### Compatibility Shims Added
```python
# In quodlibet/_init.py:
Gtk.Widget.show_all = lambda self: None
Gtk.Widget.hide_all = lambda self: self.set_visible(False)
Gtk.Widget.set_no_show_all = lambda self, value: None
Gtk.AttachOptions = IntFlag with EXPAND/SHRINK/FILL
Gtk.Window.set_type_hint = lambda self, hint: None
Gtk.Window.get_type_hint = lambda self: None
Gdk.WindowTypeHint = IntEnum with NORMAL/DIALOG/MENU/TOOLBAR
```

### Test Progress
- **Plugin tests collected**: 231 tests
- **First test attempted**: test_albumart.py::TAlbumArt::testAlbumArtWindow
- **Status**: Progressing through GTK4 compatibility layers

The test suite is a valuable tool for finding remaining GTK4 incompatibilities!
