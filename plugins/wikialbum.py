# Copyright 2005 Inigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

PLUGIN_NAME = 'Search album in wikipedia'
PLUGIN_DESC = 'Search album in wikipedia'
PLUGIN_ICON = 'gtk-open'
PLUGIN_VERSION = '0.1'


WIKI_URL = 'http://en.wikipedia.com/wiki/'

import webbrowser

def plugin_songs(songs):
    albums = dict.fromkeys([song('album') for song in songs]).keys()
    for album in albums:
        album = album.title().replace(' ', '_')
        webbrowser.open_new(WIKI_URL + album)
