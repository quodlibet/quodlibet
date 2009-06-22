from tests import TestCase, add

import os

from quodlibet import config

from quodlibet.formats._audio import AudioFile

bar_1_1 = AudioFile({
    "title": "A song",
    "discnumber": "1/2", "tracknumber": "1/3",
    "artist": "Foo", "album": "Bar" })
bar_1_2 = AudioFile({
    "title": "Perhaps another",
    "discnumber": "1", "tracknumber": "2/3",
    "artist": "Lali-ho!", "album": "Bar",
    "date": "2004-12-12"})
bar_2_1 = AudioFile({
    "~filename": "does not/exist",
    "title": "more songs",
    "discnumber": "2/2", "tracknumber": "1",
    "artist": "Foo\nI have two artists", "album": "Bar",
    "lyricist": "Foo", "composer": "Foo", "performer": "I have two artists"})

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

    def test_trackdisc(self):
        self.failUnlessEqual(bar_1_1("~#track"), 1)
        self.failUnlessEqual(bar_1_1("~#disc"), 1)
        self.failUnlessEqual(bar_1_1("~#tracks"), 3)
        self.failUnlessEqual(bar_1_1("~#discs"), 2)
        self.failIf(bar_1_2("~#discs"))
        self.failIf(bar_2_1("~#tracks"))

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

    def test_year(self):
        self.failUnlessEqual(bar_1_2("~year"), "2004")
        self.failUnlessEqual(bar_1_2("~#year"), 2004)
        self.failUnlessEqual(bar_1_1("~#year", 1999), 1999)

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

    def test_rename_to_existing(self):
        quux.rename(quux("~basename"))
        self.failUnlessRaises(ValueError, quux.rename, "/dev/null")
        self.failUnlessRaises(ValueError, quux.rename, "silence-44-s.ogg")

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
        n = AudioFile({"artist": u"foo\0bar", "title": u"baz\0",
                        "~filename": "whatever"})
        n.sanitize()
        self.failUnlessEqual(n["artist"], "foo\nbar")
        self.failUnlessEqual(n["title"], "baz")

    def test_performers(self):
        q = AudioFile([("performer:vocals", "A"), ("performer:guitar", "B"),
                       ("performer", "C")])
        self.failUnless("A (Vocals)" in q.list("~performers"))
        self.failUnless("B (Guitar)" in q.list("~performers"))
        self.failUnless("C" in q.list("~performers"))
        self.failUnless("A (Vocals)" in q.list("~people"))
        self.failUnless("B (Guitar)" in q.list("~people"))
        self.failUnlessEqual(len(q.list("~performers")), 3)

    def test_to_dump(self):
        dump = bar_1_1.to_dump()
        self.failUnlessEqual(dump.count("\n"), len(bar_1_1) + 1)
        for key, value in bar_1_1.items():
            self.failUnless(key in dump)
            self.failUnless(value in dump)

    def test_to_dump_long(self):
        b = AudioFile(bar_1_1); b["~#length"] = 200000000000L
        dump = b.to_dump()
        self.failUnlessEqual(dump.count("\n"), len(b) + 1)

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

    def test_bookmarks_none(self):
        self.failUnlessEqual([], AudioFile().bookmarks)

    def test_bookmarks_simple(self):
        af = AudioFile({"~bookmark": "1:20 Mark 1"})
        self.failUnlessEqual([(80, "Mark 1")], af.bookmarks)

    def test_bookmarks_two(self):
        af = AudioFile({"~bookmark": "1:40 Mark 2\n1:20 Mark 1"})
        self.failUnlessEqual([(80, "Mark 1"), (100, "Mark 2")], af.bookmarks)

    def test_bookmark_invalid(self):
        af = AudioFile({"~bookmark": ("Not Valid\n1:40 Mark 2\n"
                                      "-20 Not Valid 2\n1:20 Mark 1")})
        self.failUnlessEqual(
            [(80, "Mark 1"), (100, "Mark 2"), (-1, "Not Valid"),
             (-1, "-20 Not Valid 2")], af.bookmarks)

    def test_set_bookmarks_none(self):
        af = AudioFile({"bookmark": "foo"})
        af.bookmarks = []
        self.failUnlessEqual([], AudioFile().bookmarks)
        self.failIf("~bookmark" in af)

    def test_set_bookmarks_simple(self):
        af = AudioFile()
        af.bookmarks = [(120, "A mark"), (140, "Mark twain")]
        self.failUnlessEqual(af["~bookmark"], "2:00 A mark\n2:20 Mark twain")

    def test_set_bookmarks_invalid_value(self):
        self.failUnlessRaises(
            ValueError, setattr, AudioFile(), 'bookmarks', "huh?")
    def test_set_bookmarks_invalid_time(self):
        self.failUnlessRaises(
            TypeError, setattr, AudioFile(), 'bookmarks', [("notint", "!")])
    def test_set_bookmarks_unrealistic_time(self):
        self.failUnlessRaises(
            ValueError, setattr, AudioFile(), 'bookmarks', [(-1, "!")])

    def test_album_key(self):
        self.failUnlessEqual(AudioFile().album_key, ("", ""))

        album = AudioFile(album="foo")
        self.failUnlessEqual(album.album_key, ("foo", ""))

        labelid = AudioFile(labelid="foo")
        self.failUnlessEqual(labelid.album_key, ("", "foo"))

        mbid = AudioFile(musicbrainz_albumid="foo")
        self.failUnlessEqual(mbid.album_key, ("", "foo"))

        title_id = AudioFile(album="foo", labelid="bar")
        self.failUnlessEqual(title_id.album_key, ("foo", "bar"))

        all = AudioFile(album="foo", labelid="bar", musicbrainz_albumid="quux")
        self.failUnlessEqual(all.album_key, ("foo", "bar"))

    def tearDown(self):
        os.unlink(quux["~filename"])
