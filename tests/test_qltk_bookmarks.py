# Copyright 2012 Christoph Reiter
#        2017-25 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from tests import TestCase

from quodlibet.qltk.bookmarks import EditBookmarks, MenuItems, EditBookmarksPane
from quodlibet.player.nullbe import NullPlayer
from quodlibet.library import SongLibrary
from quodlibet.formats import AudioFile
from quodlibet import config


class TBookmarks(TestCase):
    def setUp(self):
        config.init()
        player = NullPlayer()
        song = AudioFile()
        song.bookmarks = [(10, "bla")]
        song.sanitize(fsnative("/"))
        player.song = song
        self.player = player
        self.library = SongLibrary()

    def tearDown(self):
        self.player.destroy()
        config.quit()

    def test_edit_window(self):
        EditBookmarks(None, self.library, self.player).destroy()

    def test_menu_items(self):
        MenuItems(self.player.song.bookmarks, self.player, False)

    def test_add_bookmark_directly(self):
        song = self.player.song
        pane = EditBookmarksPane(None, self.library, close=True, song=song)
        model = [(31, "thirty-one seconds"), (180, b"three minutes")]
        pane._set_bookmarks(model, None, None, self.library)
        assert len(song.bookmarks) == 2
        assert song.bookmarks[1] == (180, "three minutes")
