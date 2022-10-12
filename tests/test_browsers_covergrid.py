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
        "~filename": fsnative(u"/dev/null"),
    }),
    AudioFile({
        "album": "two",
        "artist": "mu",
        "~filename": fsnative(u"/dev/zero"),
    }),
    AudioFile({
        "album": "three",
        "artist": "boris",
        "~filename": fsnative(u"/bin/ls"),
    }),
    AudioFile({
        "album": "three",
        "artist": "boris",
        "~filename": fsnative(u"/bin/ls2"),
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
            child.emit('activate')
            self._wait()
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
        self.failUnlessEqual(set(albums), {s.album_key for s in SONGS})
        self.bar.filter_albums([SONGS[0].album_key])
        self._wait()
        self.failUnlessEqual({s.album_key for s in self.songs},
                             {SONGS[0].album_key})

    def test_active_filter(self):
        with realized(self.bar):
            self.bar.filter("artist", ["piman"])
            self._wait()
            self.failUnless(self.bar.active_filter(self.songs[0]))
            for s in SONGS:
                if s is not self.songs[0]:
                    self.failIf(self.bar.active_filter(s))

    def test_default_display_pattern(self):
        pattern_text = self.bar.display_pattern_text
        self.failUnlessEqual(pattern_text, DEFAULT_PATTERN_TEXT)
        self.failUnless("<album>" in pattern_text)
