# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests import TestCase, init_fake_app, destroy_fake_app
from helper import realized, dummy_path

from quodlibet import browsers
from quodlibet.formats import AudioFile
from quodlibet import config
from quodlibet.browsers import Browser
from quodlibet.library import SongFileLibrary, SongLibrarian


SONGS = [
    AudioFile({
        "title": "one",
        "artist": "piman",
        "~filename": dummy_path(u"/dev/null"),
    }),
    AudioFile({
        "title": "two",
        "artist": "mu",
        "~filename": dummy_path(u"/dev/zero"),
    }),
    AudioFile({
        "title": "three",
        "artist": "boris",
        "~filename": dummy_path(u"/bin/ls"),
    })
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
        self.failIf(self.browser.can_reorder)
        self.failIf(self.browser.headers)

    def tearDown(self):
        self.browser = None


class TBrowserBase(TestCase):
    Kind = None

    def setUp(self):
        config.init()
        init_fake_app()
        self.library = library = SongFileLibrary()
        library.librarian = SongLibrarian()
        library.add(SONGS)
        self.Kind.init(library)
        self.b = self.Kind(library)

    def tearDown(self):
        self.b.destroy()
        self.library.destroy()
        config.quit()
        destroy_fake_app()


class TBrowserMixin(object):

    def test_menu(self):
        # FIXME: the playlist browser accesses the song list directly
        if self.b.name == "Playlists":
            return
        menu = self.b.Menu([], self.library, [])
        self.assertTrue(isinstance(menu, Gtk.Menu))

    def test_key(self):
        self.assertEqual(browsers.get(browsers.name(self.Kind)), self.Kind)

    def test_pack_unpack(self):
        to_pack = Gtk.Button()
        container = self.b.pack(to_pack)
        self.b.unpack(container, to_pack)

    def test_pack_noshow_songpane(self):
        to_pack = Gtk.Button()
        to_pack.hide()
        container = self.b.pack(to_pack)
        self.assertFalse(to_pack.get_visible())
        self.b.unpack(container, to_pack)
        self.assertFalse(to_pack.get_visible())

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
            song = AudioFile({"~filename": dummy_path(u"/fake")})
            song.sanitize()
            self.b.scroll(song)

    def test_filters_caps(self):
        with realized(self.b):
            self.failUnless(isinstance(self.b.can_filter_tag("foo"), bool))
            self.failUnless(isinstance(self.b.can_filter_text(), bool))
            self.failUnless(isinstance(self.b.can_filter("foo"), bool))

    def test_filter_text(self):
        with realized(self.b):
            if self.b.can_filter_tag("foo"):
                self.b.filter("foo", ["bar"])
            if self.b.can_filter_tag("(((((##!!!!))),"):
                self.b.filter("(((((##!!!!))),", ["(((((##!!!!))),"])
            if self.b.can_filter_text():
                self.b.filter_text("foo")
                self.b.filter_text("(((((##!!!!))),,,==")

    def test_get_filter_text(self):
        with realized(self.b):
            if self.b.can_filter_text():
                self.assertEqual(self.b.get_filter_text(), u"")
                self.assertTrue(isinstance(self.b.get_filter_text(), unicode))
                self.b.filter_text(u"foo")
                self.assertEqual(self.b.get_filter_text(), u"foo")
                self.assertTrue(isinstance(self.b.get_filter_text(), unicode))

    def test_filter_albums(self):
        with realized(self.b):
            if self.b.can_filter_albums():
                self.b.filter_albums([])
                self.b.filter_albums([object])
                self.b.filter_albums(self.library.albums.values())

    def test_filter_other(self):
        with realized(self.b):
            self.b.unfilter()


browsers.init()
# create a new test class for each browser
for browser in browsers.browsers:
    cls = TBrowserBase
    name = "TB" + browser.__name__
    new_test = type(name, (TBrowserBase, TBrowserMixin), {})
    new_test.Kind = browser
    globals()[name] = new_test
