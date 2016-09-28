# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012 Christoph Reiter
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import signal

import gi
gi.require_version("Gtk", "3.0")

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib

from quodlibet.util import gdecode, print_d, print_w


def get_primary_accel_mod():
    """Returns the primary Gdk.ModifierType modifier.

    cmd on osx, ctrl everywhere else.
    """

    return Gtk.accelerator_parse("<Primary>")[1]


def redraw_all_toplevels():
    """A hack to trigger redraws for all windows and widgets."""

    for widget in Gtk.Window.list_toplevels():
        if not widget.get_realized():
            continue
        if widget.is_active():
            widget.queue_draw()
            continue
        sensitive = widget.get_sensitive()
        widget.set_sensitive(not sensitive)
        widget.set_sensitive(sensitive)


def selection_set_songs(selection_data, songs):
    """Stores filenames of the passed songs in a Gtk.SelectionData"""

    filenames = []
    for filename in (song["~filename"] for song in songs):
        if isinstance(filename, unicode):
            # win32
            filename = filename.encode("utf-8")
        filenames.append(filename)

    type_ = Gdk.atom_intern("text/x-quodlibet-songs", True)
    selection_data.set(type_, 8, "\x00".join(filenames))


def selection_get_filenames(selection_data):
    """Extracts the filenames of songs set with selection_set_songs()
    from a Gtk.SelectionData.
    """

    data_type = selection_data.get_data_type()
    assert data_type.name() == "text/x-quodlibet-songs"

    items = selection_data.get_data().split("\x00")
    if sys.platform == "win32":
        return [item.decode("utf-8") for item in items]
    else:
        return items


def get_top_parent(widget):
    """Return the ultimate parent of a widget; the assumption that code
    using this makes is that it will be a Gtk.Window, i.e. the widget
    is fully packed when this is called."""

    parent = widget and widget.get_toplevel()
    if parent and parent.is_toplevel():
        return parent
    else:
        return None


def get_menu_item_top_parent(widget):
    """Returns the toplevel for a menu item or None if the menu
    and none of its parents isn't attached to a widget
    """

    while isinstance(widget, Gtk.MenuItem):
        menu = widget.get_parent()
        if not menu:
            return
        widget = menu.get_attach_widget()
    return get_top_parent(widget)


def find_widgets(container, type_):
    """Given a container, find all children that are a subclass of type_
    (including itself)
    """

    assert isinstance(container, Gtk.Container)

    found = []

    if isinstance(container, type_):
        found.append(container)

    for child in container.get_children():
        if isinstance(child, Gtk.Container):
            found.extend(find_widgets(child, type_))

    return found


def menu_popup(menu, shell, item, func, *args):
    """Wrapper to fix API break:
    https://git.gnome.org/browse/gtk+/commit/?id=8463d0ee62b4b22fa
    """

    if func is not None:
        def wrap_pos_func(menu, *args):
            return func(menu, args[-1])
    else:
        wrap_pos_func = None

    return menu.popup(shell, item, wrap_pos_func, *args)


def _popup_menu_at_widget(menu, widget, button, time, under):

    def pos_func(menu, data, widget=widget):
        screen = widget.get_screen()
        ref = get_top_parent(widget)
        menu.set_screen(screen)
        x, y = widget.translate_coordinates(ref, 0, 0)
        dx, dy = ref.get_window().get_origin()[1:]
        wa = widget.get_allocation()

        # fit menu to screen, aligned per text direction
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        menu.realize()
        ma = menu.get_allocation()

        menu_y_under = y + dy + wa.height
        menu_y_above = y + dy - ma.height
        if under:
            menu_y = menu_y_under
            if menu_y + ma.height > screen_height and menu_y_above > 0:
                menu_y = menu_y_above
        else:
            menu_y = menu_y_above
            if menu_y < 0 and menu_y_under + ma.height < screen_height:
                menu_y = menu_y_under

        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
            menu_x = min(x + dx, screen_width - ma.width)
        else:
            menu_x = max(0, x + dx - ma.width + wa.width)

        return (menu_x, menu_y, True) # x, y, move_within_screen
    menu_popup(menu, None, None, pos_func, None, button, time)


