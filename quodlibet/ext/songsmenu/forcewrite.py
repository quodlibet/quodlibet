# Copyright 2005 Joe Wreschnig
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import any_song, is_writable


class ForceWrite(SongsMenuPlugin):
    PLUGIN_ID = "Force Write"
    PLUGIN_NAME = _("Update Tags in Files")
    PLUGIN_DESC = _("Update modified tags in files. "
                    "This will ensure play counts and ratings are up to date.")
    PLUGIN_ICON = Icons.DOCUMENT_SAVE

    plugin_handles = any_song(is_writable)

    def plugin_song(self, song):
        song._needs_write = True
