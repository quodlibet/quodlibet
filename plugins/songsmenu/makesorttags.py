# Copyright 2008 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from plugins.songsmenu import SongsMenuPlugin

def artist_to_sort(artist):
    try:
        rest, last = artist.rsplit(" ", 1)
    except ValueError:
        return None
    else:
        return ", ".join([last, rest])

def album_to_sort(album):
    try:
        first, rest = album.split(" ", 1)
    except ValueError:
        return None
    else:
        if first.lower() in ["a", "the"]:
            return ", ".join([rest, first])

class MakeSortTags(SongsMenuPlugin):
    PLUGIN_ID = "SortTags"
    PLUGIN_NAME = _("Create Sort Tags")
    PLUGIN_DESC = _("Convert album and artist names to sort names, poorly.")
    PLUGIN_ICON = 'gtk-edit'
    PLUGIN_VERSION = "1"

    def plugin_song(self, song):
        for tag in ["album"]:
            values = filter(None, map(album_to_sort, song.list(tag)))
            if values and (tag + "sort") not in song:
                song[tag + "sort"] = "\n".join(values)

        for tag in ["artist", "albumartist", "performer"]:
            values = filter(None, map(artist_to_sort, song.list(tag)))
            if values and (tag + "sort") not in song:
                song[tag + "sort"] = "\n".join(values)