def _ensure_menu_attached(menu, widget):
    assert widget is not None

    # Workaround the menu inheriting the wrong colors with the Ubuntu 12.04
    # default themes. Attaching to the parent kinda works... submenus still
    # have the wrong color.
    if isinstance(widget, Gtk.Button):
        widget = widget.get_parent() or widget

    attached_widget = menu.get_attach_widget()
    if attached_widget is widget:
        return
    if attached_widget is not None:
        menu.detach()
    menu.attach_to_widget(widget, None)


def popup_menu_under_widget(menu, widget, button, time):
    _ensure_menu_attached(menu, widget)
    _popup_menu_at_widget(menu, widget, button, time, True)


def popup_menu_above_widget(menu, widget, button, time):
    _ensure_menu_attached(menu, widget)
    _popup_menu_at_widget(menu, widget, button, time, False)


def popup_menu_at_widget(menu, widget, button, time):
    _ensure_menu_attached(menu, widget)
    menu_popup(menu, None, None, None, None, button, time)


def add_fake_accel(widget, accel):
    """Accelerators are only for window menus and global keyboard shortcuts.

    Since we want to use them in context menus as well, to indicate which
    key events the parent widget knows about, we use a global fake
    accelgroup without any actions..
    """

    if not hasattr(add_fake_accel, "_group"):
        add_fake_accel._group = Gtk.AccelGroup()
    group = add_fake_accel._group

    key, val = Gtk.accelerator_parse(accel)
    assert key is not None
    assert val is not None
    widget.add_accelerator(
        'activate', group, key, val, Gtk.AccelFlags.VISIBLE)


def is_accel(event, *accels):
    """Checks if the given keypress Gdk.Event matches
    any of accelerator strings.

    example: is_accel(event, "<shift><ctrl>z")
    """

    assert accels

    if event.type != Gdk.EventType.KEY_PRESS:
        return False

    # ctrl+shift+x gives us ctrl+shift+X and accelerator_parse returns
    # lowercase values for matching, so lowercase it if possible
    keyval = event.keyval
    if not keyval & ~0xFF:
        keyval = ord(chr(keyval).lower())

    default_mod = Gtk.accelerator_get_default_mod_mask()

    for accel in accels:
        accel_keyval, accel_mod = Gtk.accelerator_parse(accel)

        # If the accel contains non default modifiers matching will
        # never work and since no one should use them, complain
        non_default = accel_mod & ~default_mod
        if non_default:
            print_w("Accelerator '%s' contains a non default modifier '%s'." %
                (accel, Gtk.accelerator_name(0, non_default) or ""))

        # Remove everything except default modifiers and compare
        if (accel_keyval, accel_mod) == (keyval, event.state & default_mod):
            return True

    return False


def add_css(widget, css):
    """Add css for the widget, overriding the theme.

    Can raise GLib.GError in case the css is invalid
    """

    if not isinstance(css, bytes):
        css = css.encode("utf-8")

    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    context = widget.get_style_context()
    context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def remove_padding(widget):
    """Removes padding on supplied widget"""
    return add_css(widget, " * { padding: 0px; } ")


def is_wayland():
    # FIXME: Is there no better way?
    display = Gdk.Display.get_default()
    if display:
        return display.get_name() == "Wayland"
    return False


def get_backend_name():
    """The GDK backend name"""

    display = Gdk.Display.get_default()
    if display is not None:
        name = gdecode(display.__gtype__.name)
        if name.startswith("Gdk"):
            name = name[3:]
        if name.endswith("Display"):
            name = name[:-7]
        return name
    return u"Unknown"


gtk_version = (Gtk.get_major_version(), Gtk.get_minor_version(),
               Gtk.get_micro_version())

try:
    pygobject_version = gi.version_info
except AttributeError:
    # older gi versions
    try:
        pygobject_version = gi._gobject.pygobject_version
    except AttributeError:
        pygobject_version = (-1,)


def io_add_watch(fd, prio, condition, func, *args, **kwargs):
    try:
        # The new gir bindings don't fail with an invalid fd,
        # and we can't do the same with the static ones (return a valid
        # source ID..) so fail with newer pygobject as well.
        if isinstance(fd, int) and fd < 0:
            raise ValueError("invalid fd")
        elif hasattr(fd, "fileno") and fd.fileno() < 0:
            raise ValueError("invalid fd")
        return GLib.io_add_watch(fd, prio, condition, func, *args, **kwargs)
    except TypeError:
        # older pygi
        kwargs["priority"] = prio
        return GLib.io_add_watch(fd, condition, func, *args, **kwargs)


