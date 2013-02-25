# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import app
from quodlibet import browsers
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class FilterBrowser(SongsMenuPlugin):
    PLUGIN_ID = 'filterbrowser'
    PLUGIN_NAME = _('Filter on Directory')
    PLUGIN_DESC = _("Filter on directory in a new browser window.")
    PLUGIN_ICON = Gtk.STOCK_INDEX
    PLUGIN_VERSION = '0.1'

    def plugin_songs(self, songs):
        tag = "~dirname"

        values = []
        for song in songs:
            values.extend(song.list(tag))

        browser = LibraryBrowser(browsers.get("SearchBar"), app.library)
        browser.browser.filter(tag, set(values))
