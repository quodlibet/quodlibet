import os, config

from unittest import TestCase
from tests import registerCase
from formats._audio import AudioFile

try: from sets import Set as set
except ImportError: pass

bar_1_1 = AudioFile({
    "title": "A song",
    "discnumber": "1/2", "tracknumber": "1/3",
    "artist": "Foo", "album": "Bar" })
bar_1_2 = AudioFile({
    "title": "Perhaps another",
    "discnumber": "1", "tracknumber": "2/3",
    "artist": "Lali-ho!", "album": "Bar",
    "~#playlist_test": 1})
bar_2_1 = AudioFile({
    "~filename": "does not/exist",
    "title": "more songs",
    "discnumber": "2/2", "tracknumber": "1",
    "artist": "Foo\nI have two artists", "album": "Bar",
    "lyricist": "Foo", "composer": "Foo", "performer": "I have two artists",
    "~#playlist_test": 2, "~#playlist_hi%20there": 3})

quux = AudioFile({
    "~filename": "tests/data/asong.ogg",
    "album": "Quuxly"
    })

class TAudioFile(TestCase):
    def setUp(self):
        file(quux["~filename"], "w")

    def test_sort(self):
        l = [quux, bar_1_2, bar_2_1, bar_1_1]
        l.sort()
        self.assertEqual(l, [bar_1_1, bar_1_2, bar_2_1, quux])
        self.assertEqual(quux, quux)
        self.assertEqual(bar_1_1, bar_1_1)
        self.assertNotEqual(bar_2_1, bar_1_2)
        
    def test_realkeys(self):
        self.failIf("artist" in quux.realkeys())
        self.failIf("~filename" in quux.realkeys())
        self.failUnless("album" in quux.realkeys())

    def test_call(self):
        # real keys should lookup the same
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1[key], bar_1_1(key))

        # fake/generated key checks
        self.failIf(quux("not a key"))
        self.failUnlessEqual(quux("not a key", "foo"), "foo")
        self.failUnlessEqual(quux("artist"), "")
        self.failUnlessEqual(quux("~basename"), "asong.ogg")
        self.failUnlessEqual(quux("~dirname"), "tests/data")
        self.failUnlessEqual(quux("title"), "asong.ogg [Unknown]")
        
        self.failUnlessEqual(bar_1_1("~#disc"), 1)
        self.failUnlessEqual(bar_1_2("~#disc"), 1)
        self.failUnlessEqual(bar_2_1("~#disc"), 2)
        self.failUnlessEqual(bar_1_1("~#track"), 1)
        self.failUnlessEqual(bar_1_2("~#track"), 2)
        self.failUnlessEqual(bar_2_1("~#track"), 1)

    def test_call_people(self):
        self.failUnlessEqual(quux("~people"), "")
        self.failUnlessEqual(bar_1_1("~people"), "Foo")
        self.failUnlessEqual(bar_1_2("~people"), "Lali-ho!")
        self.failUnlessEqual(bar_2_1("~people"), "Foo\nI have two artists")

    def test_call_multiple(self):
        for song in [quux, bar_1_1, bar_2_1]:
            self.failUnlessEqual(song("~~people"), song("~people"))
            self.failUnlessEqual(song("~title~people"), song("title"))
            self.failUnlessEqual(song("~title~~people"), song("~title~artist"))

    def test_list(self):
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1.list(key), [bar_1_1(key)])

        self.failUnlessEqual(quux.list("artist"), [])
        self.failUnlessEqual(quux.list("title"), [quux("title")])
        self.failUnlessEqual(quux.list("not a key"), [])

        self.failUnlessEqual(len(bar_2_1.list("artist")), 2)
        self.failUnlessEqual(bar_2_1.list("artist"),
                             bar_2_1["artist"].split("\n"))

    def test_comma(self):
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1.comma(key), bar_1_1(key))
        self.failUnless(", " in bar_2_1.comma("artist"))

    def test_exist(self):
        self.failIf(bar_2_1.exists())
        self.failUnless(quux.exists())

    def test_valid(self):
        self.failIf(bar_2_1.valid())

        quux["~#mtime"] = 0
        self.failIf(quux.valid())
        quux["~#mtime"] = os.path.getmtime(quux["~filename"])
        self.failUnless(quux.valid())
        os.utime(quux["~filename"], (quux["~#mtime"], quux["~#mtime"] - 1))
        self.failIf(quux.valid())
        quux["~#mtime"] = os.path.getmtime(quux["~filename"])
        self.failUnless(quux.valid())

        os.utime(quux["~filename"], (quux["~#mtime"], quux["~#mtime"] - 1))
        quux.sanitize()
        self.failUnless(quux.valid())

    def test_can_change(self):
        self.failIf(quux.can_change("~foobar"))
        self.failIf(quux.can_change("=foobar"))
        self.failIf(quux.can_change("foo=bar"))
        self.failIf(quux.can_change(""))

        self.failUnless(quux.can_change("foo bar"))
        os.chmod(quux["~filename"], 0444)
        self.failIf(quux.can_change("foo bar"))
        os.chmod(quux["~filename"], 0644)
        self.failUnless(quux.can_change("foo bar"))

    def test_rename(self):
        old_fn = quux("~basename")
        new_fn = "anothersong.mp3"
        dir = os.getcwd() + "/tests/data/"
        self.failUnless(quux.exists())
        quux.rename(new_fn)
        self.failIf(os.path.exists(dir + old_fn))
        self.failUnless(quux.exists())
        quux.rename(old_fn)
        self.failIf(os.path.exists(dir + new_fn))
        self.failUnless(quux.exists())

        # move out of parent dir and back
        quux.rename("/tmp/more_test_data")
        self.failIf(os.path.exists(dir + old_fn))
        self.failUnless(quux.exists())
        quux.rename(dir + old_fn)
        self.failUnless(quux.exists())

        # rename to existing files
        quux.rename(quux("~basename"))
        self.failUnlessRaises(ValueError,
                              lambda: quux.rename("/dev/null"))
        self.failUnlessRaises(ValueError,
                              lambda: quux.rename("silence-44-s.ogg"))

    def test_website(self):
        song = AudioFile()
        song["comment"] = "www.foo"
        song["contact"] = "eh@foo.org"
        self.failUnlessEqual(song.website(), "www.foo")
        song["contact"] = "https://www.foo.org"
        self.failUnlessEqual(song.website(), "https://www.foo.org")
        song["website"] = "foo\nhttps://another.com"
        self.failUnlessEqual(song.website(), "foo")

        song = AudioFile({"artist": "Artist", "album": "Album"})
        for value in song.values(): self.failUnless(value in song.website())
        song["labelid"] = "QL-12345"
        self.failIf(song["artist"] in song.website())
        self.failUnless(song["labelid"] in song.website())

    def test_sanitize(self):
        q = AudioFile(quux)
        b = AudioFile(bar_1_1)
        q.sanitize()
        self.failUnlessRaises(ValueError, b.sanitize)

    def test_to_dump(self):
        dump = bar_1_1.to_dump()
        self.failUnlessEqual(dump.count("\n"), len(bar_1_1))
        for key, value in bar_1_1.items():
            self.failUnless(key in dump)
            self.failUnless(value in dump)

    def test_to_dump_long(self):
        b = AudioFile(bar_1_1); b["~#length"] = 200000000000L
        dump = b.to_dump()
        self.failUnlessEqual(dump.count("\n"), len(b))

    def test_add(self):
        song = AudioFile()
        self.failIf("foo" in song)
        song.add("foo", "bar")
        self.failUnlessEqual(song["foo"], "bar")
        song.add("foo", "another")
        self.failUnlessEqual(song.list("foo"), ["bar", "another"])

    def test_remove(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.add("foo", "another")
        song.add("foo", "one more")
        song.remove("foo", "another")
        self.failUnlessEqual(song.list("foo"), ["bar", "one more"])
        song.remove("foo", "bar")
        self.failUnlessEqual(song.list("foo"), ["one more"])
        song.remove("foo", "one more")
        self.failIf("foo" in song)

        song.add("foo", "bar")
        song.add("foo", "another")
        song.add("foo", "one more")
        song.remove("foo", "not in list")
        self.failIf("foo" in song)
        
    def test_change(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.add("foo", "another")
        song.change("foo", "bar", "one more")
        self.failUnlessEqual(song.list("foo"), ["one more", "another"])
        song.change("foo", "does not exist", "finally")
        self.failUnlessEqual(song["foo"], "finally")
        song.change("foo", "finally", "we're done")
        self.failUnlessEqual(song["foo"], "we're done")

    def tearDown(self):
        os.unlink(quux["~filename"])

class ReplayGain(TestCase):
    def test_replaygain(self):
        song = AudioFile({"replaygain_album_gain": "-1.00 dB",
                          "replaygain_album_peak": "1.1",
                          "replaygain_track_gain": "+1.0 dB",
                          "replaygain_track_peak": "0.9"})

        config.set("settings", "gain", 0)
        self.failUnlessEqual(song.replay_gain(), 1)

        config.set("settings", "gain", 1)
        self.failUnless(song.replay_gain() > 1)
        radio_rg = song.replay_gain()

        config.set("settings", "gain", 2)
        self.failUnless(song.replay_gain() < 1)

        # verify complete ignorance of RG when tags aren't right
        song["replaygain_album_gain"] = "fdsodgbdf"
        self.failUnlessEqual(song.replay_gain(), 1)

        del(song["replaygain_album_gain"])
        del(song["replaygain_album_peak"])
        # verify defaulting to track when album is present
        self.failUnlessAlmostEqual(song.replay_gain(), radio_rg)

# Special test case for find_cover since it has to create/remove
# various files.
class FindCoverTest(TestCase):
    def setUp(self):
        self.dir = os.path.realpath(quux("~dirname"))
        self.files = [os.path.join(self.dir, "12345.jpg"),
                      os.path.join(self.dir, "nothing.jpg")
                      ]
        for f in self.files: file(f, "w").close()

    def test_dir_not_exist(self):
        self.failIf(bar_2_1.find_cover())

    def test_nothing(self):
        self.failIf(quux.find_cover())

    def test_labelid(self):
        quux["labelid"] = "12345"
        self.failUnlessEqual(quux.find_cover().name,
                             os.path.join(self.dir, "12345.jpg"))
        del(quux["labelid"])

    def test_regular(self):
        files = [os.path.join(self.dir, f) for f in
                 ["cover.png", "frontcover.jpg", "frontfoldercover.gif",
                  "jacketcoverfrontfolder.jpeg"]]
        for f in files:
            file(f, "w").close()
            self.failUnless(quux.find_cover().name == f)
        self.test_labelid() # labelid must work with other files present

        for f in files: os.unlink(f)
        self.failIf(quux.find_cover())

    def tearDown(self):
        for f in self.files: os.unlink(f)

registerCase(TAudioFile)
registerCase(FindCoverTest)
registerCase(ReplayGain)
