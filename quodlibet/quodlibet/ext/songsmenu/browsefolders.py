# -*- coding: utf-8 -*-
# Copyright 2012,2016 Nick Boultbee
#           2012,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.plugins.songshelpers import any_song, is_a_file

try:
    import dbus
except ImportError:
    dbus = None

from quodlibet import _
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk import Icons
from quodlibet.qltk.showfiles import show_files
from quodlibet.util.dprint import print_d


def show_songs(songs):
    """Returns False if showing any of them failed"""

    dirs = {}
    for s in songs:
        dirs.setdefault(s("~dirname"), []).append(s("~basename"))

    for dirname, entries in sorted(dirs.items()):
        status = show_files(dirname, entries)
        if not status:
            return False
    return True


class BrowseFolders(SongsMenuPlugin):
    PLUGIN_ID = 'Browse Folders'
    PLUGIN_NAME = _('Browse Folders')
    PLUGIN_DESC = _("Opens the songs' folders in a file manager.")
    PLUGIN_ICON = Icons.DOCUMENT_OPEN

    def plugin_songs(self, songs):
        songs = [s for s in songs if s.is_file]
        print_d("Trying to browse folders...")
        if not show_songs(songs):
            ErrorMessage(self.plugin_window,
                         _("Unable to open folders"),
                         _("No program available to open folders.")).run()

    plugin_handles = any_song(is_a_file)
    """By default, any single song being a file is good enough"""
