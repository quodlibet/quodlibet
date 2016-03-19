# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
from quodlibet.config import RatingsPrefs, RATINGS

from quodlibet import print_d, print_w
from quodlibet.formats.remote import RemoteFile
from quodlibet.library.libraries import SongLibrary
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

    def rename(self, song, newname, changed=None):
        raise TypeError("Can't rename Soundcloud files")

    def _on_songs_received(self, client, songs):
        new = len(self.add(songs))
        print_d("Got %d songs (%d new)." % (len(songs), new))


class SoundcloudFile(RemoteFile):
    format = "Remote Soundcloud File"

    def __init__(self, uri, client=None):
        super(SoundcloudFile, self).__init__(uri)
        self.client = client
        if not self.client:
            raise EnvironmentError("Must have a Soundcloud client")

    def set_image(self, image):
        raise TypeError("Can't change images on Soundcloud")

    @property
    def track_id(self):
        return self["soundcloud_track_id"]

    def can_change(self, k=None):
        if k is None:
            return ["~rating", "~#rating"]
        else:
            return "rating" in k

    def write(self):
        if not self.client or not self.client.online:
            print_w("Can't save without a logged-in Soundcloud client")
            return
        # There's not much that can be written
        self._write_rating()

    def _write_rating(self):
        track_id = self.track_id
        if self.has_rating and self("~#rating") >= RATINGS.default:
            self.client.put_favourite(track_id)
        else:
            self.client.remove_favourite(track_id)