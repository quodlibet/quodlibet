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
from quodlibet import qltk
from quodlibet import ngettext
from quodlibet import util
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons
from quodlibet.qltk.msg import Message, WarningMessage, ErrorMessage
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
        # throws sqlite3.OperationalError if CoreTracks is not found
        for row in db.execute("SELECT * FROM CoreTracks"):
            try:
                filename = uri2fsn(row["Uri"])
            except ValueError:
                continue

            song = self._library.get(normalize_path(filename))
            if not song:
                continue

            has_changed = False

            # rating is stored as integer from 0 to 5
            b_rating = row["Rating"] / 5.0
            if b_rating != song("~#rating"):
                song["~#rating"] = b_rating
                has_changed = True

            # play count is stored as integer from 0
            if row["PlayCount"] != song("~#playcount"):
                # summing play counts would break on multiple imports
                song["~#playcount"] = row["PlayCount"]
                has_changed = True

            # skip count is stored as integer from 0
            if row["SkipCount"] != song("~#skipcount"):
                song["~#skipcount"] = row["SkipCount"]
                has_changed = True

            # timestamp is stored as integer or None
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
    db_path = expanduser(BansheeImport.USR_PATH)
    db = sqlite3.connect(db_path)

    importer = BansheeDBImporter(library)
    try:
        importer.read(db)
    except sqlite3.OperationalError:
        msg = _("Specified Banshee database is malformed or missing")
        WarningMessage(parent, BansheeImport.PLUGIN_NAME, msg).run()
    except Exception:
        util.print_exc()
        importer.finish()
        msg = _("Import Failed")
        # FIXME: don't depend on the plugin class here
        ErrorMessage(parent, BansheeImport.PLUGIN_NAME, msg).run()
    else:
        count = importer.finish()
        preamble = "Successfully imported ratings and statistics for "
        msg = ngettext(preamble + "%d song", preamble + "%d songs",
                       count) % count
        Message(Gtk.MessageType.INFO, parent, BansheeImport.PLUGIN_NAME,
                msg).run()

    db.close()


class BansheeImport(EventPlugin):
    PLUGIN_ID = "bansheeimport"
    PLUGIN_NAME = _("Banshee Import")
    PLUGIN_DESC = _("Imports ratings and song statistics from Banshee.")
    PLUGIN_ICON = Icons.DOCUMENT_OPEN

    DEF_PATH = "~/.config/banshee-1/banshee.db"
    USR_PATH = DEF_PATH

    def PluginPreferences(self, *args):
        grid = Gtk.Grid(row_spacing=6, column_spacing=6)

        label = Gtk.Label(label=_("_Database path:"), use_underline=True)
        label.set_alignment(0.0, 0.5)
        grid.attach(label, 0, 0, 1, 1)

        entry = UndoEntry()
        entry.set_hexpand(True)
        entry.set_text(BansheeImport.DEF_PATH)

        def path_activate(entry, *args):
            path = entry.get_text()
            if BansheeImport.USR_PATH != path:
                BansheeImport.USR_PATH = path

        entry.connect_after("activate", path_activate)
        entry.connect_after("focus-out-event", path_activate)
        grid.attach_next_to(entry, label, Gtk.PositionType.RIGHT, 1, 1)

        path_revert = Gtk.Button()
        path_revert.add(Gtk.Image.new_from_icon_name(
                        Icons.DOCUMENT_REVERT, Gtk.IconSize.MENU))

        def path_revert_cb(button, entry):
            entry.set_text(BansheeImport.DEF_PATH)
            entry.emit("activate")

        path_revert.connect("clicked", path_revert_cb, entry)
        grid.attach_next_to(path_revert, entry, Gtk.PositionType.RIGHT, 1, 1)

        button = Gtk.Button(label=_("Start Import"))

        def clicked_cb(button):
            do_import(button, app.library)

        button.connect("clicked", clicked_cb)

        box = Gtk.VBox(spacing=12)

        box.pack_start(grid, True, True, 0)
        box.pack_start(button, False, False, 0)

        return box
