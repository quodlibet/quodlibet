# Copyright 2005 Joe Wreschnig, Michael Urman
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gi
from gi.repository import Gtk
from gi.repository import Gdk


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


def popup_menu_under_widget(menu, widget, button, time):
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
        menu_y = y + dy + wa.height
        if menu_y + ma.height > screen_height and y + dy - ma.height > 0:
            menu_y = y + dy - ma.height
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.LTR:
            menu_x = min(x + dx, screen_width - ma.width)
        else:
            menu_x = max(0, x + dx - ma.width + wa.width)
        return (menu_x, menu_y, True) # x, y, move_within_screen
    menu.popup(None, None, pos_func, None, button, time)
    return True


def is_accel(event, accel):
    """Checks if the given keypress Gdk.Event matches an accelerator string

    example: is_accel(event, "<shift><ctrl>z")
    """
    if event.type != Gdk.EventType.KEY_PRESS:
        return False

    # ctrl+shift+x gives us ctrl+shift+X and accelerator_parse returns
    # lowercase values for matching, so lowercase it if possible
    keyval = event.keyval
    if not keyval & ~0xFF:
        keyval = ord(chr(keyval).lower())

    default_mod = Gtk.accelerator_get_default_mod_mask()
    accel_keyval, accel_mod = Gtk.accelerator_parse(accel)

    # If the accel contains non default modifiers matching will never work and
    # since no one should use them, complain
    non_default = accel_mod & ~default_mod
    if non_default:
        print_w("Accelerator '%s' contains a non default modifier '%s'." %
            (accel, Gtk.accelerator_name(0, non_default) or ""))

    # Remove everything except default modifiers and compare
    return (accel_keyval, accel_mod) == (keyval, event.state & default_mod)


gtk_version = (Gtk.get_major_version(), Gtk.get_minor_version(),
               Gtk.get_micro_version())

try:
    # no public way
    pygobject_version = gi._gobject.pygobject_version
except AttributeError:
    pygobject_version = (-1,)

# Legacy plugin/code support.
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.msg import *
from quodlibet.qltk.x import *
