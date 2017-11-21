# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.id3 import ID3

from quodlibet import _
from quodlibet import app
from quodlibet import util
from quodlibet.formats._id3 import ID3File
from quodlibet.plugins.songshelpers import any_song, is_writable, is_an_id3
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons


class RemoveID3TLEN(SongsMenuPlugin):
    PLUGIN_ID = "RemoveID3TLEN"
    PLUGIN_NAME = _("Fix MP3 Duration")
    PLUGIN_DESC = _("Removes TLEN frames from ID3 tags which can be the cause "
                    "for invalid song durations.")
    PLUGIN_ICON = Icons.EDIT_CLEAR

    plugin_handles = any_song(is_an_id3, is_writable)

    def plugin_songs(self, songs):
        for song in songs:
            song = song._song
            if not isinstance(song, ID3File):
                continue

            filename = song["~filename"]

            try:
                tag = ID3(filename)
            except Exception:
                util.print_exc()
                continue

            if not tag.getall("TLEN"):
                continue

            tag.delall("TLEN")

            try:
                tag.save()
            except Exception:
                util.print_exc()
                continue

            app.librarian.reload(song)
