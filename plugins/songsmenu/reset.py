# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from plugins.songsmenu import SongsMenuPlugin

class ResetLibrary(SongsMenuPlugin):
    PLUGIN_ID = "Reset Library Data"
    PLUGIN_NAME = _("Reset Library Data")
    PLUGIN_VERSION = "1"
    PLUGIN_DESC = "Reset ratings, play counts, skip counts, and play times."
    PLUGIN_ICON = 'gtk-refresh'

    def plugin_song(self, song):
        song["~#rating"] = 0.5
        for key in ["~#playcount", "~#skipcount", "~#lastplayed",
                    "~#laststarted"]:
            song[key] = 0
