# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet import app
from quodlibet import browsers
from quodlibet.plugins.songshelpers import any_song, is_a_file
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class FilterBrowser(SongsMenuPlugin):
    PLUGIN_ID = 'filterbrowser'
    PLUGIN_NAME = _('Filter on Directory')
    PLUGIN_DESC = _("Filters on directory in a new browser window.")
    PLUGIN_ICON = Icons.EDIT_SELECT_ALL

    plugin_handles = any_song(is_a_file)

    def plugin_songs(self, songs):
        tag = "~dirname"

        values = []
        for song in songs:
            values.extend(song.list(tag))

        browser = LibraryBrowser.open(
            browsers.get("SearchBar"), app.library, app.player)
        browser.browser.filter(tag, set(values))
