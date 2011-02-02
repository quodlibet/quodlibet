# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import mutagen.apev2

from quodlibet.formats._apev2 import APEv2File
from quodlibet.formats.mp3 import MP3File
from quodlibet.plugins.songsmenu import SongsMenuPlugin

class APEv2toID3v2(SongsMenuPlugin):
    PLUGIN_ID = "APEv2 to ID3v2"
    PLUGIN_NAME = _("APEv2 to ID3v2")
    PLUGIN_DESC = ("Convert your APEv2 tags to ID3v2 tags. This will delete "
                   "the APEv2 tags after conversion.")
    PLUGIN_ICON = 'gtk-convert'
    PLUGIN_VERSION = '0.2'

    def plugin_handles(self, songs):
        for song in songs:
            if not song.get("~filename", "").lower().endswith(".mp3"):
                return False
        return True

    def plugin_song(self, song):
        try: apesong = APEv2File(song["~filename"])
        except: return # File doesn't have an APEv2 tag
        song.update(apesong)
        mutagen.apev2.delete(song["~filename"])
        song._song.write()
