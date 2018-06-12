# -*- coding: utf-8 -*-
# Copyright 2005 Inigo Serna
#           2018 Phoenix Dailey
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import config
from quodlibet.util import website
from quodlibet.qltk.entry import Entry
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.compat import quote

WIKI_URL = "https://%s.wikipedia.org/wiki/Special:Search/"


def get_lang():
    return config.get("plugins", __name__, "en")


def set_lang(value):
    config.set("plugins", __name__, value)


class WikiSearch(object):
    PLUGIN_ICON = Icons.APPLICATION_INTERNET

    @classmethod
    def changed(self, e):
        set_lang(e.get_text())

    @classmethod
    def PluginPreferences(self, parent):
        hb = Gtk.HBox(spacing=3)
        hb.set_border_width(6)
        e = Entry(max_length=2)
        e.set_width_chars(3)
        e.set_max_width_chars(3)
        e.set_text(get_lang())
        e.connect('changed', self.changed)
        hb.pack_start(
            Gtk.Label(label=_("Search at %(website)s") % {
                "website": "https://"}),
            False, True, 0)
        hb.pack_start(e, False, True, 0)
        hb.pack_start(Gtk.Label(label=".wikipedia.org"), False, True, 0)
        hb.show_all()
        return hb

    def plugin_songs(self, songs):
        l = dict.fromkeys([song(self.k) for song in songs]).keys()
        for a in l:
            a = quote(str(a).title().replace(' ', '_'))
            website(WIKI_URL % get_lang() + a)


class WikiArtist(WikiSearch, SongsMenuPlugin):
    PLUGIN_ID = 'Search artist in Wikipedia'
    PLUGIN_NAME = _('Search Artist in Wikipedia')
    PLUGIN_DESC = _("Opens a browser window with the Wikipedia article "
                    "on the playing song's artist.")
    k = 'artist'


class WikiAlbum(WikiSearch, SongsMenuPlugin):
    PLUGIN_ID = 'Search album in Wikipedia'
    PLUGIN_NAME = _('Search Album in Wikipedia')
    PLUGIN_DESC = _("Opens a browser window with the Wikipedia article "
                    "on the playing song's album.")
    k = 'album'


class WikiComposer(WikiSearch, SongsMenuPlugin):
    PLUGIN_ID = 'Search composer in Wikipedia'
    PLUGIN_NAME = _('Search Composer in Wikipedia')
    PLUGIN_DESC = _("Opens a browser window with the Wikipedia article "
                    "on the playing song's composer.")
    k = 'composer'
