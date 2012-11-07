# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from tests import TestCase, add

from quodlibet import config

from quodlibet.browsers.albums import AlbumList
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian

SONGS = [
    AudioFile({"album": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"album": "two", "artist": "mu", "~filename": "/dev/zero"}),
    AudioFile({"album": "three", "artist": "boris", "~filename": "/bin/ls"}),
    AudioFile({"album": "three", "artist": "boris", "~filename": "/bin/ls2"}),
    ]
SONGS.sort()

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
        w = gtk.Window()
        w.add(self.bar)
        w.show_all()
        w.hide()
        self.w = w

        self._id = self.bar.connect("songs-selected", self._selected)
        self._id2 = self.bar.connect("activated", self._activated)
        self.bar.filter_text("")
        self._wait()
        self.songs = []
        self.activated = False

    def _activated(self, albumlist):
        self.activated = True

    def _selected(self, albumlist, songs, *args):
        self.songs = songs

    def _wait(self):
        while gtk.events_pending():
            gtk.main_iteration()

    def test_activated(self):
        view = self.bar.view
        view.row_activated((0,), view.get_column(0))
        self.failUnless(self.activated)

    def test_can_filter(self):
        self.failUnless(self.bar.can_filter(None))
        self.failUnless(self.bar.can_filter("album"))
        self.failUnless(self.bar.can_filter("foobar"))
        self.failIf(self.bar.can_filter("~#length"))
        self.failIf(self.bar.can_filter("title"))

    def test_set_text(self):
        self.bar.filter_text("artist=piman")
        self._wait()
        self.failUnlessEqual(len(self.songs), 1)
        self.bar.filter_text("")
        self._wait()
        self.failUnlessEqual(set(self.songs), set(SONGS))

    def test_filter_album(self):
        self.bar.filter_text("dsagfsag")
        self._wait()
        self.failUnlessEqual(len(self.songs), 0)
        self.bar.filter_text("")
        self._wait()
        self.bar.filter("album", ["one", "three"])
        self._wait()
        self.failUnlessEqual(len(self.songs), 3)

    def test_filter_artist(self):
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
        self.bar.filter("artist", ["piman"])
        self._wait()
        self.failUnless(self.bar.active_filter(self.songs[0]))
        for s in SONGS:
            if s is not self.songs[0]:
                self.failIf(self.bar.active_filter(s))

    def tearDown(self):
        self.bar.disconnect(self._id)
        self.bar.disconnect(self._id2)
        self.w.destroy()
        config.quit()

add(TAlbumBrowser)
