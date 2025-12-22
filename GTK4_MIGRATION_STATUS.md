GTK4 Migration Status
=====================

**Branch**: `gtk4`
**Last Updated**: 2025-12-21
**Status**: 🟡 In Progress - Application starts but has runtime issues

> ⚠️ **Note**: This file tracks the GTK4 migration progress and should be **deleted** once the migration is complete and merged to main.

---

Quick Summary
-------------

The GTK4 migration is approximately **60% complete**. Core infrastructure changes are done, but several subsystems need work:
- ✅ Event handling and time management
- ✅ Menu system basics (widgets)
- ✅ Container widget API updates
- ⚠️ Menu system (actions/signals incomplete)
- ❌ Drag-and-Drop (disabled, needs rewrite)
- ❌ UIManager migration
- ⚠️ Box packing (partially done)

**Current blocking issue**: RadioAction "changed" signal not implemented

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

## Known Issues & TODO Items ⚠️

### Critical (Blocking Application)

#### 1. RadioAction Signal Implementation
**File**: `quodlibet/qltk/x.py:490`
**Error**: `RadioAction: unknown signal name: changed`

**Problem**: `Gio.SimpleAction` doesn't emit a "changed" signal. GTK3's `Gtk.RadioAction` did.

**Solutions**:
- **Option A** (Quick): Implement signal manually using GObject.signal_new()
- **Option B** (Better): Use stateful SimpleAction with state change handling
- **Option C** (Best): Migrate to full Gio.Menu system

**Code location**:
```python
# quodlibet/qltk/quodlibetwindow.py:1095
act.connect("changed", self.__change_view)  # ← This fails
```

**Implementation guide**:
```python
# Option B: Stateful action
class RadioAction(Gio.SimpleAction):
    def __init__(self, *args, **kwargs):
        value = kwargs.pop("value", 0)
        kwargs["state"] = GLib.Variant.new_int32(value)
        kwargs["parameter_type"] = GLib.VariantType.new("i")
        super().__init__(*args, **kwargs)

    # Connect to "activate" or "change-state" instead of "changed"
```

---

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

### Files Modified
- **Direct changes**: 15 files
- **DnD commented**: 12 files
- **Gtk.get_current_event_time**: 27 files
- **Total affected**: ~50+ files

### Lines Changed
- **Additions**: ~295 lines
- **Deletions**: ~203 lines
- **Net**: +92 lines
- **Comments added**: ~150 lines (TODO markers and explanations)

### TODO Markers Added
- **Total**: 30+
- **Critical**: 5
- **High Priority**: 10
- **Medium/Low**: 15+

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

### Immediate (To get application running)
1. **Fix RadioAction signal** → Implement "activate" or stateful action
2. **Test main window display** → Should now show
3. **Fix any remaining startup crashes** → Iterate on errors

### Week 1
4. **Restore keyboard accelerators** → Add to application
5. **Fix get_children() calls** → Replace with helper
6. **Complete Box packing migration** → Systematic file-by-file

### Week 2-3
7. **Implement GTK4 DnD for queue** → Core functionality
8. **Implement GTK4 DnD for playlists** → User-facing feature
9. **Test and fix browser DnD** → All browser types

### Month 1
10. **UIManager → Gio.Menu migration** → Menu bar
11. **Fix submenus** → Proper Gio.Menu implementation
12. **Deprecate container migrations** → HBox/VBox/Table/Alignment

### Before Merge
13. **Comprehensive testing** → All features
14. **Plugin compatibility** → Test external plugins
15. **Delete this file** → Clean up tracking document
16. **Update main documentation** → Note GTK4 requirement

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
