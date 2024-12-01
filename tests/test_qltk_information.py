# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from tests import TestCase, init_fake_app, destroy_fake_app

from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary
from quodlibet.qltk.information import Information, OneArtist, OneAlbum, \
    ManySongs, OneSong, TitleLabel, _sort_albums
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
        f = AF({"~filename": fsnative("/dev/null")})
        self.inf = Information(self.library, [f])
        self.assert_child_is(OneSong)

    def test_two(self):
        f = AF({"~filename": fsnative("/dev/null")})
        f2 = AF({"~filename": fsnative("/dev/null2")})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(ManySongs)

    def test_album(self):
        f = AF({"~filename": fsnative("/dev/null"), "album": "woo"})
        f2 = AF({"~filename": fsnative("/dev/null2"), "album": "woo"})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(OneAlbum)

    def test_album_special_chars(self):
        f = AF({"~filename": fsnative("/dev/null"), "album": "woo & hoo"})
        f2 = AF({"~filename": fsnative("/dev/null2"), "album": "woo & hoo"})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(OneAlbum)

    def test_artist(self):
        f = AF({"~filename": fsnative("/dev/null"), "artist": "woo"})
        f2 = AF({"~filename": fsnative("/dev/null2"), "artist": "woo"})
        self.inf = Information(self.library, [f, f2])
        self.assert_child_is(OneArtist)

    def test_performer_roles(self):
        f = AF({"~filename": fsnative("/dev/null"), "performer:piano": "woo"})
        self.inf = Information(self.library, [f])
        self.assert_child_is(OneSong)

    def test_remove_song(self):
        f = AF({"~filename": fsnative("/dev/null"), "artist": "woo"})
        f2 = AF({"~filename": fsnative("/dev/null2"), "artist": "woo"})
        self.library.add([f, f2])
        self.inf = Information(self.library, [f, f2])
        self.library.remove([f])

    def assert_child_is(self, cls):
        assert isinstance(self.inf.get_child(), cls)


class TUtils(TestCase):
    def test_sort_albums(self):
        # Make sure we have more than one album, one having a null date
        f = AF({"~filename": fsnative("/1"), "album": "one"})
        f2 = AF({"~filename": fsnative("/2"), "album": "one"})
        f3 = AF({"~filename": fsnative("/3"), "album": "two", "date": "2009"})
        f4 = AF({"~filename": fsnative("/4")})
        albums, count = _sort_albums([f, f2, f3, f4])
        self.assertEqual(count, 1)
        self.assertEqual(len(albums), 2)


class TTitleLabel(TestCase):
    def test_foo(self):
        label = TitleLabel("foo & bar")
        self.assertEqual(label.get_text(), "foo & bar")
