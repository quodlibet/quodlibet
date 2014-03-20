# Copyright 2012,2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests import TestCase
from helper import realized

from quodlibet import config

from quodlibet.browsers.albums import AlbumList
from quodlibet.browsers.albums.prefs import Preferences, FakeAlbum
from quodlibet.browsers.albums.main import (compare_title, compare_artist,
    compare_genre, compare_rating, compare_date)
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian
from quodlibet.util.collection import Album

SONGS = [
    AudioFile({"album": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"album": "two", "artist": "mu", "~filename": "/dev/zero"}),
    AudioFile({"album": "three", "artist": "boris", "~filename": "/bin/ls"}),
    AudioFile({"album": "three", "artist": "boris", "~filename": "/bin/ls2"}),
    ]
SONGS.sort()


class TAlbumPrefs(TestCase):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_main(self):

        class Browser(Gtk.Box):
            _pattern_text = ""

        widget = Preferences(Browser())
        widget.destroy()


class TAlbumSort(TestCase):

    def _get_album(self, dict_):
        song = AudioFile(dict_)
        album = Album(song)
        album.songs.add(song)
        return album

    def assertOrder(self, func, list_):
        # sort twice for full line coverage of the compare function
        reversed_ = list(sorted(list_, cmp=func, reverse=True))
        sorted_ = list(sorted(list_, cmp=func))
        self.assertEqual(reversed_[::-1], sorted_)
        self.assertEqual(list_, sorted_)

    def test_sort_title(self):
        a = self._get_album({"album": "a"})
        b = self._get_album({"album": "b"})
        n = self._get_album({"album": ""})

        self.assertOrder(compare_title, [None, a, b, n])

    def test_sort_artist(self):
        a = self._get_album({"album": "b", "artist": "x"})
        b = self._get_album({"album": "a", "artist": "y"})
        c = self._get_album({"album": "a", "artist": ""})
        n = self._get_album({"album": ""})

        self.assertOrder(compare_artist, [None, a, b, c, n])

    def test_sort_genre(self):
        a = self._get_album({"album": "b", "genre": "x"})
        b = self._get_album({"album": "a", "genre": "y"})
        c = self._get_album({"album": "a", "genre": ""})
        n = self._get_album({"album": ""})

        self.assertOrder(compare_genre, [None, a, b, c, n])

    def test_sort_date(self):
        a = self._get_album({"album": "b", "date": "1970"})
        b = self._get_album({"album": "a", "date": "2038"})
        c = self._get_album({"album": "a", "date": ""})
        n = self._get_album({"album": ""})

        self.assertOrder(compare_date, [None, a, b, c, n])

    def test_sort_rating(self):
        a = self._get_album({"album": "b", "~#rating": 0.5})
        b = self._get_album({"album": "a", "~#rating": 0.25})
        c = self._get_album({"album": "x", "~#rating": 0.0})
        n = self._get_album({"album": "", "~#rating": 0.25})

        self.assertOrder(compare_rating, [None, a, b, c, n])


class TFakeAlbum(TestCase):

    def test_call(self):
        self.assertEqual(FakeAlbum()("title"), "Title")
        self.assertEqual(FakeAlbum()("~title~artist"), "Title - Artist")
        self.assertEqual(FakeAlbum(title="foo")("title"), "foo")
        self.assertEqual(FakeAlbum(title="f")("~title~artist"), "f - Artist")
        self.assertEqual(FakeAlbum()("~#rating"), "Rating")
        self.assertEqual(FakeAlbum({"~#rating": 0.5})("~#rating"), 0.5)
        self.assertEqual(FakeAlbum()("~#rating:max"), "Rating<max>")

    def test_get(self):
        self.assertEqual(FakeAlbum().get("title"), "Title")

    def test_comma(self):
        self.assertEqual(FakeAlbum().comma("title"), "Title")
        self.assertEqual(FakeAlbum({"~#rating": 0.5}).comma("~#rating"), 0.5)
        self.assertEqual(FakeAlbum(title="a\nb").comma("title"), "a, b")


class TAlbumBrowser(TestCase):

    def setUp(self):
        config.init()

        library = SongLibrary()
        library.librarian = SongLibrarian()
        AlbumList.init(library)

        for af in SONGS:
            af.sanitize()
        library.add(SONGS)

        self.bar = AlbumList(library, True)

        self._id = self.bar.connect("songs-selected", self._selected)
        self._id2 = self.bar.connect("activated", self._activated)
        with realized(self.bar):
            self.bar.filter_text("")
            self._wait()
        self.songs = []
        self.activated = False

    def _activated(self, albumlist):
        self.activated = True

    def _selected(self, albumlist, songs, *args):
        self.songs = songs

    def _wait(self):
        while Gtk.events_pending():
            Gtk.main_iteration()

    def test_activated(self):
        with realized(self.bar):
            view = self.bar.view
            view.row_activated(Gtk.TreePath((0,)), view.get_column(0))
            self.failUnless(self.activated)

    def test_can_filter(self):
        with realized(self.bar):
            self.failUnless(self.bar.can_filter(None))
            self.failUnless(self.bar.can_filter("album"))
            self.failUnless(self.bar.can_filter("foobar"))
            self.failIf(self.bar.can_filter("~#length"))
            self.failIf(self.bar.can_filter("title"))

    def test_set_text(self):
        with realized(self.bar):
            self.bar.filter_text("artist=piman")
            self._wait()
            self.failUnlessEqual(len(self.songs), 1)
            self.bar.filter_text("")
            self._wait()
            self.failUnlessEqual(set(self.songs), set(SONGS))

    def test_filter_album(self):
        with realized(self.bar):
            self.bar.filter_text("dsagfsag")
            self._wait()
            self.failUnlessEqual(len(self.songs), 0)
            self.bar.filter_text("")
            self._wait()
            self.bar.filter("album", ["one", "three"])
            self._wait()
            self.failUnlessEqual(len(self.songs), 3)

    def test_filter_artist(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            self.failUnlessEqual(len(self.songs), 1)
            self.failUnlessEqual(self.songs[0]("artist"), "piman")

    def test_header(self):
        self.failIf(self.bar.headers)

    def test_list(self):
        albums = self.bar.list_albums()
        self.failUnlessEqual(set(albums), set([s.album_key for s in SONGS]))
        self.bar.filter_albums([SONGS[0].album_key])
        self._wait()
        self.failUnlessEqual(set([s.album_key for s in self.songs]),
                             set([SONGS[0].album_key]))

    def test_active_filter(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            self.failUnless(self.bar.active_filter(self.songs[0]))
            for s in SONGS:
                if s is not self.songs[0]:
                    self.failIf(self.bar.active_filter(s))

    def tearDown(self):
        self.bar.disconnect(self._id)
        self.bar.disconnect(self._id2)
        config.quit()
