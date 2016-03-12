# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import any_song, is_writable


class ForceWrite(SongsMenuPlugin):
    PLUGIN_ID = "Force Write"
    PLUGIN_NAME = _("Force Write")
    PLUGIN_DESC = _("Saves the files again. This will make sure play counts "
                    "and ratings are up to date.")
    PLUGIN_ICON = Icons.DOCUMENT_SAVE

    plugin_handles = any_song(is_writable)

    def plugin_song(self, song):
        song._needs_write = True
