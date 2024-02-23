# Copyright 2012,2014 Christoph Reiter
#                2016 Nick Boultbee
#                2019 Ruud van Asseldonk
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from quodlibet.browsers.covergrid.main import CoverGrid
from senf import fsnative

from . import TestCase, run_gtk_loop
from .helper import realized

from quodlibet import config

from quodlibet.browsers.albums.prefs import DEFAULT_PATTERN_TEXT
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian


SONGS = [
    AudioFile({
        "album": "one",
        "artist": "piman",
        "~filename": fsnative("/dev/null"),
    }),
    AudioFile({
        "album": "two",
        "artist": "mu",
        "~filename": fsnative("/dev/zero"),
    }),
    AudioFile({
        "album": "three",
        "artist": "boris",
        "~filename": fsnative("/bin/ls"),
    }),
    AudioFile({
        "album": "three",
        "artist": "boris",
        "~filename": fsnative("/bin/ls2"),
    }),
]
SONGS.sort()


class TCoverGridBrowser(TestCase):

    def setUp(self):
        config.init()

        library = SongLibrary()
        library.librarian = SongLibrarian()
        CoverGrid.init(library)

        for af in SONGS:
            af.sanitize()
        library.add(SONGS)

        self.bar = CoverGrid(library)

        self._id = self.bar.connect("songs-selected", self._selected)
        self._id2 = self.bar.connect("songs-activated", self._activated)
        with realized(self.bar):
            self.bar.filter_text("")
            self._wait()
        self.songs = []
        self.activated = False

    def tearDown(self):
        self.bar.disconnect(self._id)
        self.bar.disconnect(self._id2)
        self.bar.destroy()
        del self.bar
        config.quit()

    def _activated(self, albumlist):
        self.activated = True

    def _selected(self, albumlist, songs, *args):
        self.songs = songs

    def _wait(self):
        run_gtk_loop()

    def test_activated(self):
        with realized(self.bar):
            view = self.bar.view
            child = view.get_child_at_index(0)
            child.emit("activate")
            self._wait()
            self.assertTrue(self.activated)

    def test_can_filter(self):
        with realized(self.bar):
            self.assertTrue(self.bar.can_filter(None))
            self.assertTrue(self.bar.can_filter("album"))
            self.assertTrue(self.bar.can_filter("foobar"))
            self.assertFalse(self.bar.can_filter("~#length"))
            self.assertFalse(self.bar.can_filter("title"))

    def test_set_text(self):
        with realized(self.bar):
            self.bar.filter_text("artist=piman")
            self._wait()
            self.assertEqual(len(self.songs), 1)
            self.bar.filter_text("")
            self._wait()
            self.assertEqual(set(self.songs), set(SONGS))

    def test_filter_album(self):
        with realized(self.bar):
            self.bar.filter_text("dsagfsag")
            self._wait()
            self.assertEqual(len(self.songs), 0)
            self.bar.filter_text("")
            self._wait()
            self.bar.filter("album", ["one", "three"])
            self._wait()
            self.assertEqual(len(self.songs), 3)

    def test_filter_artist(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            self.assertEqual(len(self.songs), 1)
            self.assertEqual(self.songs[0]("artist"), "piman")

    def test_header(self):
        self.assertFalse(self.bar.headers)

    def test_list(self):
        albums = self.bar.list_albums()
        self.assertEqual(set(albums), {s.album_key for s in SONGS})
        self.bar.filter_albums([SONGS[0].album_key])
        self._wait()
        self.assertEqual({s.album_key for s in self.songs},
                             {SONGS[0].album_key})

    def test_active_filter(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            self.assertTrue(self.bar.active_filter(self.songs[0]))
            for s in SONGS:
                if s is not self.songs[0]:
                    self.assertFalse(self.bar.active_filter(s))

    def test_default_display_pattern(self):
        pattern_text = self.bar.display_pattern_text
        self.assertEqual(pattern_text, DEFAULT_PATTERN_TEXT)
        self.assertTrue("<album>" in pattern_text)
