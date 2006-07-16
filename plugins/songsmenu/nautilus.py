# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import bonobo
from qltk import ConfirmAction
from plugins.songsmenu import SongsMenuPlugin

class ViewNautilus(SongsMenuPlugin):
    PLUGIN_ID = 'View in Nautilus'
    PLUGIN_NAME = _('View in Nautilus')
    PLUGIN_DESC = _('View directories in Nautilus.')
    PLUGIN_ICON = 'gtk-open'
    PLUGIN_VERSION = '0.15'

    def plugin_songs(self, songs):
        dirs = dict.fromkeys([song('~dirname') for song in songs]).keys()
        if len(dirs) < 4 or ConfirmAction(
            None, "Open %d Windows?" % len(dirs),
            "Do you want to open %d Nautilus windows?" % len(dirs)).run():
            nautilus = bonobo.get_object(
                'OAFIID:Nautilus_Shell', 'Nautilus/Shell')
            nautilus.open_windows(dirs, '', '', '')
