# Copyright 2006 Joe Wreschnig
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests import TestCase, AbstractTestCase
from helper import realized

import quodlibet.browsers

from quodlibet.formats._audio import AudioFile
from quodlibet import config
from quodlibet.browsers._base import Browser
from quodlibet.library import SongFileLibrary, SongLibrarian


SONGS = [
    AudioFile({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
    AudioFile({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
    ]
SONGS.sort()

for song in SONGS:
    song.sanitize()


class TBrowser(TestCase):
    def setUp(self):
        self.browser = Browser()

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.browser.can_filter(key))

    def test_defaults(self):
        self.failUnless(self.browser.background)
        self.failIf(self.browser.reordered)
        self.failIf(self.browser.headers)
        self.failUnless(self.browser.dynamic(None))

    def tearDown(self):
        self.browser = None


class TBrowserBase(AbstractTestCase):
    Kind = None

    def setUp(self):
        config.init()
        self.library = library = SongFileLibrary()
        library.librarian = SongLibrarian()
        library.add(SONGS)
        self.Kind.init(library)
        self.b = self.Kind(library, True)

    def tearDown(self):
        self.b.destroy()
        self.library.destroy()
        config.quit()

    def test_pack_unpack(self):
        to_pack = Gtk.Button()
        container = self.b.pack(to_pack)
        self.b.unpack(container, to_pack)

    def test_name(self):
        self.failIf("_" in self.b.name)
        self.failUnless("_" in self.b.accelerated_name)

    def test_init(self):
        self.Kind.init(self.library)

    def test_save_restore(self):
        self.b.restore()
        self.b.finalize(True)
        try:
            self.b.save()
        except NotImplementedError:
            pass

    def test_msic(self):
        with realized(self.b):
            self.b.activate()
            self.b.statusbar(1000)
            self.b.statusbar(1)
            song = AudioFile({"~filename": "/fake"})
            song.sanitize()
            self.b.scroll(song)

    def test_filters_caps(self):
        with realized(self.b):
            self.failUnless(isinstance(self.b.can_filter_tag("foo"), bool))
            self.failUnless(isinstance(self.b.can_filter_text(), bool))
            self.failUnless(isinstance(self.b.can_filter("foo"), bool))

    def test_filter_text(self):
        with realized(self.b):
            self.b.filter("foo", ["bar"])
            self.b.filter("(((((##!!!!))),", ["(((((##!!!!))),"])
            if self.b.can_filter_text():
                self.b.filter_text("foo")
                self.b.filter_text("(((((##!!!!))),,,==")

    def test_filter_albums(self):
        with realized(self.b):
            if self.b.can_filter_albums():
                self.b.filter_albums([])
                self.b.filter_albums([object])
                self.b.filter_albums(self.library.albums.values())

    def test_filter_other(self):
        with realized(self.b):
            self.b.unfilter()

# create a new test class for each browser
for browser in quodlibet.browsers.browsers:
    cls = TBrowserBase
    name = "TB" + browser.__name__
    new_test = type(name, (TBrowserBase,), {})
    new_test.Kind = browser
    globals()[name] = new_test
