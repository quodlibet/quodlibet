# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

def get_top_parent(widget):
    """Return the ultimate parent of a widget; the assumption that code
    using this makes is that it will be a gtk.Window, i.e. the widget
    is fully packed when this is called."""
    parent = widget and widget.get_toplevel()
    if parent and (parent.flags() & gtk.TOPLEVEL):
        return parent
    else:
        return None

def popup_menu_under_widget(menu, widget, button, time):
    def pos_func(menu, widget=widget):
        screen = widget.get_screen()
        ref = get_top_parent(widget)
        menu.set_screen(screen)
        x, y = widget.translate_coordinates(ref, 0, 0)
        dx, dy = ref.window.get_origin()
        wa = widget.allocation

        # fit menu to screen, aligned per text direction
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        menu.realize()
        ma = menu.allocation
        menu_y = y + dy + wa.height
        if menu_y + ma.height > screen_height and y + dy - ma.height > 0:
            menu_y = y + dy - ma.height
        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_LTR: 
            menu_x = min(x + dx, screen_width - ma.width)
        else:
            menu_x = max(0, x + dx - ma.width + wa.width)
        return (menu_x, menu_y, True) # x, y, move_within_screen
    menu.popup(None, None, pos_func, button, time)
    return True

def is_accel(event, accel):
    """Checks if the given gtk.gdk.Event matches an accelerator string

    example: is_accel(event, "<shift><ctrl>z")
    """
    if event.type != gtk.gdk.KEY_PRESS:
        return False

    # ctrl+shift+x gives us ctrl+shift+X and accelerator_parse returns
    # lowercase values for matching, so lowercase it if possible
    keyval = event.keyval
    if not keyval & ~0xFF:
        keyval = ord(chr(keyval).lower())

    default_mod = gtk.accelerator_get_default_mod_mask()
    accel_keyval, accel_mod = gtk.accelerator_parse(accel)

    # If the accel contains non default modifiers matching will never work and
    # since no one should use them, complain
    non_default = accel_mod & ~default_mod
    if non_default:
        print_w("Accelerator '%s' contains a non default modifier '%s'." %
            (accel, gtk.accelerator_name(0, non_default) or ""))

    # Remove everything except default modifiers and compare
    return (accel_keyval, accel_mod) == (keyval, event.state & default_mod)

# Legacy plugin/code support.
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.msg import *
from quodlibet.qltk.x import *
