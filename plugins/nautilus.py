# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

PLUGIN_NAME = 'View in Nautilus'
PLUGIN_DESC = 'View directories in Nautilus.'
PLUGIN_ICON = 'gtk-open'
PLUGIN_VERSION = '0.11'

import bonobo; from qltk import ConfirmAction
def plugin_songs(songs):
    dirs = dict.fromkeys([song('~dirname') for song in songs]).keys()
    if len(dirs) < 4 or ConfirmAction(None, "Open %d Windows?" % len(dirs),
            "Do you want to open %d Nautilus windows?" % len(dirs)).run():
        nautilus = bonobo.get_object('OAFIID:Nautilus_Shell', 'Nautilus/Shell')
        nautilus.open_windows(dirs, '', '')
