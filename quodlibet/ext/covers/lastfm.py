# Copyright 2013 Simonas Kazlauskas
#           2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from os import path

from quodlibet import _
from quodlibet.plugins.cover import cover_dir
from quodlibet.util import print_d
from quodlibet.util.cover.http import ApiCoverSourcePlugin, escape_query_value
from quodlibet.util.path import escape_filename


class LastFMCover(ApiCoverSourcePlugin):
    PLUGIN_ID = "lastfm-cover"
    PLUGIN_NAME = _("Last.fm Cover Source")
    PLUGIN_DESC = _("Downloads covers from Last.fm's cover art archive.")

    @classmethod
    def group_by(cls, song):
        return song.album_key

    @staticmethod
    def priority():
        return 0.33  # No cover size guarantee, accurate

    @property
    def cover_path(self):
        mbid = self.song.get("musicbrainz_albumid", None)
        # It is beneficial to use mbid for cover names.
        if mbid:
            return path.join(cover_dir, escape_filename(mbid))
        else:
            return super().cover_path

    @property
    def url(self):
        _url = (
            "https://ws.audioscrobbler.com/2.0?method=album.getinfo&"
            + "api_key=107db6fd4c1c7f53b1526fafddab2c82&format=json&"
            + "artist={artist}&album={album}&mbid={mbid}"
        )
        song = self.song
        # This can work well for albums in Last.FM
        artists = self._album_artists_for(song) or "Various Artists"
        song = self.song
        artist = escape_query_value(artists)
        album = escape_query_value(song.get("album", ""))
        mbid = escape_query_value(song.get("musicbrainz_albumid", ""))
        if (artist and album) or mbid:
            return _url.format(artist=artist, album=album, mbid=mbid)
        else:
            return None  # Not enough data

    def _handle_search_response(self, message, json, data=None):
        if not json:
            print_d("Server did not return valid JSON")
            return self.emit("search-complete", [])
        album = json.get("album", {})
        if not album:
            print_d("Album data is not available")
            return self.emit("search-complete", [])
        results = []
        for img in album["image"]:
            if img["size"] in ("mega", "extralarge"):
                url = img["#text"]
                if not url:
                    # Yes sometimes it's there but blank
                    continue
                print_d(f"Got last.fm image: {img}")
                results.append(
                    {
                        "artist": album["artist"],
                        "album": album["name"],
                        "cover": url.replace("/300x300", "/500x500"),
                        "dimensions": "500x500",
                    }
                )
                # This one can be massive, and slow
                results.append(
                    {
                        "artist": album["artist"],
                        "album": album["name"],
                        "cover": url.replace("/300x300", ""),
                        "dimensions": "(original)",
                    }
                )
                # Prefer the bigger ones
                break
        self.emit("search-complete", results)
