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
    return widget and widget.get_ancestor(gtk.Window)

# Legacy plugin/code support.
from qltk.getstring import GetStringDialog
from qltk.msg import *
from qltk.x import *
