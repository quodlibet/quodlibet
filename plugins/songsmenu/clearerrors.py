# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from plugins.songsmenu import SongsMenuPlugin

class ForceWrite(SongsMenuPlugin):
    PLUGIN_ID = "ClearErrors"
    PLUGIN_NAME = _("Clear Errors")
    PLUGIN_DESC = _("Clears the ~errors tag from all selected files.")
    PLUGIN_ICON = 'gtk-clear'
    PLUGIN_VERSION = "1"

    def plugin_song(self, song):
        try: del(song["~errors"])
        except KeyError: pass
