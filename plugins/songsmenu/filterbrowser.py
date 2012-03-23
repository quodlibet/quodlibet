# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet import browsers
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.plugins.songsmenu import SongsMenuPlugin

class FilterBrowser(SongsMenuPlugin):
    PLUGIN_ID = 'filterbrowser'
    PLUGIN_NAME = _('Filter on Directory')
    PLUGIN_DESC = _("Filter on directory in a new browser window.")
    PLUGIN_ICON = gtk.STOCK_INDEX
    PLUGIN_VERSION = '0.1'

    def plugin_songs(self, songs):
        tag = "~dirname"

        values = []
        for song in songs:
            values.extend(song.list(tag))

        from quodlibet.library import library
        browser = LibraryBrowser(browsers.get("SearchBar"), library)
        browser.browser.filter(tag, set(values))
