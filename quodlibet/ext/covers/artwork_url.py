# Copyright 2016-2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from os import path
from gi.repository import Soup

from quodlibet import _
from quodlibet.plugins.cover import CoverSourcePlugin, cover_dir
from quodlibet.util.cover.http import HTTPDownloadMixin
from quodlibet.util.path import escape_filename


class ArtworkUrlCover(CoverSourcePlugin, HTTPDownloadMixin):
    PLUGIN_ID = "artwork-url-cover"
    PLUGIN_NAME = _("Artwork URL Cover Source")
    PLUGIN_DESC_MARKUP = _(
        "Downloads covers linked to by the <tt>artwork_url</tt> tag. "
        "This works with the Soundcloud and Podcasts browsers."
    )

    @classmethod
    def group_by(cls, song):
        return song.get("album", None)

    @staticmethod
    def priority():
        return 0.9

    @property
    def cover_path(self):
        url = self.url
        if url:
            return path.join(cover_dir, escape_filename(url))
        return None

    @property
    def url(self):
        return self.song.get("artwork_url", None)

    def fetch_cover(self) -> None:
        if self.url:
            self.download(Soup.Message.new("GET", self.url))
        else:
            self.fail("artwork_url missing", log=False)
