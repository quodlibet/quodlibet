# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.util.dprint import print_d, print_w
from quodlibet.browsers.soundcloud.query import SoundcloudQuery
from quodlibet import config
from quodlibet.formats.remote import RemoteFile
from quodlibet.library.libraries import SongLibrary
from quodlibet.util import cached_property, print_exc


class SoundcloudLibrary(SongLibrary):
    STAR = ["artist", "title", "genre", "tags"]

    def __init__(self, client, player=None):
        super().__init__("Soundcloud")
        self.client = client
        self.client.connect('songs-received', self._on_songs_received)
        self.client.connect('comments-received', self._on_comments_received)
        if player:
            player.connect('song-started', self.__song_started)

    def query(self, text, sort=None, star=STAR):
        values = self._contents.values()
        try:
            return SoundcloudQuery(text).filter(values)
        except SoundcloudQuery.error:
            return values

    def query_with_refresh(self, text, sort=None, star=STAR):
        """Queries Soundcloud for some (more) relevant results, then filters"""
        current = self._contents.values()

        query = SoundcloudQuery(text, star=star)
        if not query.is_parsable:
            return current
        self.client.get_tracks(query.terms)
        filtered = query.filter(current)
        print_d("Filtered %d results to %d" % (len(current), len(filtered)))
        return filtered

    def rename(self, song, newname, changed=None):
        raise TypeError("Can't rename Soundcloud files")

    def _on_songs_received(self, client, songs):
        new = len(self.add(songs))
        print_d("Got %d songs (%d new)." % (len(songs), new))
        self.emit('changed', songs)

    def _on_comments_received(self, client, track_id, comments):
        def bookmark_for(com):
            text = "\"%s\" --%s" % (com['body'], com['user']['username'])
            return max(0, int((com.get('timestamp') or 0) / 1000.0)), text

        try:
            song = self.song_by_track_id(track_id)
        except KeyError:
            # https://github.com/quodlibet/quodlibet/issues/2410
            print_exc()
            return
        song.bookmarks = [bookmark_for(c) for c in comments]

    def song_by_track_id(self, track_id):
        for song in self.values():
            if song.track_id == track_id:
                return song
        raise KeyError("No track with id %s. Do have %s"
                       % (track_id, [s.track_id for s in self.values()]))

    def _changed(self, items):
        super()._changed(items)
        # We should ask the AudioFile subclass to write what it can ASAP
        for item in items:
            item.write()

    def __song_started(self, player, song):
        if isinstance(song, SoundcloudFile):
            print_d("Getting comments for %s (%s)" % (song("title"), song.key))
            self.client.get_comments(song.track_id)


class SoundcloudFile(RemoteFile):
    format = "Remote Soundcloud File"

    def __init__(self, uri, track_id, favorite=False, client=None):
        super().__init__(uri)
        self.client = client
        self["soundcloud_track_id"] = track_id
        self.favorite = favorite
        if self.favorite:
            self['~#rating'] = 1.0
        if not self.client:
            raise EnvironmentError("Must have a Soundcloud client")

    def set_image(self, image):
        raise TypeError("Can't change images on Soundcloud")

    @cached_property
    def track_id(self):
        return int(self["soundcloud_track_id"])

    @cached_property
    def key(self):
        return "track-%s" % (self.track_id,)

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
        should_fave = (self.has_rating and
                       self("~#rating") >= config.RATINGS.default)
        track_id = self.track_id
        if not self.favorite and should_fave:
            self.client.put_favorite(track_id)
            self.favorite = True
        elif self.favorite and not should_fave:
            self.client.remove_favorite(track_id)
            self.favorite = False