add(TAudioFile)

class Treplay_gain(TestCase):
    def setUp(self):
        self.song = AudioFile({"replaygain_album_gain": "-1.00 dB",
                               "replaygain_album_peak": "1.1",
                               "replaygain_track_gain": "+1.0 dB",
                               "replaygain_track_peak": "0.9"})

    def test_nogain(self):
        self.failUnlessEqual(self.song.replay_gain(["none", "track"]), 1)

    def test_trackgain(self):
        self.failUnless(self.song.replay_gain(["track"]) > 1)

    def test_albumgain(self):
        self.failUnless(self.song.replay_gain(["album"]) < 1)

    def test_invalid(self):
        self.song["replaygain_album_gain"] = "fdsodgbdf"
        self.failUnlessEqual(self.song.replay_gain(["album"]), 1)

    def test_track_fallback(self):
        radio_rg = self.song.replay_gain(["track"])
        del(self.song["replaygain_album_gain"])
        del(self.song["replaygain_album_peak"])
        # verify defaulting to track when album is present
        self.failUnlessAlmostEqual(
            self.song.replay_gain(["album", "track"]), radio_rg)
add(Treplay_gain)

# Special test case for find_cover since it has to create/remove
# various files.
class Tfind_cover(TestCase):
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
        self.failUnlessEqual(os.path.abspath(quux.find_cover().name),
                             os.path.join(self.dir, "12345.jpg"))
        del(quux["labelid"])

    def test_regular(self):
        files = [os.path.join(self.dir, f) for f in
                 ["cover.png", "frontcover.jpg", "frontfoldercover.gif",
                  "jacketcoverfrontfolder.jpeg"]]
        for f in files:
            file(f, "w").close()
            self.files.append(f)
            self.failUnlessEqual(os.path.abspath(quux.find_cover().name), f)
        self.test_labelid() # labelid must work with other files present        

    def tearDown(self):
        map(os.unlink, self.files)
add(Tfind_cover)
