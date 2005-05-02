# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import util

class SplitTags(object):
    PLUGIN_NAME = "Split Tags"
    PLUGIN_HINT = "Split out version and disc number"
    PLUGIN_DESC = ("Split the disc number from the album and the version "
                   "from the title at the same time.")
    PLUGIN_ICON = 'gtk-find-and-replace'
    PLUGIN_VERSION = "0.11"

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
