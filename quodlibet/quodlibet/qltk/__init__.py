# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

import gi
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib


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
    menu.popup(None, None, pos_func, None, button, time)
    return True


def popup_menu_under_widget(menu, widget, button, time):
    return _popup_menu_at_widget(menu, widget, button, time, True)


def popup_menu_above_widget(menu, widget, button, time):
    return _popup_menu_at_widget(menu, widget, button, time, False)


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

    provider = Gtk.CssProvider()
    provider.load_from_data(css)
    context = widget.get_style_context()
    context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def is_wayland():
    # FIXME: Is there no better way?
    display = Gdk.Display.get_default()
    if display:
        return display.get_name() == "Wayland"
    return False


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


# Legacy plugin/code support.
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.msg import *
from quodlibet.qltk.x import *
