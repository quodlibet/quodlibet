# Copyright 2017-21 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk

import quodlibet
from quodlibet import qltk
from quodlibet.browsers.playlists.menu import PlaylistMenu
from quodlibet.library.playlist import _DEFAULT_PLAYLIST_DIR, PlaylistLibrary
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrarian, SongFileLibrary
from quodlibet.library.file import FileLibrary
from tests.helper import dummy_path
from tests import TestCase, _TEMP_DIR

FIXED_NAME = "_foobar"


class StubbedPlaylistMenu(PlaylistMenu):
    def _get_new_name(self, parent, title):
        return FIXED_NAME


class TPlaylistMenu(TestCase):
    SONG = AudioFile(
        {"title": "two", "artist": "mu", "~filename": dummy_path("/dev/zero")}
    )
    SONGS = [
        AudioFile(
            {"title": "one", "artist": "piman", "~filename": dummy_path("/dev/null")}
        ),
        SONG,
    ]

    def setUp(self):
        # Testing locally is VERY dangerous without this...
        self.assertTrue(
            _TEMP_DIR in _DEFAULT_PLAYLIST_DIR or os.name == "nt",
            msg=f"Failing, don't want to delete {_DEFAULT_PLAYLIST_DIR}",
        )
        try:
            os.mkdir(_DEFAULT_PLAYLIST_DIR)
        except OSError:
            pass
        quodlibet.config.init()
        self.lib = FileLibrary()
        self.lib.librarian = SongLibrarian()
        for af in self.SONGS:
            af.sanitize()
        self.lib.add(self.SONGS)

    def tearDown(self):
        self.lib.destroy()
        self.lib.librarian.destroy()
        quodlibet.config.quit()

    def test_playlists_sort_order(self):
        pl_lib = PlaylistLibrary(SongFileLibrary())
        names = ["26-01 b", "25-12 a", "26-02 c"]
        playlists = [pl_lib.create(name) for name in names]
        try:
            for descending in (False, True):
                quodlibet.config.set(
                    "browsers", "playlists_sort_descending", str(descending).lower()
                )
                menu = PlaylistMenu(self.SONGS, pl_lib)
                labels = [
                    item.get_label()
                    for item in menu.get_children()
                    if isinstance(item, Gtk.CheckMenuItem)
                ]
                shown = [label for label in labels if label in names]
                assert shown == sorted(names, reverse=descending)
        finally:
            for pl in playlists:
                pl.delete()

    def test__on_new_playlist_activate(self):
        main = qltk.MenuItem("Menu")
        menu = StubbedPlaylistMenu(self.SONGS, PlaylistLibrary(SongFileLibrary()))
        main.set_submenu(menu)

        # Run it (with stubbed dialog)
        pl = menu._on_new_playlist_activate(main, self.SONGS)

        assert pl, "No playlists added"
        assert pl.name == FIXED_NAME, "Wrong name used"
        assert pl.songs == self.SONGS
