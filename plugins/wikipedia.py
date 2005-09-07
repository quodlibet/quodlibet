# Copyright 2005 Inigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

WIKI_URL = 'http://en.wikipedia.com/wiki/'
from util import website

class WikiArtist(object):
    PLUGIN_NAME = 'Search artist in wikipedia'
    PLUGIN_DESC = 'Search artist in wikipedia'
    PLUGIN_ICON = 'gtk-open'
    PLUGIN_VERSION = '0.13'

    def plugin_songs(self, songs):
        artists = dict.fromkeys([song('artist') for song in songs]).keys()
        for artist in artists:
            artist = artist.title().replace(' ', '_')
            website(WIKI_URL + artist)

class WikiAlbum(object):
    PLUGIN_NAME = 'Search album in wikipedia'
    PLUGIN_DESC = 'Search album in wikipedia'
    PLUGIN_ICON = 'gtk-open'
    PLUGIN_VERSION = '0.1'

    def plugin_songs(self, songs):
        albums = dict.fromkeys([song('album') for song in songs]).keys()
        for album in albums:
            album = album.title().replace(' ', '_')
            website(WIKI_URL + album)
