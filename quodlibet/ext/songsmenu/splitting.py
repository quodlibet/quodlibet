# Copyright 2005 Joe Wreschnig
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet.plugins.songshelpers import any_song
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.string.splitters import split_title, split_album, split_genre
from quodlibet.qltk import Icons


def has_album_splittable(song):
    return (
        "album" in song
        and "discnumber" not in song
        and song.can_change("album")
        and song.can_change("discnumber")
    )


def has_title_splittable(song):
    return "title" in song and song.can_change("title") and song.can_change("version")

def has_genre_splittable(song):
    return ("genre" in song and
            song.can_change("genre"))

class SplitTags(SongsMenuPlugin):
    PLUGIN_ID = "Split Tags"
    PLUGIN_NAME = _("Split Tags")
    PLUGIN_DESC = _(
        "Splits the disc number from the album and the version "
        "from the title at the same time."
    )
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    plugin_handles = any_song(has_title_splittable)

    def plugin_song(self, song):
        if has_title_splittable(song):
            title, versions = split_title(song["title"])
            if title:
                song["title"] = title
            if versions:
                song["version"] = "\n".join(versions)

        if has_album_splittable(song):
            album, disc = split_album(song["album"])
            if album:
                song["album"] = album
            if disc:
                song["discnumber"] = disc


class SplitAlbum(SongsMenuPlugin):
    PLUGIN_ID = "Split Album"
    PLUGIN_NAME = _("Split Album")
    PLUGIN_DESC = _("Split out disc number.")
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    plugin_handles = any_song(has_album_splittable)

    def plugin_song(self, song):
        if has_album_splittable(song):
            album, disc = split_album(song["album"])
            if album:
                song["album"] = album
            if disc:
                song["discnumber"] = disc


class SplitGenre(SongsMenuPlugin):
    PLUGIN_ID = "Split Genre"
    PLUGIN_NAME = _("Split Genre")
    PLUGIN_DESC = _("Split a single genre tag into multiple tags.")
    PLUGIN_ICON = Icons.EDIT_FIND_REPLACE

    plugin_handles = any_song(has_genre_splittable)

    def plugin_song(self, song):
        if has_genre_splittable(song):
            genre = split_genre(song["genre"])
            if genre:
                song["genre"] = genre
