# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

def get_top_parent(widget):
    """Return the ultimate parent of a widget; the assumption that code
    using this makes is that it will be a gtk.Window, i.e. the widget
    is fully packed when this is called."""
    if widget is not None:
        while widget.parent is not None: widget = widget.parent
    return widget

# Legacy plugin/code support.
from qltk.msg import *
from qltk.x import *
from qltk.getstring import GetStringDialog
