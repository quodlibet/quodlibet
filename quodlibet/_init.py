# Copyright 2012 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import warnings
import logging

from senf import fsn2text

from quodlibet.const import MinVersions
from quodlibet import config
from quodlibet.util import is_osx, is_windows, i18n
from quodlibet.util.dprint import print_e, PrintHandler, print_d
from quodlibet.util.urllib import install_urllib2_ca_file

from ._main import get_base_dir, is_release, get_cache_dir


_cli_initialized = False
_initialized = False


def _init_gtk_debug(no_excepthook):
    from quodlibet.errorreport import enable_errorhook

    enable_errorhook(not no_excepthook)


def is_init():
    """Returns if init() was called"""

    global _initialized

    return _initialized


def init(no_translations=False, no_excepthook=False, config_file=None):
    """This needs to be called before any API can be used.
    Might raise in case of an error.

    Pass no_translations=True to disable translations (used by tests)
    """

    global _initialized

    if _initialized:
        return

    init_cli(no_translations=no_translations, config_file=config_file)
    _init_gtk()
    _init_gtk_debug(no_excepthook=no_excepthook)
    _init_gst()
    _init_dbus()

    _initialized = True


def _init_gettext(no_translations=False):
    """Call before using gettext helpers"""

    if no_translations:
        language = "C"
    else:
        language = config.gettext("settings", "language")
        if language:
            print_d(f"Using language in QL settings: {language!r}")
        else:
            language = None

    i18n.init(language)

    # Use the locale dir in ../build/share/locale if there is one
    localedir = os.path.join(
        os.path.dirname(get_base_dir()), "build", "share", "locale"
    )
    if os.path.isdir(localedir):
        print_d(f"Using local locale dir {localedir}")
    else:
        localedir = None

    i18n.register_translation("quodlibet", localedir)
    debug_text = os.environ.get("QUODLIBET_TEST_TRANS")
    if debug_text is not None:
        i18n.set_debug_text(fsn2text(debug_text))


def _init_python():
    MinVersions.PYTHON3.check(sys.version_info)

    if is_osx():
        # We build our own openssl on OSX and need to make sure that
        # our own ca file is used in all cases as the non-system openssl
        # doesn't use the system certs
        install_urllib2_ca_file()

    if is_windows():
        # Not really needed on Windows as pygi-aio seems to work fine, but
        # wine doesn't have certs which we use for testing.
        install_urllib2_ca_file()

    if is_windows() and os.sep != "\\":
        # In the MSYS2 console MSYSTEM is set, which breaks os.sep/os.path.sep
        # If you hit this, do a "setup.py clean -all" to get rid of the
        # bytecode cache then start things with "MSYSTEM= ..."
        raise AssertionError("MSYSTEM is set ({!r})".format(os.environ.get("MSYSTEM")))

    logging.getLogger().addHandler(PrintHandler())


def _init_formats():
    from quodlibet.formats import init

    init()


def init_cli(no_translations=False, config_file=None):
    """This needs to be called before any API can be used.
    Might raise in case of an error.

    Like init() but for code not using Gtk etc.
    """

    global _cli_initialized

    if _cli_initialized:
        return

    _init_python()
    config.init_defaults()
    if config_file is not None:
        config.init(config_file)
    _init_gettext(no_translations)
    _init_formats()
    _init_g()

    _cli_initialized = True


def _init_dbus():
    """Setup dbus mainloop integration. Call before using dbus"""

    # To make GDBus fail early and we don't have to wait for a timeout
    if is_osx() or is_windows():
        os.environ["DBUS_SYSTEM_BUS_ADDRESS"] = "something-invalid"
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = "something-invalid"

    try:
        from dbus.mainloop.glib import DBusGMainLoop, threads_init
    except ImportError:
        try:
            import dbus.glib

            dbus.glib  # noqa
        except ImportError:
            return
    else:
        threads_init()
        DBusGMainLoop(set_as_default=True)


