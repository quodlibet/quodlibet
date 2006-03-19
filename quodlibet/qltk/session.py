# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sys
import gtk
import const

def init():
    try: import gnome, gnome.ui
    except ImportError: return

    gnome.init("quodlibet", const.VERSION)
    client = gnome.ui.master_client()
    client.set_restart_style(gnome.ui.RESTART_IF_RUNNING)
    command = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    client.set_restart_command([command] + sys.argv[1:])
    client.connect('die', gtk.main_quit)
