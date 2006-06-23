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
        ref = get_top_parent(widget)
        x, y = widget.translate_coordinates(ref, 0, 0)
        dx, dy = ref.window.get_origin()
        wa = widget.allocation
        if gtk.widget_get_default_direction() == gtk.TEXT_DIR_LTR: 
            return x + dx, y + dy + wa.height, 0
        else:
            menu.realize()
            ma = menu.allocation
            return x + dx - ma.width + wa.width, y + dy + wa.height, 0
    menu.popup(None, None, pos_func, button, time)
    return True
            
# Legacy plugin/code support.
from qltk.getstring import GetStringDialog
from qltk.msg import *
from qltk.x import *
