# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import quodlibet.config
from quodlibet.browsers.albums import AlbumList
from quodlibet.browsers.tracks import TrackList
from quodlibet.library import SongLibrarian, SongLibrary
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.browser import LibraryBrowser
from tests import TestCase


class TLibraryBrowser(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.library = SongLibrary()

    def test_ctr(self):
        win = LibraryBrowser(AlbumList, self.library, NullPlayer())
        win.browser.emit("songs-selected", [], False)
        win.songlist.get_selection().emit("changed")
        win.destroy()

    def test_open(self):
        self.library.librarian = SongLibrarian()
        widget = LibraryBrowser.open(TrackList, self.library, NullPlayer())
        self.assertTrue(widget)
        self.assertTrue(widget.get_visible())
        widget.destroy()

    def tearDown(self):
        self.library.destroy()
        quodlibet.config.quit()