def _fix_gst_leaks():
    """gst_element_add_pad and gst_bin_add are wrongly annotated and lead
    to PyGObject refing the passed element.

    Work around by adding a wrapper that unrefs afterwards.
    Can be called multiple times.

    https://bugzilla.gnome.org/show_bug.cgi?id=741390
    https://bugzilla.gnome.org/show_bug.cgi?id=702960
    """

    from gi.repository import Gst

    assert Gst.is_initialized()

    def do_wrap(func):
        def wrap(self, obj):
            result = func(self, obj)
            obj.unref()
            return result

        return wrap

    parent = Gst.Bin()
    elm = Gst.Bin()
    parent.add(elm)
    if elm.__grefcount__ == 3:
        elm.unref()
        Gst.Bin.add = do_wrap(Gst.Bin.add)

    pad = Gst.Pad.new("foo", Gst.PadDirection.SRC)
    parent.add_pad(pad)
    if pad.__grefcount__ == 3:
        pad.unref()
        Gst.Element.add_pad = do_wrap(Gst.Element.add_pad)


def _init_g():
    """Call before using GdkPixbuf/GLib/Gio/GObject"""

    import gi

    gi.require_version("GLib", "2.0")
    gi.require_version("Gio", "2.0")
    gi.require_version("GObject", "2.0")
    gi.require_version("GdkPixbuf", "2.0")

    # Newer glib is noisy regarding deprecated signals/properties
    # even with stable releases.
    if is_release():
        warnings.filterwarnings(
            "ignore", ".* It will be removed in a future version.", Warning
        )

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["glib"] = None
    sys.modules["gobject"] = None


