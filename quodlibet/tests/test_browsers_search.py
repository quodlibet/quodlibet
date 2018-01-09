# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from gi.repository import Gtk
from senf import fsnative

import quodlibet.browsers.search
import quodlibet.config

from quodlibet.browsers.search import SearchBar
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian
from quodlibet.qltk.songlist import SongList

# Don't sort yet, album_key makes it complicated...
SONGS = [AudioFile({
                "title": "one",
                "artist": "piman",
                "~filename": fsnative(u"/dev/null")}),
         AudioFile({
                "title": "two",
                "artist": "mu",
                "~#length": 234,
                "~filename": fsnative(u"/dev/zero")}),
         AudioFile({
                "title": "three",
                "artist": "boris",
                "~filename": fsnative(u"/bin/ls")}),
         AudioFile({
                "title": "four",
                "artist": "random",
                "album": "don't stop",
                "labelid": "65432-1",
                "~filename": fsnative(u"/dev/random")}),
         AudioFile({
                "title": "five € and a £",
                "artist": "shell",
                "album": "don't stop",
                "labelid": "12345-6",
                "~filename": fsnative(u"/tmp/five € and £!")})]


class TSearchBar(TestCase):
    Bar = SearchBar

    def setUp(self):
        quodlibet.config.init()
        quodlibet.browsers.search.library = SongLibrary()
        quodlibet.browsers.search.library.librarian = SongLibrarian()
        for af in SONGS:
            af.sanitize()
        quodlibet.browsers.search.library.add(SONGS)
        self.bar = self.Bar(quodlibet.browsers.search.library)
        self.bar.connect('songs-selected', self._expected)
        self.success = False

    def _expected(self, bar, songs, sort):
        songs.sort()
        self.failUnlessEqual(self.expected, songs)
        self.success = True

    def _do(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.failUnless(self.success or self.expected is None)

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failUnless(self.bar.can_filter(key))

    def test_empty_is_all(self):
        self.bar.filter_text("")
        self.expected = list(sorted(SONGS))
        self._do()

    def test_active_filter(self):
        self.assertTrue(self.bar.active_filter(SONGS[0]))
        self.bar.filter_text("this does not match any song")
        self.expected = []
        self.assertFalse(self.bar.active_filter(SONGS[0]))
        self._do()

    def test_filter(self):
        self.expected = [SONGS[1]]
        self.bar.filter("title", ["two"])
        self._do()

    def test_filter_again(self):
        self.expected = sorted(SONGS[3:5])
        self.bar.filter("album", ["don't stop"])
        self._do()

    def test_filter_notvalue(self):
        self.expected = sorted(SONGS[0:2])
        self.bar.filter("artist", ["notvalue", "mu", "piman"])
        self._do()

    def test_filter_none(self):
        self.expected = []
        self.bar.filter("title", ["not a value"])
        self._do()

    def test_filter_album_by_labelid(self):
        self.expected = [SONGS[3]]
        self.bar.filter("labelid", [("65432-1")])
        self._do()

    def test_filter_numeric(self):
        self.expected = sorted([SONGS[0]] + SONGS[2:])
        self.bar.filter("~#length", [0])
        self._do()

    def test_search_text_artist(self):
        self.bar._set_text("boris")
        self.expected = [SONGS[2]]
        self.bar._sb_box.changed()
        self._do()

    def test_search_text_custom_star(self):
        old = SongList.star
        SongList.star = ["artist", "labelid"]
        self.bar._set_text("65432-1")
        self.expected = [SONGS[3]]
        self.bar._sb_box.changed()
        try:
            self._do()
        finally:
            SongList.star = old

    def test_saverestore(self):
        self.bar.filter_text("title = %s" % SONGS[0]["title"])
        self.expected = [SONGS[0]]
        self._do()
        self.bar.save()
        self.bar.filter_text("")
        self.expected = list(sorted(SONGS))
        self._do()
        self.bar.restore()
        self.bar.activate()
        self.expected = [SONGS[0]]
        self._do()

    def tearDown(self):
        self.bar.destroy()
        quodlibet.browsers.search.library.destroy()
        quodlibet.config.quit()
