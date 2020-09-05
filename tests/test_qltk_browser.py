# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.player.nullbe import NullPlayer
import quodlibet.config


class TLibraryBrowser(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def test_ctr(self):
        from quodlibet.library import SongLibrary
        from quodlibet.browsers.albums import AlbumList
        win = LibraryBrowser(AlbumList, SongLibrary(), NullPlayer())
        win.browser.emit("songs-selected", [], False)
        win.songlist.get_selection().emit("changed")
        win.destroy()

    def test_open(self):
        from quodlibet.browsers.tracklist import TrackList
        from quodlibet.library import SongLibrary

        widget = LibraryBrowser.open(TrackList, SongLibrary(), NullPlayer())
        self.assertTrue(widget)
        self.assertTrue(widget.get_visible())
        widget.destroy()

    def tearDown(self):
        quodlibet.config.quit()
