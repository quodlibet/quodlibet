from unittest import TestCase, makeSuite
from tests import registerCase
from library import AudioFile, Unknown

class AudioFileTest(TestCase):
    def test_cmp(self):
        song1 = AudioFile({ "artist": u"Foo", "album": u"Bar",
                            "=d": 1, "=#": 2, "title": "A song" })
        
        song1c = AudioFile({ "artist": u"Foo", "album": u"Bar",
                             "=d": 1, "=#": 2, "title": "A song" })
        
        song2 = AudioFile({ "artist": u"Foo", "album": u"Bar",
                            "=d": 2, "=#": 2, "title": "Another song" })
        
        self.failUnlessEqual(song1, song1)
        self.failUnlessEqual(song1, song1c)
        self.failUnless(song2 > song1)

    def test_getters(self):
        song1 = AudioFile({ "a": "foo\nbar", "b": "foobar",
                            "=filename": "DNE",
                            "=mtime": 0, "=foobar": 2,
                            "album": Unknown("Unknown")})
        self.failUnlessEqual(song1.comma("a"), "foo, bar")
        self.failUnlessEqual(song1.comma("b"), "foobar")
        self.failUnlessEqual(song1.comma("c"), "")
        self.failUnless(song1.realkeys() in [["a", "b"], ["b", "a"]])
        self.failIf(song1.exists())
        self.failIf(song1.valid())

    def test_setters(self):
        song = AudioFile({ "=filename": "undef",
                           "artist": "foo\nbar", "title": "foobar",
                           "album": Unknown("Unknown")})
        song.add("album", "An Album")
        self.failUnlessEqual(song["album"], "An Album")
        song.change("artist", "foo", "quux")
        self.failUnlessEqual(song["artist"], "quux\nbar")
        song.remove("album", "An Album")
        self.failUnless(song.unknown("album"))
        song.add("tracknumber", "11/12")
        self.failUnlessEqual(song["=#"], 11)
        song.change("artist", "Not A Value", "baz")
        self.failUnlessEqual(song["artist"], "baz")
        song.add("artist", "foo")
        self.failUnlessEqual(song["artist"], "baz\nfoo")
        song.remove("artist", "Not A Value")
        self.failUnless(song.unknown("artist"))
        song.add("artist", "foo")
        song.add("artist", "bar")
        song.remove("artist", "foo")
        self.failUnlessEqual(song["artist"], "bar")

    def test_sanitize(self):
        song = AudioFile({ "=filename": "/foo/bar/quux.ogg",
                           "title": u"A Song",
                           "vendor": "Xiph",
                           "discnumber": "2/3",
                           "tracknumber": "11/99" })
        song.sanitize()
        self.failUnlessEqual(song["=basename"], "quux.ogg")
        self.failUnlessEqual(song["=dirname"], "/foo/bar")
        self.failUnlessEqual(song["=#"], 11)
        self.failUnlessEqual(song["=d"], 2)
        self.failUnlessEqual(song["=playcount"], 0)
        self.failUnless("vendor" not in song)
        self.failUnlessEqual(song["album"], "Unknown")
        self.failUnless(song.unknown("album"))

    def test_get_played(self):
        song1 = AudioFile({"=playcount": 0})
        song2 = AudioFile({"=playcount": 4,
                           "=lastplayed": 1099509099 })
        self.failUnlessEqual(song1.get_played(), "Never")
        # This test will fail unless you are in CST.
        self.failUnlessEqual(song2.get_played(),
                             "4 times, recently on 2004-11-03, 13:11:39")

registerCase(AudioFileTest)
