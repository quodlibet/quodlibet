# -*- coding: utf-8 -*-
# Copyright 2018 Phidica Veia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sqlite3

from gi.repository import Gtk
from senf import uri2fsn

from quodlibet import _
from quodlibet import app
from quodlibet import util
from quodlibet.qltk import Icons
from quodlibet.qltk.msg import WarningMessage, ErrorMessage
from quodlibet.util.path import expanduser, normalize_path
from quodlibet.plugins.events import EventPlugin


class BansheeDBImporter:

    def __init__(self, library):

        self._library = library
        self._changed_songs = []

    def read(self, db):
        """Iterate through the database and import data for songs found in
        the library
        """

        # use the Row class for extracting rows
        db.row_factory = sqlite3.Row

        # iterate over all songs in the database
        for row in db.execute("SELECT * FROM CoreTracks"):
            try:
                filename = uri2fsn(row["Uri"])
            except ValueError:
                continue

            song = self._library.get(normalize_path(filename))
            if not song:
                continue

            has_changed = False

            if row["Rating"] is not None:
                try:
                    # banshee stores ratings as integers up to 5
                    value = row["Rating"] / 5.0
                except ValueError:
                    pass
                else:
                    song["~#rating"] = value
                    has_changed = True

            if row["PlayCount"] is not None:
                # summing play counts would break on multiple imports
                song["~#playcount"] = row["PlayCount"]
                has_changed = True

            if row["SkipCount"] is not None:
                song["~#skipcount"] = row["SkipCount"]
                has_changed = True

            if row["LastPlayedStamp"] is not None:
                value = row["LastPlayedStamp"]
                # keep timestamp if it is newer than what we had
                if value > song("~#lastplayed", 0):
                    song["~#lastplayed"] = value
                    has_changed = True

            if row["DateAddedStamp"] is not None:
                value = row["DateAddedStamp"]
                # keep timestamp if it is older than what we had
                if value < song("~#added", 0):
                    song["~#added"] = value
                    has_changed = True

            if has_changed:
                self._changed_songs.append(song)

    def finish(self):
        """Call at the end, also returns number of songs with data imported"""

        count = len(self._changed_songs)
        self._library.changed(self._changed_songs)
        self._changed_songs = []
        return count


def do_import(parent, library):
    db_path = expanduser("~/.config/banshee-1/banshee.db")
    msg = _("test db path %s") % db_path
    # FIXME: this is just a warning so it works with older QL
    WarningMessage(parent, BansheeImport.PLUGIN_NAME, msg).run()


class BansheeImport(EventPlugin):
    PLUGIN_ID = "bansheeimport"
    PLUGIN_NAME = _("Banshee Import")
    PLUGIN_DESC = _("Imports ratings and song statistics from Banshee.")
    PLUGIN_ICON = Icons.DOCUMENT_OPEN

    def PluginPreferences(self, *args):
        button = Gtk.Button(label=_("Start Import"))

        def clicked_cb(button):
            do_import(button, app.library)

        button.connect("clicked", clicked_cb)
        return button
