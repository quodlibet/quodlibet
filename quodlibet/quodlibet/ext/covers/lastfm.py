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
from quodlibet.util.http import download_json
from quodlibet.util.cover.http import HTTPDownloadMixin
from quodlibet.util.path import escape_filename
from quodlibet.util import print_d


class LastFMCover(CoverSourcePlugin, HTTPDownloadMixin):
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
        mbid = self.song.get('musicbrainz_albumid', None)
        # It is beneficial to use mbid for cover names.
        if mbid:
            return path.join(cover_dir, escape_filename(mbid))
        else:
            return super(LastFMCover, self).cover_path

    @property
    def url(self):
        _url = 'https://ws.audioscrobbler.com/2.0?method=album.getinfo&' + \
               'api_key=107db6fd4c1c7f53b1526fafddab2c82&format=json&' +\
               '&artist={artist}&album={album}&mbid={mbid}'
        artist = Soup.URI.encode(self.song.get('artist', ''), None)
        album = Soup.URI.encode(self.song.get('album', ''), None)
        mbid = Soup.URI.encode(self.song.get('musicbrainz_albumid', ''), None)
        if (artist and album) or mbid:
            return _url.format(artist=artist, album=album, mbid=mbid)
        else:
            return None   # Not enough data

    def search(self):
        if not self.url:
            return self.emit('search-complete', [])
        msg = Soup.Message.new('GET', self.url)
        download_json(msg, self.cancellable, self.album_data, None)

    def album_data(self, message, json, data=None):
        if not json:
            print_d('Server did not return valid JSON')
            return self.emit('search-complete', [])
        album = json.get('album', {})
        if not album:
            print_d('Album data is not available')
            return self.emit('search-complete', [])
        covers = dict((i['size'], i['#text']) for i in album['image'])
        result = []
        for ck in ('mega', 'extralarge',):
            if covers.get(ck):
                result.append({'artist': album['artist'],
                               'album': album['name'],
                               'cover': covers[ck]
                               })
        self.emit('search-complete', result)

    def fetch_cover(self):
        if not self.url:
            return self.fail('Not enough data to get cover from Last.fm')

        def search_complete(self, res):
            self.disconnect(sci)
            if res:
                self.download(Soup.Message.new('GET', res[0]['cover']))
            else:
                return self.fail('No cover was found')
        sci = self.connect('search-complete', search_complete)
        self.search()
