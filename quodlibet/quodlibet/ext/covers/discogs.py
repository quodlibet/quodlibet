# -*- coding: utf-8 -*-
# Copyright 2016 Mice Pápai
#           2018 Nick Boultbee
#
# Based on lastfm.py by Simonas Kazlauskas
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
from os import path

from gi.repository import Soup

from quodlibet import _
from quodlibet.plugins.cover import CoverSourcePlugin, cover_dir
from quodlibet.util.http import download_json
from quodlibet.util.cover.http import HTTPDownloadMixin, escape_query_value
from quodlibet.util.path import escape_filename
from quodlibet.util import print_d


class DiscogsCover(CoverSourcePlugin, HTTPDownloadMixin):
    PLUGIN_ID = "discogs-cover"
    PLUGIN_NAME = _("Discogs Cover Source")
    PLUGIN_DESC = _("Downloads covers from Discogs.")

    credentials = ('?key=aWfZGjHQvkMcreUECGAp' +
                   '&secret=VlORkklpdvAwJMwxUjNNSgqicjuizJAl')

    def pretty_json(self, json_dict):
        print_d(json.dumps(json_dict,
                           sort_keys=True,
                           indent=4,
                           separators=(',', ': ')))

    @classmethod
    def group_by(cls, song):
        return song.album_key

    @staticmethod
    def priority():
        return 0.1  # Testing version

    @property
    def cover_path(self):
        mbid = self.song.get('musicbrainz_albumid', None)
        if mbid:
            return path.join(cover_dir, escape_filename(mbid))
        else:
            return super(DiscogsCover, self).cover_path

    @property
    def url(self):
        _url = ('https://api.discogs.com/database/search' +
                self.credentials +
                '&type=release' +
                '&artist={artist}' +
                '&release_title={album}')
        artist = escape_query_value(self.song.get('artist', ''))
        album = escape_query_value(self.song.get('album', ''))
        if artist and album:
            return _url.format(artist=artist, album=album)
        else:
            return None   # Not enough data

    def search(self):
        if not self.url:
            return self.emit('search-complete', [])
        msg = Soup.Message.new('GET', self.url)
        download_json(msg, self.cancellable, self.search_data, None)

    def search_data(self, message, json_dict, data=None):
        if not json_dict:
            print_d('Server did not return valid JSON')
            return self.emit('search-complete', [])

        # debug
        # self.pretty_json(json_dict)

        try:
            res_url = json_dict.get('results', [])[0].get('resource_url', '')
        except IndexError:
            res_url = ''

        if not res_url:
            print_d('Album data is not available')
            return self.emit('search-complete', [])

        msg = Soup.Message.new('GET', res_url + self.credentials)
        download_json(msg, self.cancellable, self.album_data, None)

    def album_data(self, message, json_dict, data=None):

        # debug
        # self.pretty_json(json_dict)

        images = json_dict.get('images', '')

        if not images:
            print_d('Covers are not available')
            return self.emit('search-complete', [])

        result = []
        for cover in images:
            if cover.get('uri') and cover['type'] == 'primary':
                result.append({'cover': cover['uri']})

        self.emit('search-complete', result)

    def fetch_cover(self):
        if not self.url:
            return self.fail('Not enough data to get cover from Discogs')

        def search_complete(self, res):
            self.disconnect(sci)
            if res:
                self.download(Soup.Message.new('GET', res[0]['cover']))
            else:
                return self.fail('No cover was found')
        sci = self.connect('search-complete', search_complete)
        self.search()
