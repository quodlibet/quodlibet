# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import app
from quodlibet.browsers.albums import AlbumList
from quodlibet.browsers.tracks import TrackList
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrarian
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.songlist import SongList
from tests import TestCase, init_fake_app, destroy_fake_app


class TLibraryBrowser(TestCase):
    def setUp(self):
        init_fake_app()
        self.library = app.library

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

    def test_popup_menu(self):
        self.library.librarian = SongLibrarian()
        widget = LibraryBrowser.open(TrackList, self.library, NullPlayer())
        songlist: SongList = widget.songlist
        widget.songlist.set_column_headers(["artist"])
        a_song = AudioFile({"~filename": "/dev/null"})
        songlist.add_songs([a_song])
        songlist.set_cursor(Gtk.TreePath(0), widget.songlist.get_columns()[0])
        called = []
        songlist.popup_menu = lambda *args: called.append(args)
        widget._menu(songlist, self.library)
        assert len(called) == 1, "Should have called menu once"
        assert len(called[0][0].get_children()) > 6, "doesn't seem enough items"

    def tearDown(self):
        destroy_fake_app()
