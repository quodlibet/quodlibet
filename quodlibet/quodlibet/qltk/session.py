# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys

import gtk

from quodlibet import const

def init(app_id, main_window):
    try: import gnome, gnome.ui
    except ImportError: return

    gnome.init(app_id, const.VERSION)
    client = gnome.ui.master_client()
    client.set_restart_style(gnome.ui.RESTART_IF_RUNNING)
    command = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    try: client.set_restart_command([command] + sys.argv[1:])
    except TypeError:
        # Fedora systems have a broken gnome-python wrapper for this function.
        # http://www.sacredchao.net/quodlibet/ticket/591
        # http://trac.gajim.org/ticket/929
        client.set_restart_command(len(sys.argv), [command] + sys.argv[1:])

    def destroy_window(client, window):
        gtk.gdk.threads_enter()
        window.destroy()
        gtk.gdk.threads_leave()
    client.connect('die', destroy_window, main_window)
