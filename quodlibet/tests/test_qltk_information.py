# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from tests import TestCase, init_fake_app, destroy_fake_app

from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary
from quodlibet.qltk.information import Information, OneArtist, OneAlbum, \
    ManySongs, OneSong, TitleLabel
import quodlibet.config


def AF(*args, **kwargs):
    a = AudioFile(*args, **kwargs)
    a.sanitize()
    return a


class TInformation(TestCase):

    def setUp(self):
        quodlibet.config.init()
        init_fake_app()
        self.inf = None
        self.library = SongLibrary()

    def tearDown(self):
        destroy_fake_app()
        self.library.destroy()
        quodlibet.config.quit()
        if self.inf:
            self.inf.destroy()

    def test_none(self):
        Information(self.library, []).destroy()

    def test_one(self):
        f = AF({"~filename": fsnative(u"/dev/null")})
        self.inf = Information(self.library, [f])
        self.assert_child_is(OneSong)

    def test_two(self):
        f = AF({"~filename": fsnative(u"/dev/null")})
        f2 = AF({"~filename": fsnative(u"/dev/null2")})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(ManySongs)

    def test_album(self):
        f = AF({"~filename": fsnative(u"/dev/null"), "album": "woo"})
        f2 = AF({"~filename": fsnative(u"/dev/null2"), "album": "woo"})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(OneAlbum)

    def test_album_special_chars(self):
        f = AF({"~filename": fsnative(u"/dev/null"), "album": "woo & hoo"})
        f2 = AF({"~filename": fsnative(u"/dev/null2"), "album": "woo & hoo"})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(OneAlbum)

    def test_artist(self):
        f = AF({"~filename": fsnative(u"/dev/null"), "artist": "woo"})
        f2 = AF({"~filename": fsnative(u"/dev/null2"), "artist": "woo"})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(OneArtist)

    def assert_child_is(self, cls):
        self.failUnless(isinstance(self.inf.get_child(), cls))


class TTitleLabel(TestCase):
    def test_foo(self):
        label = TitleLabel("foo & bar")
        self.failUnlessEqual(label.get_text(), "foo & bar")
