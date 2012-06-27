from tests import TestCase, add

import os

from quodlibet import config
from quodlibet.util import HashableDict
from quodlibet.formats._audio import AudioFile
from quodlibet.formats._audio import INTERN_NUM_DEFAULT

bar_1_1 = AudioFile({
    "~filename": "/fakepath/1",
    "title": "A song",
    "discnumber": "1/2", "tracknumber": "1/3",
    "artist": "Foo", "album": "Bar"})
bar_1_2 = AudioFile({
    "~filename": "/fakepath/2",
    "title": "Perhaps another",
    "discnumber": "1", "tracknumber": "2/3",
    "artist": "Lali-ho!", "album": "Bar",
    "date": "2004-12-12", "originaldate": "2005-01-01"})
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

num_call = AudioFile({"custom": "0.3"})

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

    def test_originalyear(self):
        self.failUnlessEqual(bar_1_2("~originalyear"), "2005")
        self.failUnlessEqual(bar_1_2("~#originalyear"), 2005)
        self.failUnlessEqual(bar_1_1("~#originalyear", 1999), 1999)

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
            self.failUnlessEqual(song("~title~~#tracks"), song("~title~~#tracks"))

    def test_call_numeric(self):
        self.failUnlessAlmostEqual(num_call("~#custom"), 0.3)
        self.failUnlessEqual(num_call("~#blah~foo", 0), 0)

    def test_list(self):
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1.list(key), [bar_1_1(key)])

        self.failUnlessEqual(quux.list("artist"), [])
        self.failUnlessEqual(quux.list("title"), [quux("title")])
        self.failUnlessEqual(quux.list("not a key"), [])

        self.failUnlessEqual(len(bar_2_1.list("artist")), 2)
        self.failUnlessEqual(bar_2_1.list("artist"),
                             bar_2_1["artist"].split("\n"))

    def test_list_separate(self):
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1.list_separate(key), [bar_1_1(key)])

        self.failUnlessEqual(bar_2_1.list_separate("~artist~album"),
             ['Foo - Bar', 'I have two artists - Bar'])

        self.failUnlessEqual(bar_2_1.list_separate("~artist~~#track"),
             ['Foo - 1', 'I have two artists - 1'])

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
        b.pop('~filename')
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
        num = len(set(bar_1_1.keys()) | INTERN_NUM_DEFAULT)
        self.failUnlessEqual(dump.count("\n"), num + 2)
        for key, value in bar_1_1.items():
            self.failUnless(key in dump)
            self.failUnless(value in dump)
        for key in INTERN_NUM_DEFAULT:
            self.failUnless(key in dump)

        n = AudioFile()
        n.from_dump(dump)
        self.failUnless(set(dump.split("\n")) == set(n.to_dump().split("\n")))

    def test_to_dump_long(self):
        b = AudioFile(bar_1_1); b["~#length"] = 200000000000L
        dump = b.to_dump()
        num = len(set(bar_1_1.keys()) | INTERN_NUM_DEFAULT)
        self.failUnlessEqual(dump.count("\n"), num + 2)

        n = AudioFile()
        n.from_dump(dump)
        self.failUnless(set(dump.split("\n")) == set(n.to_dump().split("\n")))

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
        album_key_tests = [
            ({}, ('', '')),
            ({'album': 'foo'}, (('foo',), '')),
            ({'labelid': 'foo'}, ('', 'foo')),
            ({'musicbrainz_albumid': 'foo'}, ('', 'foo')),
            ({'album': 'foo', 'labelid': 'bar'}, (('foo',), 'bar')),
            ({'album': 'foo', 'labelid': 'bar', 'musicbrainz_albumid': 'quux'},
                (('foo',), 'bar'))
            ]
        for tags, expected in album_key_tests:
            afile = AudioFile(**tags)
            afile.sanitize('/dir/fn')
            self.failUnlessEqual(afile.album_key, expected)

    def test_album_id_values(self):
        album_key_tests = [
            ({}, {}),
            ({'album': 'foo'}, None),
            ({'labelid': 'foo'}, None),
            ({'musicbrainz_albumid': 'foo'}, None),
            ({'album': 'foo', 'labelid': 'bar'}, {'labelid': 'bar'}),
            # Musicbrainz is our current "favourite" tag
            ({'album': 'foo', 'labelid': 'bar', 'musicbrainz_albumid': 'quux'},
                    {'musicbrainz_albumid': 'quux'}),
            # albumartist > album in this case
            ({'album': 'foo', 'albumartist': 'bar', 'artist': 'baz'},
                    {'album': 'foo', 'albumartist': 'bar'}),
            # Fail as there's nothing to specify the album
            ({'albumartist': 'bar', 'artist': 'baz', 'title': 'foo'}, {})
            ]
        for tags, expected in album_key_tests:
            if expected is None: expected = tags
            afile = AudioFile(**tags)
            afile.sanitize('/dir/fn')
            self.failUnlessEqual(afile.album_id_values, HashableDict(expected))

    def test_album_id_values_with_artist(self):
        album_key_tests = [
            # The artist should now appear
            ({'album': 'foo', 'artist': 'bar', 'title': 'baz'},
                    {'album': 'foo', 'artist': 'bar'}),
            # But albumartist > album still
            ({'album': 'foo', 'albumartist': 'bar', 'artist': 'baz'},
                    {'album': 'foo', 'albumartist': 'bar'}),
            ]
        for tags, expected in album_key_tests:
            if expected is None: expected = tags
            afile = AudioFile(**tags)
            afile.sanitize('/dir/fn')
            # Use alternate version, that includes artist in dict
            self.failUnlessEqual(afile._album_id_values(True),
                                 HashableDict(expected))

    def test_eq_ne(self):
        self.failIf(AudioFile({"a": "b"}) == AudioFile({"a": "b"}))
        self.failUnless(AudioFile({"a": "b"}) != AudioFile({"a": "b"}))

    def test_invalid_fs_encoding(self):
        # issue 798
        a = AudioFile()
        a.sanitize("/\xf6\xe4\xfc/\xf6\xe4\xfc.ogg") # latin 1 encoded
        a.sort_by_func("~filename")(a)
        a.sort_by_func("~basename")(a)
        a.sort_by_func("~dirname")(a)

        # windows
        a.sanitize("/\xf6\xe4\xfc/\xf6\xe4\xfc.ogg".decode("latin-1"))
        a.sort_by_func("~filename")(a)
        a.sort_by_func("~basename")(a)
        a.sort_by_func("~dirname")(a)

    def test_sort_cache(self):
        copy = AudioFile(bar_1_1)

        sort_1 = tuple(copy.sort_key)
        copy["title"] = copy["title"] + "something"
        sort_2 = tuple(copy.sort_key)
        self.failIfEqual(sort_1, sort_2)

        album_sort_1 = tuple(copy.album_key)
        copy["album"] = copy["album"] + "something"
        sort_3 = tuple(copy.sort_key)
        self.failIfEqual(sort_2, sort_3)

        album_sort_2 = tuple(copy.album_key)
        self.failIfEqual(album_sort_1, album_sort_2)

    def test_cache_attributes(self):
        x = AudioFile()
        x.multisong = not x.multisong
        x["a"] = "b" # clears cache
        # attribute should be unchanged
        self.failIfEqual(AudioFile().multisong, x.multisong)

    def test_sort_func(self):
        tags = [lambda s: s("foo"), "artistsort", "albumsort",
                "~filename", "~format", "discnumber", "~#track"]

        for tag in tags:
            f = AudioFile.sort_by_func(tag)
            f(bar_1_1)
            f(bar_1_2)
            f(bar_2_1)

    def test_uri(self):
        # On windows where we have unicode paths (windows encoding is utf-16)
        # we need to encode to utf-8 first, then escape.
        # On linux we take the byte stream and escape it.
        # see g_filename_to_uri

        f = AudioFile({"~filename": "/\x87\x12.mp3", "title": "linux"})
        self.failUnlessEqual(f("~uri"), "file:///%87%12.mp3")

        f = AudioFile({"~filename": u"/\xf6\xe4.mp3", "title": "win"})
        self.failUnlessEqual(f("~uri"), "file:///%C3%B6%C3%A4.mp3")

    def tearDown(self):
        os.unlink(quux["~filename"])
