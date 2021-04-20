# Copyright 2005 Joe Wreschnig
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import mutagen.apev2

from quodlibet import _
from quodlibet.formats import AudioFileError
from quodlibet.formats._apev2 import APEv2File
from quodlibet.plugins.songshelpers import each_song, is_writable
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.util import print_exc


def is_an_mp3(song):
    return song.get("~filename", "").lower().endswith(".mp3")


class APEv2toID3v2(SongsMenuPlugin):
    PLUGIN_ID = "APEv2 to ID3v2"
    PLUGIN_NAME = _("APEv2 to ID3v2")
    PLUGIN_DESC = _("Converts your APEv2 tags to ID3v2 tags. This will delete "
                    "the APEv2 tags after conversion.")
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    plugin_handles = each_song(is_an_mp3, is_writable)

    def plugin_song(self, song):
        try:
            apesong = APEv2File(song["~filename"])
        except:
            return # File doesn't have an APEv2 tag
        song.update(apesong)
        mutagen.apev2.delete(song["~filename"])
        try:
            song._song.write()
        except AudioFileError:
            print_exc()