def add_signal_watch(signal_action):
    """Catches signals which should exit the program and calls `signal_action`
    after the main loop has started, even if the signal occurred before the
    main loop has started.
    """

    sig_names = ["SIGINT", "SIGTERM", "SIGHUP"]
    if os.name == "nt":
        sig_names = ["SIGINT", "SIGTERM"]

    signals = {}
    for name in sig_names:
        id_ = getattr(signal, name, None)
        if id_ is None:
            continue
        signals[id_] = name

    # in case Python catches a signal, wake up the mainloop.
    # this makes signal handling work with older pygobject/glib (Ubuntu 12.04)
    # no idea why..
    rfd, wfd = os.pipe()

    def wakeup_notify(source, condition):
        # just read and do nothing so we can keep the watch around
        if condition == GLib.IO_IN:
            try:
                os.read(rfd, 1)
            except EnvironmentError:
                pass
            return True
        else:
            return False

    try:
        import fcntl
    except ImportError:
        pass
    else:
        fcntl.fcntl(wfd, fcntl.F_SETFL, os.O_NONBLOCK)

    signal.set_wakeup_fd(wfd)
    io_add_watch(rfd, GLib.PRIORITY_HIGH,
                 GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
                 wakeup_notify)

    # set a python handler for each signal, used before the mainloop
    for signum, name in signals.items():
        # Before the mainloop starts we catch signals in python
        # directly and idle_add the app.quit
        def idle_handler(signum, frame):
            print_d("Python signal handler activated: %s" % signals[signum])
            GLib.idle_add(signal_action, priority=GLib.PRIORITY_HIGH)

        print_d("Register Python signal handler: %r" % name)
        signal.signal(signum, idle_handler)

    if os.name == "nt":
        return

    # also try to use the official glib handling if available,
    # can't hurt I guess
    unix_signal_add = None
    if hasattr(GLib, "unix_signal_add"):
        unix_signal_add = GLib.unix_signal_add
    elif hasattr(GLib, "unix_signal_add_full"):
        unix_signal_add = GLib.unix_signal_add_full
    else:
        print_d("Can't install GLib signal handler, too old gi or wrong OS")
        return

    for signum, name in signals.items():

        def handler(signum):
            print_d("GLib signal handler activated: %s" % signals[signum])
            signal_action()

        print_d("Register GLib signal handler: %r" % name)
        unix_signal_add(GLib.PRIORITY_HIGH, signum, handler, signum)


class ThemeOverrider(object):
    """Allows registering global Gtk.StyleProviders for a specific theme.
    They get activated when the theme gets active and removed when the theme
    changes to something else.
    """

    def __init__(self):
        self._providers = {}
        self._active_providers = []
        settings = Gtk.Settings.get_default()
        settings.connect("notify::gtk-theme-name", self._on_theme_name_notify)
        settings.notify("gtk-theme-name")

    def register_provider(self, theme_name, provider):
        """
        Args:
            theme_name (str): A gtk+ theme name e.g. "Adwaita" or empty to
                apply to all themes
            provider (Gtk.StyleProvider)
        """

        self._providers.setdefault(theme_name, []).append(provider)
        settings = Gtk.Settings.get_default()
        settings.notify("gtk-theme-name")

    def _on_theme_name_notify(self, settings, gparam):

        theme_name = settings.get_property(gparam.name)
        wanted_providers = \
            self._providers.get(theme_name, []) + self._providers.get("", [])

        for provider in list(self._active_providers):
            if provider not in wanted_providers:
                Gtk.StyleContext.remove_provider_for_screen(
                    Gdk.Screen.get_default(), provider)
            self._active_providers.remove(provider)

        for provider in wanted_providers:
            if provider not in self._active_providers:
                Gtk.StyleContext.add_provider_for_screen(
                    Gdk.Screen.get_default(),
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
                self._active_providers.append(provider)


from .msg import Message, ErrorMessage, WarningMessage
from .x import Align, Button, ToggleButton, Notebook, SeparatorMenuItem, \
    WebImage, MenuItem, Frame, EntryCompletion
from .icons import Icons
from .window import Window, UniqueWindow, Dialog
from .paned import ConfigRPaned, ConfigRHPaned

Message, ErrorMessage, WarningMessage
Align, Button, ToggleButton, Notebook, SeparatorMenuItem, \
    WebImage, MenuItem, Frame, EntryCompletion
Icons
Window, UniqueWindow, Dialog
ConfigRPaned, ConfigRHPaned
