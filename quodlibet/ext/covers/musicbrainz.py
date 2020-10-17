# Copyright 2013 Simonas Kazlauskas
#           2018-20 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from typing import Dict

from os import path
from gi.repository import Soup

from quodlibet import _
from quodlibet.plugins.cover import CoverSourcePlugin, cover_dir
from quodlibet.util.cover.http import HTTPDownloadMixin
from quodlibet.util.path import escape_filename


class MusicBrainzCover(CoverSourcePlugin, HTTPDownloadMixin):
    PLUGIN_ID = "musicbrainz-cover"
    PLUGIN_NAME = _("MusicBrainz Cover Source")
    PLUGIN_DESC = _("Downloads covers from MusicBrainz's cover art archive.")

    _SIZES = {"original": "front",
              "500x500": "front-500",
              "500x500 (back)": "back-500",
              "original (back)": "back"}

    @classmethod
    def group_by(cls, song):
        return song.get("musicbrainz_albumid", None)

    @staticmethod
    def priority():
        # It's a pretty good source, but very slow...
        return 0.55

    @property
    def cover_path(self):
        mbid = self.mbid
        if mbid is None:
            return super().cover_path
        return path.join(cover_dir, escape_filename(mbid))

    @property
    def mbid(self):
        return self.song.get("musicbrainz_albumid", None)

    def search(self):
        # This class has hard-coded search results,
        # and relies on 404s being filtered out later
        if not self.urls:
            return self.fail("No Musicbrainz tag found")
        self.emit("search-complete",
                  [{"cover": url, "dimensions": dims}
                   for dims, url in self.urls.items()])

    @property
    def urls(self) -> Dict[str, str]:
        if not self.mbid:
            return {}
        mbid = Soup.URI.encode(self.mbid, None)
        return {dim: f"https://coverartarchive.org/release/{mbid}/{extra}"
                for dim, extra in self._SIZES.items()}

    def fetch_cover(self):
        if not self.mbid:
            return self.fail("MBID is required to fetch the cover")
        self.download(Soup.Message.new("GET", self.urls.get("original", None)))
