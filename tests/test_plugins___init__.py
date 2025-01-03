# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, mkstemp

import os

from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.util.songwrapper import SongWrapper, list_wrapper
from quodlibet.plugins import PluginConfig


class TSongWrapper(TestCase):
    psong = AudioFile(
        {
            "~filename": "does not/exist",
            "title": "more songs",
            "discnumber": "2/2",
            "tracknumber": "1",
            "artist": "Foo\nI have two artists",
            "album": "Bar",
            "~bookmark": "2:10 A bookmark",
        }
    )
    pwrap = SongWrapper(psong)

    def setUp(self):
        fd, self.filename = mkstemp()
        os.close(fd)
        config.init()
        self.wrap = SongWrapper(AudioFile({"title": "woo", "~filename": self.filename}))

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

    def test_slots(self):
        def breakme():
            self.wrap.woo = 1

        self.assertRaises(AttributeError, breakme)

    def test_cmp(self):
        songs = [SongWrapper(AudioFile({"tracknumber": str(i)})) for i in range(10)]
        songs.reverse()
        songs.sort()
        self.assertEqual([s("~#track") for s in songs], list(range(10)))

    def test_needs_write_yes(self):
        assert not self.wrap._needs_write
        self.wrap["woo"] = "bar"
        assert self.wrap._needs_write

    def test_needs_write_no(self):
        assert not self.wrap._needs_write
        self.wrap["~woo"] = "bar"
        assert not self.wrap._needs_write

    def test_pop(self):
        assert not self.wrap._needs_write
        self.wrap.pop("artist", None)
        assert self.wrap._needs_write

    def test_getitem(self):
        self.assertEqual(self.wrap["title"], "woo")

    def test_get(self):
        self.assertEqual(self.wrap.get("title"), "woo")
        self.assertEqual(self.wrap.get("dne"), None)
        self.assertEqual(self.wrap.get("dne", "huh"), "huh")

    def test_delitem(self):
        assert "title" in self.wrap
        del self.wrap["title"]
        assert "title" not in self.wrap
        assert self.wrap._needs_write

    def test_realkeys(self):
        self.assertEqual(self.pwrap.realkeys(), self.psong.realkeys())

    def test_can_change(self):
        for key in ["~foo", "title", "whee", "a test", "foo=bar", ""]:
            self.assertEqual(self.pwrap.can_change(key), self.psong.can_change(key))

    def test_comma(self):
        for key in ["title", "artist", "album", "notexist", "~length"]:
            self.assertEqual(self.pwrap.comma(key), self.psong.comma(key))

    def test_list(self):
        for key in ["title", "artist", "album", "notexist", "~length"]:
            self.assertEqual(self.pwrap.list(key), self.psong.list(key))

    def test_dicty(self):
        self.assertEqual(self.pwrap.keys(), self.psong.keys())
        self.assertEqual(list(self.pwrap.values()), list(self.psong.values()))
        self.assertEqual(self.pwrap.items(), self.psong.items())

    def test_mtime(self):
        self.wrap._song.sanitize()
        assert self.wrap.valid()
        self.wrap["~#mtime"] = os.path.getmtime(self.filename) - 2
        self.wrap._updated = False
        assert not self.wrap.valid()

    def test_setitem(self):
        assert not self.wrap._was_updated()
        self.wrap["title"] = "bar"
        assert self.wrap._was_updated()
        self.assertEqual(self.wrap["title"], "bar")

    def test_not_really_updated(self):
        assert not self.wrap._was_updated()
        self.wrap["title"] = "woo"
        assert not self.wrap._was_updated()
        self.wrap["title"] = "quux"
        assert self.wrap._was_updated()

    def test_new_tag(self):
        assert not self.wrap._was_updated()
        self.wrap["version"] = "bar"
        assert self.wrap._was_updated()

    def test_bookmark(self):
        self.assertEqual(self.psong.bookmarks, self.pwrap.bookmarks)
        self.pwrap.bookmarks = [(43, "another mark")]
        self.assertEqual(self.psong["~bookmark"], "0:43 another mark")
        self.assertEqual(self.psong.bookmarks, self.pwrap.bookmarks)


class TListWrapper(TestCase):
    def test_empty(self):
        wrapped = list_wrapper([])
        self.assertEqual(wrapped, [])

    def test_empty_song(self):
        wrapped = list_wrapper([{}])
        assert len(wrapped) == 1
        assert not isinstance(wrapped[0], dict)

    def test_none(self):
        wrapped = list_wrapper([None, None])
        assert len(wrapped) == 2
        self.assertEqual(wrapped, [None, None])


class TPluginConfig(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_mapping(self):
        c = PluginConfig("some")
        c.set("foo", "bar")
        self.assertEqual(config.get("plugins", "some_foo"), "bar")

    def test_defaults(self):
        c = PluginConfig("some")
        c.defaults.set("hm", "mh")
        self.assertEqual(c.get("hm"), "mh")
