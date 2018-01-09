# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
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


class MusicBrainzCover(CoverSourcePlugin, HTTPDownloadMixin):
    PLUGIN_ID = "musicbrainz-cover"
    PLUGIN_NAME = _("MusicBrainz Cover Source")
    PLUGIN_DESC = _("Downloads covers from MusicBrainz's cover art archive.")

    @classmethod
    def group_by(cls, song):
        return song.get('musicbrainz_albumid', None)

    @staticmethod
    def priority():
        # It's a pretty good source
        return 0.65

    @property
    def cover_path(self):
        mbid = self.mbid
        if mbid is None:
            return super(MusicBrainzCover, self).cover_path
        return path.join(cover_dir, escape_filename(mbid))

    @property
    def mbid(self):
        return self.song.get('musicbrainz_albumid', None)

    @property
    def url(self):
        if not self.mbid:
            return None
        mbid = Soup.URI.encode(self.mbid, None)
        return 'https://coverartarchive.org/release/{0}/front'.format(mbid)

    def fetch_cover(self):
        if not self.mbid:
            return self.fail('MBID is required to fetch the cover')
        self.download(Soup.Message.new('GET', self.url))
