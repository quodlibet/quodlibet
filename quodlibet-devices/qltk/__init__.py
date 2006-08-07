# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

def get_top_parent(widget):
    """Return the ultimate parent of a widget; the assumption that code
    using this makes is that it will be a gtk.Window, i.e. the widget
    is fully packed when this is called."""
    return widget and widget.get_ancestor(gtk.Window)

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
            
# Legacy plugin/code support.
from qltk.getstring import GetStringDialog
from qltk.msg import *
from qltk.x import *