add(TAudioFile)

class Treplay_gain(TestCase):

    # -6dB is approximately equal to half magnitude
    minus_6db = 0.501187234

    def setUp(self):
        self.rg_data = {"replaygain_album_gain": "-1.00 dB",
                        "replaygain_album_peak": "1.1",
                        "replaygain_track_gain": "+1.0000001 dB",
                        "replaygain_track_peak": "0.9"}
        self.song = AudioFile(self.rg_data)

    def test_nogain(self):
        self.failUnlessEqual(self.song.replay_gain(["none", "track"]), 1)

    def test_fallback_track(self):
        del(self.song["replaygain_track_gain"])
        self.failUnlessAlmostEqual(
            self.song.replay_gain(["track"], 0, -6.0), self.minus_6db)

    def test_fallback_album(self):
        del(self.song["replaygain_album_gain"])
        self.failUnlessAlmostEqual(
            self.song.replay_gain(["album"], 0, -6.0), self.minus_6db)

    def test_fallback_and_preamp(self):
        del(self.song["replaygain_track_gain"])
        self.failUnlessEqual(self.song.replay_gain(["track"], 9, -9), 1)

    def test_preamp_track(self):
        self.failUnlessAlmostEqual(
            self.song.replay_gain(["track"], -7.0, 0), self.minus_6db)

    def test_preamp_album(self):
        self.failUnlessAlmostEqual(
            self.song.replay_gain(["album"], -5.0, 0), self.minus_6db)

    def test_preamp_clip(self):
        # Make sure excess pre-amp won't clip a track (with peak data)
        self.failUnlessAlmostEqual(
            self.song.replay_gain(["track"], 12.0, 0), 1.0 / 0.9)

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

    def test_numeric_rg_tags(self):
        """"Tests fully-numeric (ie no "db") RG tags.  See Issue 865"""
        self.failUnless(self.song("replaygain_album_gain"), "-1.00 db")
        for key, exp in self.rg_data.items():
            # Hack the nasties off and produce the "real" expected value
            exp = float(exp.split(" ")[0])
            # Compare as floats. Seems fairer.
            album_rg = self.song("~#%s" % key)
            try:
                val = float(album_rg)
            except ValueError: self.fail("Invalid %s returned: %s" %
                                         (key,album_rg))
            self.failUnlessAlmostEqual(val, exp, places=5,
                                 msg="%s should be %s not %s" % (key,exp,val))
