# -*- coding: utf-8 -*-
from tests import TestCase

from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.player.nullbe import NullPlayer
import quodlibet.config


class TLibraryBrowser(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def test_ctr(self):
        from quodlibet.library import SongLibrary
        from quodlibet.browsers.empty import EmptyBar
        win = LibraryBrowser(EmptyBar, SongLibrary(), NullPlayer())
        win.browser.emit("songs-selected", [], False)
        win.songlist.get_selection().emit("changed")
        win.destroy()

    def test_open(self):
        from quodlibet.browsers.empty import EmptyBar
        from quodlibet.library import SongLibrary

        widget = LibraryBrowser.open(EmptyBar, SongLibrary(), NullPlayer())
        self.assertTrue(widget)
        self.assertTrue(widget.get_visible())
        widget.destroy()

    def tearDown(self):
        quodlibet.config.quit()
