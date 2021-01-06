# Copyright 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import quodlibet
from quodlibet import qltk
from quodlibet.browsers.playlists.menu import PlaylistMenu
from quodlibet.browsers.playlists.util import PLAYLISTS
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrarian
from quodlibet.library.file import FileLibrary
from tests.helper import dummy_path
from tests import TestCase, _TEMP_DIR

FIXED_NAME = "_foobar"


class StubbedPlaylistMenu(PlaylistMenu):

    def _get_new_name(self, parent, title):
        return FIXED_NAME


class TPlaylistMenu(TestCase):
    SONG = AudioFile({
        "title": "two",
        "artist": "mu",
        "~filename": dummy_path(u"/dev/zero")})
    SONGS = [
        AudioFile({
            "title": "one",
            "artist": "piman",
            "~filename": dummy_path(u"/dev/null")}),
        SONG,
    ]

    def setUp(self):
        # Testing locally is VERY dangerous without this...
        self.assertTrue(_TEMP_DIR in PLAYLISTS or os.name == "nt",
                        msg="Failing, don't want to delete %s" % PLAYLISTS)
        try:
            os.mkdir(PLAYLISTS)
        except EnvironmentError:
            pass
        quodlibet.config.init()
        self.lib = FileLibrary()
        self.lib.librarian = SongLibrarian()
        for af in self.SONGS:
            af.sanitize()
        self.lib.add(self.SONGS)
        self.added = []

    def tearDown(self):
        self.lib.destroy()
        self.lib.librarian.destroy()
        quodlibet.config.quit()

    def _on_new(self, _, playlist):
        self.added.append(playlist)

    def test__on_new_playlist_activate(self):
        main = qltk.MenuItem('Menu')
        menu = StubbedPlaylistMenu(self.SONGS, [])
        menu.connect('new', self._on_new)
        main.set_submenu(menu)

        menu._on_new_playlist_activate(main, self.SONGS)

        self.failUnless(self.added, msg="No playlists signalled")
        self.failUnlessEqual(self.added[0].songs, self.SONGS)
        self.added[0].delete()
