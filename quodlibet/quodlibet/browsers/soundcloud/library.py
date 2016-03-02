# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import print_d
from quodlibet.library import SongLibrary
from quodlibet.query import Query


class SoundcloudLibrary(SongLibrary):
    STAR = ["artist", "title", "genre", "comment"]

    def __init__(self, client):
        super(SoundcloudLibrary, self).__init__("Soundcloud")
        self.client = client
        self.client.connect('songs-received', self._on_songs_received)

    def query(self, text, sort=None, star=STAR):
        return Query(text).filter(self._contents.values())

    def query_with_refresh(self, text, sort=None, star=STAR):
        """Queries Soundcloud for some (more) relevant results, then filters"""
        print_d("Updating library with new results...")
        self.client.get_tracks(text.strip('"\''))
        return self.query(text, sort, star)

    def _on_songs_received(self, client, songs):
        new = len(self.add(songs))
        print_d("Got %d songs (%d new)." % (len(songs), new))
