# -*- coding: utf-8 -*-
# Copyright 2013 Simonas Kazlauskas
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import json
from os import path
from gi.repository import Soup, GLib

from quodlibet.plugins.cover import CoverSourcePlugin, cover_dir
from quodlibet.util.http import download_json
from quodlibet.util.cover.http import HTTPDownloadMixin


class LastFMCover(CoverSourcePlugin, HTTPDownloadMixin):
    PLUGIN_ID = "lastfm-cover"
    PLUGIN_NAME = _("LastFM cover source")
    PLUGIN_DESC = _("Use LastFM database to fetch covers")
    PLUGIN_VERSION = "1.0"

    @staticmethod
    def priority():
        return 0.33  # No cover size guarantee, accurate

    @property
    def cover_path(self):
        mbid = self.song.get('musicbrainz_albumid', None)
        # It is beneficial to use mbid for cover names.
        if mbid:
            return path.join(cover_dir, mbid)
        else:
            return super(LastFMCover, self).cover_path

    @property
    def url(self):
        _url = 'http://ws.audioscrobbler.com/2.0?method=album.getinfo&' + \
               'api_key=107db6fd4c1c7f53b1526fafddab2c82&format=json&' +\
               '&artist={artist}&album={album}&mbid={mbid}'
        artist = Soup.URI.encode(self.song.get('artist', ''), None)
        album = Soup.URI.encode(self.song.get('album', ''), None)
        mbid = Soup.URI.encode(self.song.get('musicbrainz_albumid', ''), None)
        if (artist and album) or mbid:
            return _url.format(artist=artist, album=album, mbid=mbid)
        else:
            return None   # Not enough data

    def fetch_cover(self):
        if not self.url:
            return self.fail('Not enough data to get cover from LastFM')
        msg = Soup.Message.new('GET', self.url)
        download_json(msg, self.cancellable, self.album_data, None)

    def album_data(self, message, json, data=None):
        if not json:
            return self.fail('Server did not return valid JSON')
        album = json.get('album', {})
        if not album:
            return self.fail('Album data is not available')
        covers = dict((i['size'], i['#text']) for i in album['image'])
        cover = covers.get('mega', covers.get('extralarge', None))
        if not cover:
            return self.fail('Satisfactory cover is not available')
        self.download(Soup.Message.new('GET', cover))
