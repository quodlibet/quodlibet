# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Don't write plugins like this unless you're really hardcore.

from qltk.remote import FIFOControl

def foo(self, watcher, window, player):
    import gtk
    from qltk.msg import ErrorMessage
    gtk.threads_enter()
    ErrorMessage(None, "Holy Crap!", "I should not be.").run()
    gtk.threads_leave()
FIFOControl._fmh = foo
