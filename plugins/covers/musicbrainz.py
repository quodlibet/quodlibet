# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from os import path
from gi.repository import Soup, Gio, GLib

from quodlibet.plugins.cover import CoverSourcePlugin, cover_dir
from quodlibet.util.http import HTTPRequest
from quodlibet.util.cover.http import HTTPDownloadMixin


class MusicBrainzCover(CoverSourcePlugin, HTTPDownloadMixin):
    PLUGIN_ID = "musicbrainz-cover"
    PLUGIN_NAME = _("MusicBrainz cover source")
    PLUGIN_DESC = _("Download covers from musicbrainz's cover art archive")
    PLUGIN_VERSION = "1.0"

    @staticmethod
    def priority():
        # It's a pretty good source
        return 0.65

    @property
    def cover_path(self):
        return path.join(cover_dir, self.mbid) if self.mbid else None

    @property
    def mbid(self):
        return self.song.get('musicbrainz_albumid', None)

    @property
    def url(self):
        if not self.mbid:
            return None
        mbid = Soup.URI.encode(self.mbid, None)
        return 'http://coverartarchive.org/release/{0}/front'.format(mbid)

    def fetch_cover(self):
        if not self.mbid:
            return self.fail('MBID is required to fetch the cover')
        self.download(Soup.Message.new('GET', self.url))
