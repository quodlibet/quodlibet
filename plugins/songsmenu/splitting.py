# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import util
from plugins.songsmenu import SongsMenuPlugin

class SplitTags(SongsMenuPlugin):
    PLUGIN_ID = "Split Tags"
    PLUGIN_NAME = _("Split Tags")
    PLUGIN_HINT = "Split out version and disc number"
    PLUGIN_DESC = ("Split the disc number from the album and the version "
                   "from the title at the same time.")
    PLUGIN_ICON = 'gtk-find-and-replace'
    PLUGIN_VERSION = "0.13"

    def plugin_song(self, song):
        if ("title" in song and
            song.can_change("title") and song.can_change("version")):
            title, versions = util.split_title(song["title"])
            if title: song["title"] = title
            if versions: song["version"] = "\n".join(versions)

        if ("album" in song and "discnumber" not in song and
            song.can_change("album") and song.can_change("discnumber")):
            album, disc = util.split_album(song["album"])
            if album: song["album"] = album
            if disc: song["discnumber"] = disc

class SplitAlbum(SongsMenuPlugin):
    PLUGIN_ID = "Split Album"
    PLUGIN_NAME = _("Split Album")
    PLUGIN_HINT = "Split out disc number"
    PLUGIN_ICON = 'gtk-find-and-replace'
    PLUGIN_VERSION = "0.13"

    def plugin_song(self, song):
        if ("album" in song and "discnumber" not in song and
            song.can_change("album") and song.can_change("discnumber")):
            album, disc = util.split_album(song["album"])
            if album: song["album"] = album
            if disc: song["discnumber"] = disc
