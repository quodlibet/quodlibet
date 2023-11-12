# Copyright 2016-2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GLib

from quodlibet import config, _
from quodlibet.browsers.soundcloud.query import SoundcloudQuery
from quodlibet.formats import AudioFile
from quodlibet.formats.remote import RemoteFile
from quodlibet.library import SongLibrary
from quodlibet.library.base import K
from quodlibet.qltk.notif import Task
from quodlibet.util import cached_property, print_exc, copool
from quodlibet.util.dprint import print_d, print_w
from senf import fsnative


class SoundcloudLibrary(SongLibrary[K, "SoundcloudFile"]):
    STAR = ["artist", "title", "genre", "tags"]

    def __init__(self, client, player=None):
        super().__init__("Soundcloud")
        self.client = client
        self._sids = [
            self.client.connect("songs-received", self._on_songs_received),
            self.client.connect("stream-uri-received", self._on_stream_uri_received),
            self.client.connect("comments-received", self._on_comments_received)
        ]
        self._psid = None
        # Keep track of async-changed songs for bulk signalling
        self._dirty = set()
        GLib.timeout_add(2000, self._on_tick)
        if player:
            self.player = player
            self._psid = self.player.connect("song-started", self.__song_started)

    def destroy(self):
        super().destroy()
        for sid in self._sids:
            self.client.disconnect(sid)
        if self._psid:
            self.player.disconnect(self._psid)

    def query(self, text, sort=None, star=STAR):
        values = self._contents.values()
        try:
            return SoundcloudQuery(text).filter(values)
        except SoundcloudQuery.Error:
            return values

    def query_with_refresh(self, query: SoundcloudQuery):
        """Queries Soundcloud for some (more) relevant results, then filters"""
        current = self._contents.values()

        if not query.is_parsable:
            return current
        self.client.get_tracks(query.terms)
        filtered = query.filter(current)
        print_d("Filtered %d results to %d" % (len(current), len(filtered)))
        return filtered

    def rename(self, song, newname, changed=None):
        raise TypeError("Can't rename Soundcloud files")

    def _get_stream_urls(self, songs):
        # Pre-cache. It's horrible, but at least you can play things immediately
        with Task(_("Soundcloud"), "Pre-fetching stream URLs") as task:
            total = len(songs)
            for i, song in enumerate(songs):
                # Only update ones without streaming URLs
                # TODO: But yes these will time out...
                if "~uri" not in song or "api.soundcloud.com" in song["~uri"]:
                    self.client.get_stream_url(song)
                task.update(i / total)
                yield

    def _on_songs_received(self, client, songs):
        print_d(f"Got {len(songs)} songs")
        self.add(songs)
        # Can't have multiple requests cancel each other's copools
        funcid = hash("".join(s["~uri"] for s in songs))
        # Rate limit a little to avoid 429s
        copool.add(self._get_stream_urls, songs, timeout=100, funcid=funcid)

    def _on_stream_uri_received(self, client, song: AudioFile, uri: str):
        # URI isn't the key in this SoundcloudFile, so this is OK
        song["~uri"] = uri
        self._dirty.add(song)

    def _on_tick(self) -> bool:
        if self._dirty:
            self.changed(self._dirty)
            self._dirty.clear()
        return True

    def _on_comments_received(self, client, track_id, comments):
        def bookmark_for(com):
            text = f'{com["body"]!r} – {com["user"]["username"]}'
            return max(0, int((com.get("timestamp") or 0) / 1000.0)), text

        try:
            song = self.song_by_track_id(track_id)
        except KeyError:
            # https://github.com/quodlibet/quodlibet/issues/2410
            print_exc()
            return
        song.bookmarks = [bookmark_for(c) for c in comments]
        print_d(f"Updated song bookmarks for {song('title')}")

    def song_by_track_id(self, track_id):
        for song in self.values():
            if song.track_id == track_id:
                return song
        raise KeyError(f"No track with id {track_id}. "
                       f"Do have {[s.track_id for s in self.values()]}")

    def _changed(self, items):
        super()._changed(items)
        # We should ask the AudioFile subclass to write what it can ASAP
        for item in items:
            item.write()

    def __song_started(self, player, song):
        if isinstance(song, SoundcloudFile):
            print_d(f"Getting comments for {song('title')} ({song.key})")
            self.client.get_comments(song.track_id)


class SoundcloudFile(RemoteFile):
    format = "Remote Soundcloud File"

    def __init__(self, uri: str, track_id: int, client, favorite: bool = False):
        # Don't call super, it invokes __getitem__
        self["~uri"] = uri
        self.sanitize(fsnative(uri))
        self.client = client
        if not self.client:
            raise OSError("Must have a Soundcloud client")
        self["soundcloud_track_id"] = track_id
        self.favorite = favorite
        if self.favorite:
            self["~#rating"] = 1.0

    def set_image(self, image):
        raise TypeError("Can't change images on Soundcloud")

    @cached_property
    def track_id(self):
        return int(self["soundcloud_track_id"])

    @cached_property
    def key(self):
        return f"track-{self.track_id}"

    def can_change(self, k=None):
        if k is None:
            return ["~rating", "~#rating"]
        else:
            return k.endswith("rating")

    def write(self):
        if not self.client or not self.client.online:
            print_w("Can't save without a logged-in Soundcloud client")
            return
        # There's not much that can be written
        self._write_rating()

    def _write_rating(self):
        should_fave = self.has_rating and self("~#rating") >= config.RATINGS.default
        track_id = self.track_id
        if not self.favorite and should_fave:
            self.client.save_favorite(track_id)
            self.favorite = True
        elif self.favorite and not should_fave:
            self.client.remove_favorite(track_id)
            self.favorite = False