add(Treplay_gain)

# Special test case for find_cover since it has to create/remove
# various files.
class Tfind_cover(TestCase):
    def setUp(self):
        config.init()
        self.dir = os.path.realpath(quux("~dirname"))
        self.files = [self.full_path("12345.jpg"),
                      self.full_path("nothing.jpg")
                      ]
        for f in self.files: file(f, "w").close()

    def full_path(self, path):
        return os.path.join(self.dir, path)

    def test_dir_not_exist(self):
        self.failIf(bar_2_1.find_cover())

    def test_nothing(self):
        self.failIf(quux.find_cover())

    def test_labelid(self):
        quux["labelid"] = "12345"
        self.failUnlessEqual(os.path.abspath(quux.find_cover().name),
                             self.full_path("12345.jpg"))
        del(quux["labelid"])

    def test_regular(self):
        files = [os.path.join(self.dir, f) for f in
                 ["cover.png", "folder.jpg", "frontcover.jpg",
                  "front_folder_cover.gif", "jacket_cover.front.folder.jpeg"]]
        for f in files:
            file(f, "w").close()
            self.files.append(f)
            self.failUnlessEqual(os.path.abspath(quux.find_cover().name), f)
        self.test_labelid() # labelid must work with other files present

    def test_intelligent(self):
        song = quux
        song["artist"] = "Q-Man"
        song["title"] = "First Q falls hardest"
        files = [self.full_path(f) for f in
                 ["Quuxly - back.jpg", "Quuxly.jpg", "q-man - quxxly.jpg",
                  "folder.jpeg", "Q-man - Quuxly (FRONT).jpg"]]
        for f in files:
            file(f, "w").close()
            self.files.append(f)
            cover = song.find_cover()
            if cover:
                actual = os.path.abspath(cover.name)
                self.failUnlessEqual(actual, f)
            else:
                # Here, no cover is better than the back...
                self.failUnlessEqual(f, self.full_path("Quuxly - back.jpg"))

    def test_embedded_special_cover_words(self):
        """Tests that words incidentally containing embedded "special" words 
        album keywords (e.g. cover, disc, back) don't trigger
        See Issue 818"""

        song = AudioFile({
            "~filename": "tests/data/asong.ogg",
            "album": "foobar",
            "title": "Ode to Baz",
            "artist": "Q-Man",
        })
        files = [self.full_path(f) for f in
                 ['back.jpg',
                  'discovery.jpg', "Pharell - frontin'.jpg",
                  'nickelback - Curb.jpg',
                  'foobar.jpg', 'folder.jpg',     # Though this is debatable
                  'Q-Man - foobar.jpg', 'Q-man - foobar (cover).jpg']]
        for f in files:
            file(f, "w").close()
            self.files.append(f)
            cover = song.find_cover()
            if cover:
                actual = os.path.abspath(cover.name)
                self.failUnlessEqual(actual, f,
                                     "\"%s\" should trump \"%s\"" % (f, actual))
            else:
                self.failUnless(f, self.full_path('back.jpg'));

    def tearDown(self):
        map(os.unlink, self.files)
        config.quit()
add(Tfind_cover)
