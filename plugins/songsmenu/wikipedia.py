# Copyright 2005 Inigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

WIKI_URL = "http://%s.wikipedia.org/wiki/"
from util import website
from urllib import quote
import gtk, config

try: config.get("plugins", __name__)
except: config.set("plugins", __name__, "en")

from plugins.songsmenu import SongsMenuPlugin

class WikiSearch(object):
    PLUGIN_ICON = gtk.STOCK_OPEN
    PLUGIN_VERSION = '0.14'

    def changed(self, e):
        config.set("plugins", __name__, e.get_text())
    changed = classmethod(changed)

    def PluginPreferences(self, parent):
        hb = gtk.HBox(spacing=3)
        hb.set_border_width(6)
        e = gtk.Entry(2)
        e.set_property('width-request', 25)
        e.set_text(config.get('plugins', __name__))
        e.connect('changed', self.changed)
        hb.pack_start(gtk.Label("Search at http://"), expand=False)
        hb.pack_start(e, expand=False)
        hb.pack_start(gtk.Label(".wikipedia.org"), expand=False)
        hb.show_all()
        return hb
    PluginPreferences = classmethod(PluginPreferences)

    def plugin_songs(self, songs):
        l = dict.fromkeys([song(self.k) for song in songs]).keys()
        for a in l:
            a = quote(str(a).title().replace(' ', '_'))
            website(WIKI_URL % config.get('plugins', __name__) + a)

class WikiArtist(WikiSearch, SongsMenuPlugin):
    PLUGIN_ID = 'Search artist in Wikipedia'
    PLUGIN_NAME = _('Search artist in Wikipedia')
    k = 'artist'

class WikiAlbum(WikiSearch, SongsMenuPlugin):
    PLUGIN_ID = 'Search album in Wikipedia'
    PLUGIN_NAME = _('Search album in Wikipedia')
    k = 'album'
