from tests import TestCase, add

import os

from quodlibet import config
from quodlibet.formats._audio import AudioFile
from quodlibet.util.songwrapper import SongWrapper, ListWrapper

class TSongWrapper(TestCase):

    psong = AudioFile({
        "~filename": "does not/exist",
        "title": "more songs",
        "discnumber": "2/2", "tracknumber": "1",
        "artist": "Foo\nI have two artists", "album": "Bar",
        "~bookmark": "2:10 A bookmark" })
    pwrap = SongWrapper(psong)

    def setUp(self):
        config.init()
        self.wrap = SongWrapper(AudioFile(
            {"title": "woo", "~filename": "/dev/null"}))

    def tearDown(self):
        config.quit()

    def test_slots(self):
        def breakme(): self.wrap.woo = 1
        self.failUnlessRaises(AttributeError, breakme)

    def test_cmp(self):
        songs = [SongWrapper(AudioFile({"tracknumber": str(i)}))
                 for i in range(10)]
        songs.reverse()
        songs.sort()
        self.failUnlessEqual([s("~#track") for s in songs], range(10))

    def test_needs_write_yes(self):
        self.failIf(self.wrap._needs_write)
        self.wrap["woo"] = "bar"
        self.failUnless(self.wrap._needs_write)

    def test_needs_write_no(self):
        self.failIf(self.wrap._needs_write)
        self.wrap["~woo"] = "bar"
        self.failIf(self.wrap._needs_write)

    def test_getitem(self):
        self.failUnlessEqual(self.wrap["title"], "woo")

    def test_get(self):
        self.failUnlessEqual(self.wrap.get("title"), "woo")
        self.failUnlessEqual(self.wrap.get("dne"), None)
        self.failUnlessEqual(self.wrap.get("dne", "huh"), "huh")

    def test_delitem(self):
        self.failUnless("title" in self.wrap)
        del(self.wrap["title"])
        self.failIf("title" in self.wrap)
        self.failUnless(self.wrap._needs_write)

    def test_realkeys(self):
        self.failUnlessEqual( self.pwrap.realkeys(), self.psong.realkeys())

    def test_website(self):
        self.failUnlessEqual(self.pwrap.website(), self.psong.website())

    def test_find_cover(self):
        self.failUnlessEqual(self.pwrap.find_cover(), self.psong.find_cover())

    def test_can_change(self):
        for key in ["~foo", "title", "whee", "a test", "foo=bar", ""]:
            self.failUnlessEqual(
                self.pwrap.can_change(key), self.psong.can_change(key))

    def test_comma(self):
        for key in ["title", "artist", "album", "notexist", "~length"]:
            self.failUnlessEqual(self.pwrap.comma(key), self.psong.comma(key))

    def test_list(self):
        for key in ["title", "artist", "album", "notexist", "~length"]:
            self.failUnlessEqual(self.pwrap.list(key), self.psong.list(key))

    def test_dicty(self):
        self.failUnlessEqual(self.pwrap.keys(), self.psong.keys())
        self.failUnlessEqual(self.pwrap.values(), self.psong.values())
        self.failUnlessEqual(self.pwrap.items(), self.psong.items())

    def test_mtime(self):
        self.wrap._song.sanitize()
        self.failUnless(self.wrap.valid())
        self.wrap["~#mtime"] = os.path.getmtime("/dev/null") - 2
        self.wrap._updated = False
        self.failIf(self.wrap.valid())

    def test_setitem(self):
        self.failIf(self.wrap._was_updated())
        self.wrap["title"] = "bar"
        self.failUnless(self.wrap._was_updated())
        self.failUnlessEqual(self.wrap["title"], "bar")

    def test_not_really_updated(self):
        self.failIf(self.wrap._was_updated())
        self.wrap["title"] = "woo"
        self.failIf(self.wrap._was_updated())
        self.wrap["title"] = "quux"
        self.failUnless(self.wrap._was_updated())

    def test_new_tag(self):
        self.failIf(self.wrap._was_updated())
        self.wrap["version"] = "bar"
        self.failUnless(self.wrap._was_updated())

    def test_bookmark(self):
        self.failUnlessEqual(self.psong.bookmarks, self.pwrap.bookmarks)
        self.pwrap.bookmarks = [(43, "another mark")]
        self.failUnlessEqual(self.psong["~bookmark"], "0:43 another mark")
        self.failUnlessEqual(self.psong.bookmarks, self.pwrap.bookmarks)

add(TSongWrapper)

class TListWrapper(TestCase):
    def test_empty(self):
        wrapped = ListWrapper([])
        self.failUnlessEqual(wrapped, [])

    def test_empty_song(self):
        wrapped = ListWrapper([{}])
        self.failUnless(len(wrapped) == 1)
        self.failIf(isinstance(wrapped[0], dict))

    def test_none(self):
        wrapped = ListWrapper([None, None])
        self.failUnless(len(wrapped) == 2)
        self.failUnlessEqual(wrapped, [None, None])
add(TListWrapper)


