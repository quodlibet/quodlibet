# Copyright 2008 Joe Wreschnig
#      2016-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import functools

from quodlibet import _
from quodlibet.plugins.songshelpers import any_song, is_finite, is_writable
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.util.collection import PEOPLE
from quodlibet.util.string.filter import remove_diacritics

SUPPORTED_TAGS = ["album", "artist", "albumartist", "composer", "performer"]

# Pretty arbitrary, but helps a lot IMO
FAMOUS_COMPOSERS = {
    "bach", "mozart", "beethoven", "chopin", "brahms", "faure",
    "rachmaninov", "rachmaninoff", "puccini"
    "mendelssohn", "liszt", "elgar", "mahler", "debussy", "bartok", "schumann",
    "dvorak", "holst", "britten", "straus"
    "williams", "zimmer"}


def artist_to_sort(tag: str, artist: str) -> str | None:
    try:
        first, rest = artist.split(" ", 1)
    except ValueError:
        pass
    else:
        # "The Beach Boys" -> "Beach Boys, The" etc
        if first.lower() in ["a", "the"]:
            return ", ".join([rest, first])
        # We really want "Amadeus Mozart" -> "Mozart, Amadeus"
        # But not really "Rage Against The Machine" -> "Machine, Rage Against The"
        # So let's restrict to composer then.
        try:
            rest, last = artist.rsplit(" ", 1)
            last_normalised = remove_diacritics(last).lower()
            if tag in {"composer"} or last_normalised in FAMOUS_COMPOSERS:
                return ", ".join([last, rest])
        except ValueError:
            pass
    return None


def album_to_sort(album: str) -> str | None:
    try:
        first, rest = album.split(" ", 1)
    except ValueError:
        pass
    else:
        if first.lower() in ["a", "the"]:
            return ", ".join([rest, first])
    return None


class MakeSortTags(SongsMenuPlugin):
    PLUGIN_ID = "SortTags"
    PLUGIN_NAME = _("Create Sort Tags")
    PLUGIN_DESC_MARKUP = _(
        "Guesses sort tags for albums and people.\n\ne.g.\n\n"
        "  <tt>album</tt>: <i>The Greatest Hits</i> → <i>Greatest Hits, The</i>\n"
        "  <tt>composer</tt>: <i>Irving Berlin</i> → <i>Berlin, Irving</i>\n"
        "  <tt>artist</tt>: <i>Franz Liszt</i> → <i>Liszt, Franz</i>\n"
        "  <tt>artist</tt>: <i>The Beach Boys</i> → <i>Beach Boys, The</i>\n"
       "\nApplies to tags: <tt>%s</tt>") % ", ".join(SUPPORTED_TAGS)
    PLUGIN_ICON = Icons.EDIT

    plugin_handles = any_song(is_writable, is_finite)

    def plugin_song(self, song):
        for tag in SUPPORTED_TAGS:
            func = (functools.partial(artist_to_sort, tag)
                    if tag in PEOPLE else album_to_sort)
            values = [v for tag in song.list(tag) if (v:=func(tag))]
            if values and (tag + "sort") not in song:
                song[tag + "sort"] = "\n".join(values)