def _init_gtk():
    """Call before using Gtk/Gdk"""

    import gi

    if (
        config.getboolean("settings", "pangocairo_force_fontconfig")
        and "PANGOCAIRO_BACKEND" not in os.environ
    ):
        os.environ["PANGOCAIRO_BACKEND"] = "fontconfig"

    # disable for consistency and trigger events seem a bit flaky here
    if config.getboolean("settings", "scrollbar_always_visible"):
        os.environ["GTK_OVERLAY_SCROLLING"] = "0"

    try:
        # not sure if this is available under Windows
        gi.require_version("GdkX11", "4.0")
        from gi.repository import GdkX11

        GdkX11  # noqa
    except (ValueError, ImportError):
        pass

    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Pango", "1.0")
    gi.require_version("Soup", "3.0")
    gi.require_version("PangoCairo", "1.0")

    from gi.repository import Gtk
    from quodlibet.qltk import ThemeOverrider, gtk_version

    # PyGObject doesn't fail any more when init fails, so do it ourselves
    initialized = Gtk.init_check()
    if not initialized:
        raise SystemExit("Gtk.init failed")

    # GTK4 compatibility: Add show_all/hide_all/set_no_show_all as no-ops
    if not hasattr(Gtk.Widget, "show_all"):
        Gtk.Widget.show_all = lambda self: None
    if not hasattr(Gtk.Widget, "hide_all"):
        Gtk.Widget.hide_all = lambda self: self.set_visible(False)
    if not hasattr(Gtk.Widget, "set_no_show_all"):
        Gtk.Widget.set_no_show_all = lambda self, value: None
    if not hasattr(Gtk.Widget, "destroy"):
        # GTK4: Widgets no longer have destroy(), they're auto-destroyed
        Gtk.Widget.destroy = lambda self: None
    if not hasattr(Gtk.Widget, "get_toplevel"):
        Gtk.Widget.get_toplevel = lambda self: self.get_root() or self

    # GTK4: add_events removed - event system redesigned with controllers
    if not hasattr(Gtk.Widget, "add_events"):
        Gtk.Widget.add_events = lambda self, events: None

    # GTK4: Wrap GObject.connect to ignore removed event signals
    from gi.repository import GObject

    _orig_gobject_connect = GObject.Object.connect
    _removed_signals = {
        "button-press-event",
        "button-release-event",
        "motion-notify-event",
        "key-press-event",
        "key-release-event",
        "scroll-event",
        "enter-notify-event",
        "leave-notify-event",
        "focus-in-event",
        "focus-out-event",
        "configure-event",
        "delete-event",
        "destroy-event",
        "expose-event",
        "map-event",
        "unmap-event",
        "property-notify-event",
        "selection-clear-event",
        "visibility-notify-event",
        "window-state-event",
        "damage-event",
        "grab-broken-event",
        "event",
        "event-after",
    }

    def _connect_compat(self, signal_name, *args, **kwargs):
        # Silently ignore GTK3 event signals that don't exist in GTK4
        if signal_name in _removed_signals:
            print_d(f"Ignoring GTK3 signal connection: {signal_name}")
            return 0  # Return dummy handler ID
        try:
            return _orig_gobject_connect(self, signal_name, *args, **kwargs)
        except TypeError as e:
            # Catch "unknown signal name" errors for removed signals
            if "unknown signal name" in str(e):
                print_d(f"Ignoring unknown signal: {signal_name}")
                return 0
            raise

    GObject.Object.connect = _connect_compat

    # Also wrap connect_after
    _orig_gobject_connect_after = GObject.Object.connect_after

    def _connect_after_compat(self, signal_name, *args, **kwargs):
        # Silently ignore GTK3 event signals that don't exist in GTK4
        if signal_name in _removed_signals:
            print_d(f"Ignoring GTK3 signal connection (after): {signal_name}")
            return 0  # Return dummy handler ID
        try:
            return _orig_gobject_connect_after(self, signal_name, *args, **kwargs)
        except TypeError as e:
            # Catch "unknown signal name" errors for removed signals
            if "unknown signal name" in str(e):
                print_d(f"Ignoring unknown signal (after): {signal_name}")
                return 0
            raise

    GObject.Object.connect_after = _connect_after_compat

    # GTK4: Button.add() → Button.set_child()
    if not hasattr(Gtk.Button, "add"):
        Gtk.Button.add = lambda self, child: self.set_child(child)

    # GTK4: Window.add() → Window.set_child()
    if not hasattr(Gtk.Window, "add"):
        Gtk.Window.add = lambda self, child: self.set_child(child)

    # GTK4: Window.resize() removed - use set_default_size() as approximation
    if not hasattr(Gtk.Window, "resize"):
        Gtk.Window.resize = lambda self, width, height: self.set_default_size(
            width, height
        )

    # GTK4: Box.add() → Box.append() (or prepend depending on context, append is default)
    if not hasattr(Gtk.Box, "add"):
        Gtk.Box.add = lambda self, child: self.append(child)

    # GTK4: ComboBox.add() → ComboBox.set_child() for entry widget
    if not hasattr(Gtk.ComboBox, "add"):
        Gtk.ComboBox.add = lambda self, child: self.set_child(child)

    # GTK4: Wrap Box.prepend/append to ignore GTK3 pack_start/pack_end arguments
    _orig_box_prepend = Gtk.Box.prepend
    _orig_box_append = Gtk.Box.append

    def _box_prepend_compat(self, child, expand=None, fill=None, padding=None):
        # GTK4: prepend only takes child, ignore expand/fill/padding
        return _orig_box_prepend(self, child)

    def _box_append_compat(self, child, expand=None, fill=None, padding=None):
        # GTK4: append only takes child, ignore expand/fill/padding
        return _orig_box_append(self, child)

    Gtk.Box.prepend = _box_prepend_compat
    Gtk.Box.append = _box_append_compat

    # GTK4: Frame.add() → Frame.set_child()
    if not hasattr(Gtk.Frame, "add"):
        Gtk.Frame.add = lambda self, child: self.set_child(child)

    if not hasattr(Gtk.Window, "add_accel_group"):
        Gtk.Window.add_accel_group = lambda self, group: None

    # GTK4: accelerator_parse now returns (success, keyval, modifiers)
    _original_accelerator_parse = Gtk.accelerator_parse

    def _accelerator_parse_compat(accelerator):
        result = _original_accelerator_parse(accelerator)
        if len(result) == 3:
            # GTK4: returns (success, keyval, modifiers)
            success, keyval, modifiers = result
            return (keyval, modifiers) if success else (0, 0)
        return result  # GTK3: returns (keyval, modifiers)

    Gtk.accelerator_parse = _accelerator_parse_compat

    # GTK4 compatibility: Add Gtk.AttachOptions for Table compatibility
    # (Gtk.Table removed in GTK4, but plugins still use it)
    if not hasattr(Gtk, "AttachOptions"):
        from enum import IntFlag

        class AttachOptions(IntFlag):
            EXPAND = 1 << 0
            SHRINK = 1 << 1
            FILL = 1 << 2

        Gtk.AttachOptions = AttachOptions

    # GTK4: Window type property removed - wrap __init__ to filter it out
    _orig_window_init = Gtk.Window.__init__

    def _window_init_compat(self, *args, **kwargs):
        # Remove 'type' kwarg if present (GTK3 only, not supported in GTK4)
        kwargs.pop("type", None)
        return _orig_window_init(self, *args, **kwargs)

    Gtk.Window.__init__ = _window_init_compat

    # GTK4 compatibility: Window type hints removed
    if not hasattr(Gtk.Window, "set_type_hint"):
        Gtk.Window.set_type_hint = lambda self, hint: None
        Gtk.Window.get_type_hint = lambda self: None

    # GTK4 compatibility: Gdk.WindowTypeHint removed
    from gi.repository import Gdk, GLib

    # GTK4: GLib.CURRENT_TIME removed - use constant 0
    if not hasattr(GLib, "CURRENT_TIME"):
        GLib.CURRENT_TIME = 0

    # GTK4: EventMask removed - event system redesigned
    if not hasattr(Gdk, "EventMask"):
        from enum import IntFlag

        class EventMask(IntFlag):
            EXPOSURE_MASK = 1 << 1
            POINTER_MOTION_MASK = 1 << 2
            POINTER_MOTION_HINT_MASK = 1 << 3
            BUTTON_MOTION_MASK = 1 << 4
            BUTTON1_MOTION_MASK = 1 << 5
            BUTTON2_MOTION_MASK = 1 << 6
            BUTTON3_MOTION_MASK = 1 << 7
            BUTTON_PRESS_MASK = 1 << 8
            BUTTON_RELEASE_MASK = 1 << 9
            KEY_PRESS_MASK = 1 << 10
            KEY_RELEASE_MASK = 1 << 11
            ENTER_NOTIFY_MASK = 1 << 12
            LEAVE_NOTIFY_MASK = 1 << 13
            FOCUS_CHANGE_MASK = 1 << 14
            STRUCTURE_MASK = 1 << 15
            PROPERTY_CHANGE_MASK = 1 << 16
            VISIBILITY_NOTIFY_MASK = 1 << 17
            PROXIMITY_IN_MASK = 1 << 18
            PROXIMITY_OUT_MASK = 1 << 19
            SUBSTRUCTURE_MASK = 1 << 20
            SCROLL_MASK = 1 << 21
            TOUCH_MASK = 1 << 22
            SMOOTH_SCROLL_MASK = 1 << 23
            TOUCHPAD_GESTURE_MASK = 1 << 24
            TABLET_PAD_MASK = 1 << 25
            ALL_EVENTS_MASK = 0x3FFFFFE

        Gdk.EventMask = EventMask

    if not hasattr(Gdk, "WindowTypeHint"):
        from enum import IntEnum

        class WindowTypeHint(IntEnum):
            NORMAL = 0
            DIALOG = 1
            MENU = 2
            TOOLBAR = 3

        Gdk.WindowTypeHint = WindowTypeHint

    # GTK4 compatibility: Gdk.WindowState removed
    if not hasattr(Gdk, "WindowState"):
        from enum import IntFlag

        class WindowState(IntFlag):
            """GTK4 compatibility shim for Gdk.WindowState.

            In GTK4, window states are handled via Gdk.ToplevelState.
            This provides a compatible enum for GTK3 code.
            """

            WITHDRAWN = 1 << 0
            ICONIFIED = 1 << 1
            MAXIMIZED = 1 << 2
            STICKY = 1 << 3
            FULLSCREEN = 1 << 4
            ABOVE = 1 << 5
            BELOW = 1 << 6
            FOCUSED = 1 << 7
            TILED = 1 << 8

        Gdk.WindowState = WindowState

    # GTK4 compatibility: Gtk.WindowType removed (used for Window constructor)
    if not hasattr(Gtk, "WindowType"):
        from enum import IntEnum

        class WindowType(IntEnum):
            TOPLEVEL = 0
            POPUP = 1

        Gtk.WindowType = WindowType

    # GTK4: UIManager removed - stub for now, needs proper Gio.Menu migration
    if not hasattr(Gtk, "UIManager"):
        from gi.repository import GObject

        class UIManager(GObject.Object):
            def __init__(self):
                GObject.Object.__init__(self)
                self._action_groups = []
                self._ui_string = ""
                self._widgets = {}

            def insert_action_group(self, group, pos):
                self._action_groups.append(group)

            def add_ui_from_string(self, ui_string):
                self._ui_string = ui_string

            def get_widget(self, path):
                if path not in self._widgets:
                    widget = Gtk.Box()
                    widget.get_children = lambda: []
                    self._widgets[path] = widget
                return self._widgets[path]

            def get_accel_group(self):
                # Return dummy accel group
                if not hasattr(self, "_accel_group"):

                    class DummyAccelGroup(GObject.Object):
                        def connect(self, *args, **kwargs):
                            pass

                    self._accel_group = DummyAccelGroup()
                return self._accel_group

        Gtk.UIManager = UIManager

    # GTK4: AccelGroup removed - create dummy for compatibility
    class AccelGroup(GObject.Object):
        """Dummy AccelGroup for GTK4 compatibility.

        In GTK4, AccelGroup was removed in favor of application-wide
        keyboard shortcuts via GtkApplication. This dummy allows
        code to continue creating AccelGroups without crashing.
        """

        def __init__(self):
            super().__init__()

        def connect(self, *args, **kwargs):
            """Dummy connect - does nothing in GTK4"""
            pass

        def disconnect(self, *args, **kwargs):
            """Dummy disconnect - does nothing in GTK4"""
            pass

    Gtk.AccelGroup = AccelGroup

    # GTK4: ImageMenuItem removed - dummy for isinstance checks
    class ImageMenuItem:
        pass

    Gtk.ImageMenuItem = ImageMenuItem

    # GTK4: Alignment widget removed - use Box with alignment properties
    class Alignment(Gtk.Box):
        """Dummy Alignment for GTK4 compatibility.

        In GTK4, Gtk.Alignment was removed. Use widget alignment
        properties (halign, valign, margins) directly on widgets.
        This provides a simple Box container as a replacement.
        """

        def __init__(self, xalign=0.5, yalign=0.5, xscale=1.0, yscale=1.0):
            super().__init__()
            # Store these for compatibility but don't use them
            self._xalign = xalign
            self._yalign = yalign
            self._xscale = xscale
            self._yscale = yscale

        def set(self, xalign, yalign, xscale, yscale):
            """GTK4: set() method for compatibility"""
            self._xalign = xalign
            self._yalign = yalign
            self._xscale = xscale
            self._yscale = yscale

        def set_padding(self, top, bottom, left, right):
            """GTK4: Use margins instead of padding"""
            self.set_margin_top(top)
            self.set_margin_bottom(bottom)
            self.set_margin_start(left)
            self.set_margin_end(right)

        def add(self, widget):
            """Add a child widget"""
            self.append(widget)

    Gtk.Alignment = Alignment

    # GTK4: CheckMenuItem removed
    Gtk.CheckMenuItem = Gtk.CheckButton

    # GTK4: Arrow removed - create factory class that returns Image
    if not hasattr(Gtk, "Arrow"):

        class ArrowFactory:
            @staticmethod
            def new(arrow_type, shadow_type):
                # Map arrow types to icon names
                icon_map = {
                    Gtk.ArrowType.UP: "pan-up-symbolic",
                    Gtk.ArrowType.DOWN: "pan-down-symbolic",
                    Gtk.ArrowType.LEFT: "pan-start-symbolic",
                    Gtk.ArrowType.RIGHT: "pan-end-symbolic",
                }
                icon_name = icon_map.get(arrow_type, "pan-down-symbolic")
                return Gtk.Image.new_from_icon_name(icon_name)

            def __call__(self, arrow_type, shadow_type):
                return self.new(arrow_type, shadow_type)

        Gtk.Arrow = ArrowFactory()

    # GTK4: ArrowType enum - add if missing
    if not hasattr(Gtk, "ArrowType"):
        from enum import IntEnum

        class ArrowType(IntEnum):
            UP = 0
            DOWN = 1
            LEFT = 2
            RIGHT = 3

        Gtk.ArrowType = ArrowType

    # GTK4: ShadowType enum - add if missing (used for frames)
    if not hasattr(Gtk, "ShadowType"):
        from enum import IntEnum

        class ShadowType(IntEnum):
            NONE = 0
            IN = 1
            OUT = 2
            ETCHED_IN = 3
            ETCHED_OUT = 4

        Gtk.ShadowType = ShadowType

    # GTK4: MenuItem removed - use Button with flat style
    class MenuItem(Gtk.Button):
        def __init__(self, label=None, use_underline=False):
            super().__init__(label=label, use_underline=use_underline)
            self.add_css_class("flat")

        def set_submenu(self, menu):
            # Store submenu reference but don't show it (needs proper implementation)
            self._submenu = menu

    Gtk.MenuItem = MenuItem

    # GTK4: AccelMap removed
    class AccelMap:
        @staticmethod
        def load(filename):
            pass

        @staticmethod
        def save(filename):
            pass

    Gtk.AccelMap = AccelMap

    # GTK4: IconSize enum changed
    if not hasattr(Gtk.IconSize, "LARGE_TOOLBAR"):
        Gtk.IconSize.LARGE_TOOLBAR = Gtk.IconSize.LARGE
        Gtk.IconSize.SMALL_TOOLBAR = Gtk.IconSize.NORMAL
        Gtk.IconSize.BUTTON = Gtk.IconSize.NORMAL
        Gtk.IconSize.MENU = Gtk.IconSize.NORMAL

    # GTK4: CSS class constants removed - add them back
    if not hasattr(Gtk, "STYLE_CLASS_LINKED"):
        Gtk.STYLE_CLASS_LINKED = "linked"

    # GTK4: Container removed - all widgets are now containers
    Gtk.Container = Gtk.Widget

    # GTK4: set_border_width removed - use margins instead
    if not hasattr(Gtk.Frame, "set_border_width"):

        def _set_border_width(self, width):
            # In GTK4, use margins instead of border_width
            self.set_margin_start(width)
            self.set_margin_end(width)
            self.set_margin_top(width)
            self.set_margin_bottom(width)

        Gtk.Frame.set_border_width = _set_border_width
        Gtk.Window.set_border_width = _set_border_width
        Gtk.Paned.set_border_width = _set_border_width

    # GTK4: PopoverMenu.append() compatibility
    _orig_popover_menu_init = Gtk.PopoverMenu.__init__

    def _popover_menu_init_compat(self, *args, **kwargs):
        _orig_popover_menu_init(self, *args, **kwargs)
        if not hasattr(self, "_menu_box"):
            self._menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            # Don't set_child during init - wait until widget is in hierarchy
            try:
                if self.get_root() is not None:
                    self.set_child(self._menu_box)
            except:
                pass  # Set it later when appending

    def _popover_menu_append_compat(self, widget):
        if not hasattr(self, "_menu_box"):
            self._menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # Always append to the box, but delay setting it as child until we're in a window
        self._menu_box.append(widget)
        # Ensure box is set as child, but only if we're in a window
        if self.get_child() is None:
            # Only set_child if we're already in a widget hierarchy to avoid realize() issues
            if self.get_parent() is not None and self.get_root() is not None:
                self.set_child(self._menu_box)

    Gtk.PopoverMenu.__init__ = _popover_menu_init_compat
    Gtk.PopoverMenu.append = _popover_menu_append_compat

    # GTK4: Wrap popup() to prevent crashes when not properly parented
    _orig_popover_popup = Gtk.PopoverMenu.popup

    def _popover_menu_popup_compat(self):
        # Silently fail if not properly set up to avoid crashes
        if self.get_parent() is None:
            print_d("PopoverMenu.popup() called without parent, ignoring")
            return
        if self.get_root() is None:
            print_d("PopoverMenu.popup() called before parented to window, ignoring")
            return
        # Ensure child is set if we have a menu box
        if hasattr(self, "_menu_box") and self.get_child() is None:
            self.set_child(self._menu_box)
        return _orig_popover_popup(self)

    Gtk.PopoverMenu.popup = _popover_menu_popup_compat

    # GTK4: Table removed - wrap Grid to provide Table API
    class Table(Gtk.Grid):
        def __init__(
            self, rows=1, columns=1, homogeneous=False, n_rows=None, n_columns=None
        ):
            super().__init__()
            self._rows = n_rows if n_rows is not None else rows
            self._columns = n_columns if n_columns is not None else columns
            self.set_row_homogeneous(homogeneous)
            self.set_column_homogeneous(homogeneous)

        @property
        def props(self):
            class Props:
                def __init__(self, parent):
                    self._parent = parent

                @property
                def n_rows(self):
                    return self._parent._rows

                @property
                def n_columns(self):
                    return self._parent._columns

            if not hasattr(self, "_props"):
                self._props = Props(self)
            return self._props

        def attach(
            self,
            child,
            left,
            right,
            top,
            bottom,
            xoptions=0,
            yoptions=0,
            xpadding=0,
            ypadding=0,
        ):
            child.set_margin_start(xpadding)
            child.set_margin_end(xpadding)
            child.set_margin_top(ypadding)
            child.set_margin_bottom(ypadding)

            width = right - left
            height = bottom - top

            super().attach(child, left, top, width, height)

        def set_row_spacings(self, spacing):
            self.set_row_spacing(spacing)

        def set_col_spacings(self, spacing):
            self.set_column_spacing(spacing)

    Gtk.Table = Table

    # TODO: include our own icon theme directory
    # theme = Gtk.IconTheme.get_default()
    # theme_search_path = get_image_dir()
    # assert os.path.exists(theme_search_path)
    # theme.append_search_path(theme_search_path)

    # Force menu/button image related settings. We might show too many atm
    # but this makes sure we don't miss cases where we forgot to force them
    # per widget.
    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

    # some day... but not now
    warnings.filterwarnings("ignore", ".*Stock items are deprecated.*", Warning)
    warnings.filterwarnings("ignore", ".*:use-stock.*", Warning)
    warnings.filterwarnings(
        "ignore", r".*The property GtkAlignment:[^\s]+ is deprecated.*", Warning
    )

    settings = Gtk.Settings.get_default()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # settings.set_property("gtk-button-images", True)
        # settings.set_property("gtk-menu-images", True)
    if hasattr(settings.props, "gtk_primary_button_warps_slider"):
        # https://bugzilla.gnome.org/show_bug.cgi?id=737843
        settings.set_property("gtk-primary-button-warps-slider", True)

    # Make sure PyGObject includes support for foreign cairo structs
    try:
        gi.require_foreign("cairo")
    except ImportError:
        print_e("PyGObject is missing cairo support")
        sys.exit(1)

    css_override = ThemeOverrider()

    if sys.platform == "darwin":
        # fix duplicated shadows for popups with Gtk+3.14
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            GtkWindow {
                box-shadow: none;
            }
            .tooltip {
                border-radius: 0;
                padding: 0;
            }
            .tooltip.background {
                background-clip: border-box;
            }
            """)
        css_override.register_provider("", style_provider)

    if gtk_version[:2] >= (3, 20):
        # https://bugzilla.gnome.org/show_bug.cgi?id=761435
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            spinbutton, button {
                min-height: 22px;
            }

            .view button {
                min-height: 24px;
            }

            entry {
                min-height: 28px;
            }

            entry.cell {
                min-height: 0;
            }
        """)
        css_override.register_provider("Adwaita", style_provider)
        css_override.register_provider("HighContrast", style_provider)

        # https://github.com/quodlibet/quodlibet/issues/2541
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            treeview.view.separator {
                min-height: 2px;
                color: @borders;
            }
        """)
        css_override.register_provider("Ambiance", style_provider)
        css_override.register_provider("Radiance", style_provider)
        # https://github.com/quodlibet/quodlibet/issues/2677
        css_override.register_provider("Clearlooks-Phenix", style_provider)
        # https://github.com/quodlibet/quodlibet/issues/2997
        css_override.register_provider("Breeze", style_provider)

    if gtk_version[:2] >= (3, 18):
        # Hack to get some grab handle like thing for panes
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(b"""
            GtkPaned.vertical, paned.vertical >separator {
                -gtk-icon-source: -gtk-icontheme("view-more-symbolic");
                -gtk-icon-transform: rotate(90deg) scaleX(0.1) scaleY(3);
            }

            GtkPaned.horizontal, paned.horizontal >separator {
                -gtk-icon-source: -gtk-icontheme("view-more-symbolic");
                -gtk-icon-transform: rotate(0deg) scaleX(0.1) scaleY(3);
            }
        """)
        css_override.register_provider("", style_provider)

    # https://bugzilla.gnome.org/show_bug.cgi?id=708676
    warnings.filterwarnings("ignore", ".*g_value_get_int.*", Warning)

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gtk"] = None
    sys.modules["gpod"] = None
    sys.modules["gnome"] = None

    from quodlibet.qltk import pygobject_version, gtk_version

    MinVersions.GTK.check(gtk_version)
    MinVersions.PYGOBJECT.check(pygobject_version)


def _init_gst():
    """Call once before importing GStreamer"""

    arch_key = "64" if sys.maxsize > 2**32 else "32"
    registry_name = f"gst-registry-{sys.platform}-{arch_key}.bin"
    os.environ["GST_REGISTRY"] = os.path.join(get_cache_dir(), registry_name)

    assert "gi.repository.Gst" not in sys.modules

    import gi

    # We don't want python-gst, it changes API..
    assert "gi.overrides.Gst" not in sys.modules
    sys.modules["gi.overrides.Gst"] = None

    # blacklist some modules, simply loading can cause segfaults
    sys.modules["gst"] = None

    # We don't depend on Gst overrides, so make sure it's initialized.
    try:
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
    except (ValueError, ImportError):
        return

    if Gst.is_initialized():
        return

    from gi.repository import GLib

    try:
        ok, sys.argv[:] = Gst.init_check(sys.argv)
    except GLib.GError:
        print_e("Failed to initialize GStreamer")
        # Uninited Gst segfaults: make sure no one can use it
        sys.modules["gi.repository.Gst"] = None
    else:
        # monkey patching ahead
        _fix_gst_leaks()
