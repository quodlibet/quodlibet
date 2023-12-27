# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import os
import shutil
import time
from contextlib import contextmanager
from tempfile import mkstemp, mkdtemp

from quodlibet import config, app
from quodlibet.formats import AudioFile, types as format_types, AudioFileError
from quodlibet.formats import decode_value, MusicFile, FILESYSTEM_TAGS
from quodlibet.formats._audio import NUMERIC_ZERO_DEFAULT, TIME_TAGS
from quodlibet.util.environment import is_windows
from quodlibet.util.path import (normalize_path, mkdir, get_home_dir, unquote,
                                 escape_filename, RootPathFile)
from quodlibet.util.string.date import format_date
from quodlibet.util.tags import _TAGS as TAGS
from senf import fsnative, fsn2text, bytes2fsn
from tests import TestCase, get_data_path, init_fake_app, destroy_fake_app
from .helper import temp_filename

bar_1_1 = AudioFile({
    "~filename": fsnative("/fakepath/1"),
    "title": "A song",
    "discnumber": "1/2", "tracknumber": "1/3",
    "artist": "Foo", "album": "Bar"})
bar_1_2 = AudioFile({
    "~filename": fsnative("/fakepath/2"),
    "title": "Perhaps another",
    "titlesort": "Titles don't sort",
    "discnumber": "1", "tracknumber": "2/3",
    "artist": "Lali-ho!", "album": "Bar",
    "date": "2004-12-12", "originaldate": "2005-01-01",
    "~#filesize": 1024 ** 2, "~#bitrate": 128})
bar_2_1 = AudioFile({
    "~filename": fsnative("/does not/exist"),
    "title": "more songs",
    "discnumber": "2/2", "tracknumber": "1",
    "artist": "Foo\nI have two artists",
    "artistsort": "Foosort\n\nThird artist",
    "album": "Bar",
    "lyricist": "Foo", "composer": "Foo", "performer": "I have two artists"})
bar_va = AudioFile({
    "~filename": "/fakepath/3",
    "title": "latest",
    "artist": "Foo\nI have two artists",
    "album": "Bar",
    "language": "de\neng",
    "albumartist": "Various Artists",
    "performer": "Jay-Z",
    "producer": "Kanye West"})

num_call = AudioFile({"custom": "0.3"})
ANOTHER_RATING = 0.2
SOME_RATING = 0.8


class TAudioFile(TestCase):

    def setUp(self):
        # Need the playlists library now
        init_fake_app()
        config.RATINGS = config.HardCodedRatingsPrefs()
        fd, filename = mkstemp()
        os.close(fd)
        self.quux = AudioFile({
            "~filename": normalize_path(filename, True),
            "album": "Quuxly"
        })

    def tearDown(self):
        destroy_fake_app()
        try:
            os.unlink(self.quux["~filename"])
        except OSError:
            pass

    def test_format_type(self):
        for t in format_types:
            i = AudioFile.__new__(t)
            assert isinstance(i("~format"), str)

    def test_tag_strs(self):
        for t in format_types:
            i = AudioFile.__new__(t)
            i["~filename"] = fsnative("foo")
            for tag in TAGS.values():
                name = tag.name
                # brute force
                variants = [
                    name, "~" + name, name + "sort", "~" + name + "sort",
                    name + ":role", "~" + name + ":role",
                    "~" + name + "sort:role", name + "sort:role",
                ]
                for name in variants:
                    if name in FILESYSTEM_TAGS:
                        assert isinstance(i(name, fsnative()), fsnative)
                    else:
                        assert isinstance(i(name), str)

    def test_sort(self):
        l = [self.quux, bar_1_2, bar_2_1, bar_1_1]
        l.sort()
        self.assertEqual(l, [bar_1_1, bar_1_2, bar_2_1, self.quux])
        self.assertEqual(self.quux, self.quux)
        self.assertEqual(bar_1_1, bar_1_1)
        self.assertNotEqual(bar_2_1, bar_1_2)

    def test_realkeys(self):
        self.assertFalse("artist" in self.quux.realkeys())
        self.assertFalse("~filename" in self.quux.realkeys())
        self.assertTrue("album" in self.quux.realkeys())

    def test_iterrealitems(self):
        af = AudioFile({
            "~filename": fsnative("foo"),
            "album": "Quuxly"
        })
        assert list(af.iterrealitems()) == [("album", "Quuxly")]

    def test_language(self):
        self.assertEqual(bar_va("~language"), "German\nEnglish")
        self.assertEqual(bar_va.list("~language"), ["German", "English"])
        self.assertEqual(bar_1_1("~language", default="foo"), "foo")
        self.assertEqual(bar_1_1.list("~language"), [])

    def test_trackdisc(self):
        self.assertEqual(bar_1_1("~#track"), 1)
        self.assertEqual(bar_1_1("~#disc"), 1)
        self.assertEqual(bar_1_1("~#tracks"), 3)
        self.assertEqual(bar_1_1("~#discs"), 2)
        self.assertFalse(bar_1_2("~#discs"))
        self.assertFalse(bar_2_1("~#tracks"))

    def test_setitem_keys(self):
        af = AudioFile()
        af["foo"] = "bar"
        assert "foo" in af
        assert isinstance(list(af.keys())[0], str)
        af.clear()
        af["öäü"] = "bar"
        assert "öäü" in af
        assert isinstance(list(af.keys())[0], str)

        with self.assertRaises(TypeError):
            af[42] = "foo"

        with self.assertRaises(TypeError):
            af[b"foo"] = "bar"

    def test_call(self):
        # real keys should lookup the same
        for key in bar_1_1.realkeys():
            self.assertEqual(bar_1_1[key], bar_1_1(key))

        # fake/generated key checks
        af = AudioFile()
        self.assertFalse(af("not a key"))
        self.assertEqual(af("not a key", "foo"), "foo")
        self.assertEqual(af("artist"), "")

        assert self.quux("~basename")
        assert self.quux("~dirname") == os.path.dirname(self.quux("~filename"))
        assert self.quux("title") == \
            "%s [untitled Unknown Audio File]" % fsn2text(self.quux("~basename"))

        self.assertEqual(bar_1_1("~#disc"), 1)
        self.assertEqual(bar_1_2("~#disc"), 1)
        self.assertEqual(bar_2_1("~#disc"), 2)
        self.assertEqual(bar_1_1("~#track"), 1)
        self.assertEqual(bar_1_2("~#track"), 2)
        self.assertEqual(bar_2_1("~#track"), 1)

    def test_year(self):
        self.assertEqual(bar_1_2("~year"), "2004")
        self.assertEqual(bar_1_2("~#year"), 2004)
        self.assertEqual(bar_1_1("~#year", 1999), 1999)

    def test_filesize(self):
        self.assertEqual(bar_1_2("~filesize"), "1.00 MB")
        self.assertEqual(bar_1_2("~#filesize"), 1024 ** 2)
        assert isinstance(bar_1_2("~filesize"), str)

    def test_bitrate(self):
        self.assertEqual(bar_1_2("~#bitrate"), 128)
        self.assertEqual(bar_1_2("~bitrate"), "128 kbps")

    def test_originalyear(self):
        self.assertEqual(bar_1_2("~originalyear"), "2005")
        self.assertEqual(bar_1_2("~#originalyear"), 2005)
        self.assertEqual(bar_1_1("~#originalyear", 1999), 1999)

    def test_call_people(self):
        af = AudioFile()
        self.assertEqual(af("~people"), "")
        self.assertEqual(bar_1_1("~people"), "Foo")
        self.assertEqual(bar_1_2("~people"), "Lali-ho!")
        self.assertEqual(bar_2_1("~people"), "Foo\nI have two artists")
        # See Issue 1034
        expected = "Foo\nI have two artists\nVarious Artists\nJay-Z\nKanye West"
        assert bar_va("~people") == expected

    def test_call_multiple(self):
        for song in [self.quux, bar_1_1, bar_2_1]:
            self.assertEqual(song("~~people"), song("~people"))
            self.assertEqual(song("~title~people"), song("title"))
            self.assertEqual(
                song("~title~~people"), song("~title~artist"))

    def test_tied_filename_numeric(self):
        self.assertEqual(
            bar_1_2("~~filename~~#originalyear"), "/fakepath/2 - 2005")

    def test_call_numeric(self):
        self.assertAlmostEqual(num_call("~#custom"), 0.3)
        self.assertEqual(num_call("~#blah~foo", 0), 0)

    def test_list(self):
        for key in bar_1_1.realkeys():
            self.assertEqual(bar_1_1.list(key), [bar_1_1(key)])

        af = AudioFile({"~filename": fsnative("foo")})
        self.assertEqual(af.list("artist"), [])
        self.assertEqual(af.list("title"), [af("title")])
        self.assertEqual(af.list("not a key"), [])

        self.assertEqual(len(bar_2_1.list("artist")), 2)
        self.assertEqual(bar_2_1.list("artist"),
                             bar_2_1["artist"].split("\n"))

    def test_list_tied_tags(self):
        expected = ["{} - {}".format(bar_1_1("artist"), bar_1_1("title"))]
        self.assertEqual(bar_1_1.list("~artist~title"), expected)

    def test_list_multiple_tied_tags(self):
        expected = ["{} - {}".format(bar_2_1.comma("artist"), bar_2_1("title"))]
        self.assertEqual(bar_2_1.list("~artist~title"), expected)

    def test_list_sort(self):
        self.assertEqual(bar_1_1.list_sort("title"),
                             [("A song", "A song")])
        self.assertEqual(bar_1_1.list_sort("artist"),
                             [("Foo", "Foo")])

        af = AudioFile({"~filename": fsnative("foo")})
        self.assertEqual(af.list_sort("artist"), [])
        self.assertEqual(af.list_sort("title"),
                             [(af("title"), af("title"))])
        self.assertEqual(af.list_sort("not a key"), [])

        self.assertEqual(bar_1_2.list_sort("title"),
                             [("Perhaps another", "Perhaps another")])
        self.assertEqual(bar_2_1.list_sort("artist"),
                             [("Foo", "Foosort"),
                              ("I have two artists", "I have two artists")])
        self.assertEqual(bar_2_1.list_sort("~#track"),
                             [("1", "1")])

    def test_list_sort_empty_sort(self):
        # we don't want to care about empty sort values, make sure we ignore
        # them
        s = AudioFile({"artist": "x\ny\nz", "artistsort": "c\n\nd"})
        self.assertEqual(
            s.list_sort("artist"), [("x", "c"), ("y", "y"), ("z", "d")])

    def test_list_sort_noexist(self):
        self.assertEqual(bar_1_1.list_sort("nopenopenope"), [])

    def test_list_separate_noexist(self):
        self.assertEqual(bar_1_1.list_separate("nopenopenope"), [])

    def test_list_sort_length_diff(self):
        s = AudioFile({"artist": "a\nb", "artistsort": "c"})
        self.assertEqual(s.list_sort("artist"), [("a", "c"), ("b", "b")])

        s = AudioFile({"artist": "a\nb", "artistsort": "c\nd\ne"})
        self.assertEqual(s.list_sort("artist"), [("a", "c"), ("b", "d")])

        s = AudioFile({"artistsort": "c\nd\ne"})
        self.assertEqual(s.list_sort("artist"), [])

        s = AudioFile({"artist": "a\nb"})
        self.assertEqual(s.list_sort("artist"), [("a", "a"), ("b", "b")])

        s = AudioFile({})
        self.assertEqual(s.list_sort("artist"), [])

    def test_list_separate(self):
        self.assertEqual(bar_1_1.list_separate("title"),
                             [("A song", "A song")])
        self.assertEqual(bar_1_1.list_separate("artist"),
                             [("Foo", "Foo")])

        self.assertEqual(bar_2_1.list_separate("~artist~album"),
                             [("Foo", "Foosort"),
                              ("I have two artists", "I have two artists"),
                              ("Bar", "Bar")])

        self.assertEqual(bar_2_1.list_separate("~artist~~#track"),
                             [("Foo", "Foosort"),
                              ("I have two artists", "I have two artists"),
                              ("1", "1")])

    def test_list_list_separate_types(self):
        res = bar_2_1.list_separate("~~#track~artist~~filename")
        self.assertEqual(res, [("1", "1"), ("Foo", "Foosort"),
                               ("I have two artists", "I have two artists"),
                               ("/does not/exist", "/does not/exist")])

    def test_list_numeric(self):
        self.assertEqual(bar_1_2.list("~#bitrate"), [128])

    def test_comma(self):
        for key in bar_1_1.realkeys():
            self.assertEqual(bar_1_1.comma(key), bar_1_1(key))
        self.assertTrue(", " in bar_2_1.comma("artist"))

    def test_comma_filename(self):
        self.assertTrue(isinstance(bar_1_1.comma("~filename"), str))

    def test_comma_mountpoint(self):
        assert not bar_1_1("~mountpoint")
        assert isinstance(bar_1_1.comma("~mountpoint"), str)
        assert bar_1_1.comma("~mountpoint") == ""

    def test_exist(self):
        self.assertFalse(bar_2_1.exists())
        self.assertTrue(self.quux.exists())

    def test_valid(self):
        self.assertFalse(bar_2_1.valid())

        quux = self.quux
        quux["~#mtime"] = 0
        self.assertFalse(quux.valid())
        quux["~#mtime"] = os.path.getmtime(quux["~filename"])
        self.assertTrue(quux.valid())
        os.utime(quux["~filename"], (quux["~#mtime"], quux["~#mtime"] - 1))
        self.assertFalse(quux.valid())
        quux["~#mtime"] = os.path.getmtime(quux["~filename"])
        self.assertTrue(quux.valid())

        os.utime(quux["~filename"], (quux["~#mtime"], quux["~#mtime"] - 1))
        quux.sanitize()
        self.assertTrue(quux.valid())

    def test_can_change(self):
        af = AudioFile()
        self.assertFalse(af.can_change("~foobar"))
        self.assertFalse(af.can_change("=foobar"))
        self.assertFalse(af.can_change("foo=bar"))
        self.assertFalse(af.can_change(""))
        self.assertTrue(af.can_change("foo bar"))

    def test_is_writable(self):
        fn = self.quux["~filename"]
        os.chmod(fn, 0o444)
        assert not self.quux.is_writable(), f"{fn!r} is writeable ({os.stat(fn)})"
        os.chmod(fn, 0o644)
        assert self.quux.is_writable(), f"{fn!r} is unwriteable ({os.stat(fn)})"

    def test_can_multiple_values(self):
        af = AudioFile()
        self.assertEqual(af.can_multiple_values(), True)
        self.assertTrue(af.can_multiple_values("artist"))

    def test_rename(self):
        old_fn = self.quux["~filename"]

        fd, new_fn = mkstemp()
        os.close(fd)
        os.unlink(new_fn)

        assert self.quux.exists()
        self.quux.rename(new_fn)
        assert not os.path.exists(old_fn)
        assert self.quux.exists()
        self.quux.rename(old_fn)
        assert not os.path.exists(new_fn)
        assert self.quux.exists()

    def test_rename_other_dir(self):
        old_fn = self.quux["~filename"]
        new_dir = mkdtemp()
        self.quux.rename(os.path.join(new_dir, "foo"))
        assert not os.path.exists(old_fn)
        assert self.quux.exists()
        self.quux.rename(old_fn)
        assert self.quux.exists()
        os.rmdir(new_dir)

    def test_rename_to_existing(self):
        self.quux.rename(self.quux("~filename"))
        if os.name != "nt":
            self.assertRaises(
                ValueError, self.quux.rename, fsnative("/dev/null"))

        with temp_filename() as new_file:
            with self.assertRaises(ValueError):
                self.quux.rename(new_file)

    def test_playlists_tag(self):
        songs_lib = app.library
        pl_name = "playlist 123!"
        songs_lib.add([bar_1_1, bar_1_2, self.quux])
        pl_lib = songs_lib.playlists
        pl = pl_lib.create(pl_name)
        pl.extend([self.quux, bar_1_1])
        assert pl, "Nothing added to playlist"
        for song in pl:
            assert song("~playlists") == pl_name
        assert not bar_1_2("~playlists")

    def test_lyric_filename(self):
        song = AudioFile()
        song["~filename"] = fsnative("filename")
        self.assertTrue(isinstance(song.lyric_filename, fsnative))
        song["title"] = "Title"
        song["artist"] = "Artist"
        self.assertTrue(isinstance(song.lyric_filename, fsnative))
        song["lyricist"] = "Lyricist"
        self.assertTrue(isinstance(song.lyric_filename, fsnative))

    def lyric_filename_search_test_song(self, pathfile):
        s = AudioFile()
        s.sanitize(pathfile)
        s["artist"] = "SpongeBob SquarePants"
        s["title"] = "Theme Tune"
        return s

    @contextmanager
    def lyric_filename_test_setup(self, no_config=False):

        with temp_filename() as filename:
            s = self.lyric_filename_search_test_song(filename)
            root = os.path.dirname(filename)

            if not no_config:
                config.set("memory", "lyric_filenames",
                           "<artist>.-.<title>,<artist> - <title>.lyrics_mod")
            config.set("memory", "lyric_rootpaths", root)

            s.root = root
            yield s

            if not no_config:
                self.lyric_filename_search_clean_config()

    def lyric_filename_search_clean_config(self):
        """reset config to ensure other tests aren't affected"""
        config.remove_option("memory", "lyric_rootpaths")
        config.remove_option("memory", "lyric_filenames")

    def test_lyric_filename_search_builtin_default(self):
        """test built-in default"""
        with self.lyric_filename_test_setup(no_config=True) as ts:
            fp = os.path.join(ts.root, ts["artist"], ts["title"] + ".lyric")
            p = os.path.dirname(fp)
            mkdir(p)
            with open(fp, "w", encoding="utf-8") as f:
                f.write("")
            search = unquote(ts.lyric_filename)
            os.remove(fp)
            os.rmdir(p)
            self.assertEqual(search, fp)

    def test_lyric_filename_search_builtin_default_local_path(self):
        """test built-in default local path"""
        with self.lyric_filename_test_setup(no_config=True) as ts:
            fp = os.path.join(ts.root, ts["artist"] + " - " +
                              ts["title"] + ".lyric")
            with open(fp, "w", encoding="utf-8") as f:
                f.write("")
            search = ts.lyric_filename
            os.remove(fp)
            if is_windows():
                fp = fp.lower()  # account for 'os.path.normcase' santisatation
                search = search.lower()  # compensate for the above
            self.assertEqual(search, fp)

    def test_lyric_filename_search_file_not_found(self):
        """test default file not found fallback"""
        with self.lyric_filename_test_setup() as ts:
            fp = os.path.join(ts.root, ts["artist"] + ".-." + ts["title"])
            search = unquote(ts.lyric_filename)
            self.assertEqual(search, fp)

    def test_lyric_filename_search_custom_path(self):
        """test custom lyrics file location / naming"""
        with self.lyric_filename_test_setup() as ts:
            fp = os.path.join(ts.root, ts["artist"] + " - " +
                              ts["title"] + ".lyric")
            with open(fp, "w", encoding="utf-8") as f:
                f.write("")
            search = ts.lyric_filename
            os.remove(fp)
            self.assertEqual(search, fp)

    def test_lyric_filename_search_order_priority(self):
        """test custom lyrics order priority"""
        with self.lyric_filename_test_setup() as ts:
            root2 = os.path.join(get_home_dir(), ".lyrics") # built-in default
            fp2 = os.path.join(root2, ts["artist"] + " - " +
                                      ts["title"] + ".lyric")
            p2 = os.path.dirname(fp2)
            mkdir(p2)
            with open(fp2, "w", encoding="utf-8") as f:
                f.write("")
            fp = os.path.join(ts.root, ts["artist"] + " - " +
                                       ts["title"] + ".lyric")
            with open(fp, "w", encoding="utf-8") as f:
                f.write("")
            mkdir(p2)
            search = ts.lyric_filename
            os.remove(fp2)
            os.rmdir(p2)
            os.remove(fp)
            self.assertEqual(search, fp)

    def test_lyric_filename_search_modified_extension_fallback(self):
        """test modified extension fallback search"""
        with self.lyric_filename_test_setup() as ts:
            fp = os.path.join(ts.root,
                              ts["artist"] + " - " + ts["title"] + ".txt")
            with open(fp, "w", encoding="utf-8") as f:
                f.write("")
            search = ts.lyric_filename
            os.remove(fp)
            self.assertEqual(search, fp)

    def test_lyric_filename_search_special_characters(self):
        """test '<' and/or '>' in name (not parsed (transparent to test))"""
        with self.lyric_filename_test_setup(no_config=True) as ts:

            path_variants = ["<oldskool>"] \
                if is_windows() else [r"\<artist\>", r"\<artist>",
                                      r"<artist\>"]

            for path_variant in path_variants:
                ts["artist"] = path_variant + " SpongeBob SquarePants"
                parts = [ts.root,
                         ts["artist"] + " - " + ts["title"] + ".lyric"]
                rpf = RootPathFile(ts.root, os.path.sep.join(parts))
                if not rpf.valid:
                    rpf = RootPathFile(rpf.root, rpf.pathfile_escaped)
                self.assertTrue(rpf.valid,
                                "even escaped target file is not valid")
                with open(rpf.pathfile, "w", encoding="utf-8") as f:
                    f.write("")
                search = ts.lyric_filename
                os.remove(rpf.pathfile)
                fp = rpf.pathfile
                if is_windows():
                    # account for 'os.path.normcase' santisatation
                    fp = fp.lower()
                    search = search.lower() # compensate for the above
                self.assertEqual(search, fp)

    def test_lyric_filename_search_special_characters_across_path(self):
        """test '<' and/or '>' in name across path separator (not parsed
        (transparent to test))"""
        with self.lyric_filename_test_setup(no_config=True) as ts:
            # test '<' and '>' in name across path
            # (not parsed (transparent to test))
            ts["artist"] = "a < b"
            ts["title"] = "b > a"
            parts = [ts.root, ts["artist"], ts["title"] + ".lyric"]
            rpf = RootPathFile(ts.root, os.path.sep.join(parts))
            rootp = ts.root
            rmdirs = []
            # ensure valid dir existence
            for p in rpf.end.split(os.path.sep)[:-1]:
                rootp = os.path.sep.join([ts.root, p])
                if not RootPathFile(ts.root, rootp).valid:
                    rootp = os.path.sep.join([ts.root, escape_filename(p)])
                self.assertTrue(RootPathFile(ts.root, rootp).valid,
                                "even escaped target dir part is not valid!")
                if not os.path.exists(rootp):
                    mkdir(rootp)
                    rmdirs.append(rootp)

            if not rpf.valid:
                rpf = RootPathFile(rpf.root, rpf.pathfile_escaped)

            with open(rpf.pathfile, "w", encoding="utf-8") as f:
                f.write("")
            # search for lyric file
            search = ts.lyric_filename
            # clean up test lyric file / path
            os.remove(rpf.pathfile)
            for p in rmdirs:
                os.rmdir(p)
            # test whether the 'found' file is the test lyric file
            fp = rpf.pathfile
            if is_windows():
                fp = fp.lower()  # account for 'os.path.normcase' santisatation
                search = search.lower()  # compensate for the above
            self.assertEqual(search, fp)

    def test_lyrics_from_file(self):
        with temp_filename() as filename:
            af = AudioFile(artist="Motörhead", title="this: again")
            af.sanitize(filename)
            lyrics = "blah!\nblasé 😬\n"
            lyrics_dir = os.path.dirname(af.lyric_filename)
            mkdir(lyrics_dir)
            with open(af.lyric_filename, "w", encoding="utf-8") as lf:
                lf.write(str(lyrics))
            self.assertEqual(af("~lyrics").splitlines(),
                                 lyrics.splitlines())
            os.remove(af.lyric_filename)
            os.rmdir(lyrics_dir)

    def test_lyrics_mp3_is_not_a_valid_lyrics_file(self):
        # https://github.com/quodlibet/quodlibet/issues/3395
        fn = get_data_path("silence-44-s.mp3")
        with temp_filename() as filename:
            af = AudioFile(artist="bar", title="foo")
            af.sanitize(filename)
            lyrics_dir = os.path.dirname(af.lyric_filename)
            mkdir(lyrics_dir)
            try:
                with open(af.lyric_filename, "wb") as target:
                    with open(fn, "rb") as source:
                        target.write(source.read())
                assert "\0" not in af("~lyrics")
            finally:
                shutil.rmtree(lyrics_dir)

    def test_unsynced_lyrics(self):
        song = AudioFile()
        song["unsyncedlyrics"] = "lala"
        assert song("~lyrics") == "lala"
        assert song("unsyncedlyrics") == "lala"
        assert song("lyrics") != "lala"

    def test_mountpoint(self):
        song = AudioFile()
        song["~filename"] = fsnative("filename")
        song.sanitize()
        assert isinstance(song["~mountpoint"], fsnative)
        assert isinstance(song.comma("~mointpoint"), str)

    def test_sanitize(self):
        q = AudioFile(self.quux)
        b = AudioFile(bar_1_1)
        q.sanitize()
        b.pop("~filename")
        self.assertRaises(ValueError, b.sanitize)
        n = AudioFile({"artist": "foo\0bar", "title": "baz\0",
                       "~filename": fsnative("whatever")})
        n.sanitize()
        self.assertEqual(n["artist"], "foo\nbar")
        self.assertEqual(n["title"], "baz")

    def test_performers(self):
        q = AudioFile([("performer:vocals", "A"), ("performer:guitar", "B"),
                       ("performer", "C")])
        self.assertEqual(set(q.list("~performers")), {"A", "B", "C"})
        self.assertEqual(set(q.list("~performers:roles")),
                             {"A (Vocals)", "B (Guitar)", "C"})

    def test_performers_multi_value(self):
        q = AudioFile([
            ("performer:vocals", "X\nA\nY"),
            ("performer:guitar", "Y\nB\nA"),
            ("performer", "C\nB\nA"),
        ])

        self.assertEqual(
            set(q.list("~performer")), {"A", "B", "C", "X", "Y"})

        self.assertEqual(
            set(q.list("~performer:roles")), {
                    "A (Guitar, Vocals)",
                    "C",
                    "B (Guitar)",
                    "X (Vocals)",
                    "Y (Guitar, Vocals)",
                })


    def test_producer(self):
        s = AudioFile({"producer": "Kanye West"})
        assert s("producer") == "Kanye West"
        assert set(s.list("~people")) == {"Kanye West"}


    def test_people(self):
        q = AudioFile([("performer:vocals", "A"), ("performer:guitar", "B"),
                       ("performer", "C"), ("arranger", "A"),
                       ("albumartist", "B"), ("artist", "C")])
        self.assertEqual(q.list("~people"), ["C", "B", "A"])
        self.assertEqual(q.list("~people:roles"),
            ["C (Performance)", "B (Guitar)", "A (Arrangement, Vocals)"])

    def test_people_mix(self):
        q = AudioFile([
            ("performer:arrangement", "A"),
            ("arranger", "A"),
            ("performer", "A"),
            ("performer:foo", "A"),
        ])
        self.assertEqual(q.list("~people"), ["A"])
        self.assertEqual(q.list("~people:roles"),
            ["A (Arrangement, Arrangement, Foo, Performance)"])

    def test_people_multi_value(self):
        q = AudioFile([
            ("arranger", "A\nX"),
            ("performer", "A\nY"),
            ("performer:foo", "A\nX"),
        ])

        self.assertEqual(q.list("~people"), ["A", "Y", "X"])
        self.assertEqual(q.list("~people:roles"),
            ["A (Arrangement, Foo, Performance)", "Y (Performance)",
             "X (Arrangement, Foo)"])

    def test_people_individuals(self):
        q = AudioFile({"artist": "A\nX", "albumartist": "Various Artists"})
        self.assertEqual(q.list("~people:real"), ["A", "X"])

        lonely = AudioFile({"artist": "various artists", "title": "blah"})
        self.assertEqual(lonely.list("~people:real"),
                             ["various artists"])

        lots = AudioFile({"artist": "Various Artists", "albumartist": "V.A."})
        self.assertEqual(lots.list("~people:real"),
                             ["Various Artists"])

    def test_peoplesort(self):
        q = AudioFile([("performer:vocals", "The A"),
                       ("performersort:vocals", "A, The"),
                       ("performer:guitar", "The B"),
                       ("performersort:guitar", "B, The"),
                       ("performer", "The C"),
                       ("performersort", "C, The"),
                       ("albumartist", "The B"),
                       ("albumartistsort", "B, The")])
        self.assertEqual(q.list("~peoplesort"),
                             ["B, The", "C, The", "A, The"])
        self.assertEqual(q.list("~peoplesort:roles"),
            ["B, The (Guitar)", "C, The (Performance)", "A, The (Vocals)"])

    def test_blank_tag_handling_comma(self):
        q = AudioFile([("title", "A\n"),
                       ("artists", "A\n\nB\n")])
        self.assertEqual(q.comma("artists"), "A, B")
        self.assertEqual(q.comma("~title~version"), "A")

    def test_blank_tag_handling_list(self):
        q = AudioFile([("artist", "A\n\nB\n"),
                       ("performer", ""),
                       ("albumartist", "C")])
        self.assertEqual(q.list("performer"), [])
        self.assertEqual(q.list("~people"), ["A", "B", "C"])

    def test_blank_tag_handling_list_sort(self):
        q = AudioFile([("artist", "A\n\nB"),
                       ("artistsort", "\n\nY")])
        self.assertEqual(q.list_sort("artist"), [("A", "A"), ("B", "Y")])
        q = AudioFile([("artist", "A\n\nB"),
                       ("artistsort", "X\nY")])
        self.assertEqual(q.list_sort("artist"), [("A", "X"), ("B", "B")])

    def test_to_dump(self):
        dump = bar_1_1.to_dump()
        num = len(set(bar_1_1.keys()) | NUMERIC_ZERO_DEFAULT)
        self.assertEqual(dump.count(b"\n"), num + 2)
        for key, value in bar_1_1.items():
            self.assertTrue(key.encode("utf-8") in dump)
            self.assertTrue(value.encode("utf-8") in dump)
        for key in NUMERIC_ZERO_DEFAULT:
            self.assertTrue(key.encode("utf-8") in dump)

        n = AudioFile()
        n.from_dump(dump)
        self.assertTrue(
            set(dump.split(b"\n")) == set(n.to_dump().split(b"\n")))

    def test_to_dump_unicode(self):
        b = AudioFile(bar_1_1)
        b["öäü"] = "öäü"
        dump = b.to_dump()
        n = AudioFile()
        n.from_dump(dump)
        self.assertEqual(n["öäü"], "öäü")

    def test_add(self):
        song = AudioFile()
        self.assertFalse("foo" in song)
        song.add("foo", "bar")
        self.assertEqual(song["foo"], "bar")
        song.add("foo", "another")
        self.assertEqual(song.list("foo"), ["bar", "another"])

    def test_remove(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.add("foo", "another")
        song.add("foo", "one more")
        song.remove("foo", "another")
        self.assertEqual(song.list("foo"), ["bar", "one more"])
        song.remove("foo", "bar")
        self.assertEqual(song.list("foo"), ["one more"])
        song.remove("foo", "one more")
        self.assertFalse("foo" in song)

    def test_remove_unknown(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.remove("foo", "not in list")
        song.remove("nope")
        self.assertEqual(song.list("foo"), ["bar"])

    def test_remove_all(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.add("foo", "another")
        song.add("foo", "one more")
        song.remove("foo")
        self.assertFalse("foo" in song)

    def test_remove_empty(self):
        song = AudioFile()
        song.add("foo", "")
        song.remove("foo", "")
        self.assertFalse("foo" in song)

    def test_change(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.add("foo", "another")
        song.change("foo", "bar", "one more")
        self.assertEqual(song.list("foo"), ["one more", "another"])
        song.change("foo", "does not exist", "finally")
        self.assertEqual(song["foo"], "finally")
        song.change("foo", "finally", "we're done")
        self.assertEqual(song["foo"], "we're done")

    def test_bookmarks_none(self):
        self.assertEqual([], AudioFile().bookmarks)

    def test_bookmarks_simple(self):
        af = AudioFile({"~bookmark": "1:20 Mark 1"})
        self.assertEqual([(80, "Mark 1")], af.bookmarks)

    def test_bookmarks_two(self):
        af = AudioFile({"~bookmark": "1:40 Mark 2\n1:20 Mark 1"})
        self.assertEqual([(80, "Mark 1"), (100, "Mark 2")], af.bookmarks)

    def test_bookmark_invalid(self):
        af = AudioFile({"~bookmark": ("Not Valid\n1:40 Mark 2\n"
                                      "-20 Not Valid 2\n1:20 Mark 1")})
        self.assertEqual(
            [(80, "Mark 1"), (100, "Mark 2"), (-1, "Not Valid"),
             (-1, "-20 Not Valid 2")], af.bookmarks)

    def test_set_bookmarks_none(self):
        af = AudioFile({"bookmark": "foo"})
        af.bookmarks = []
        self.assertEqual([], AudioFile().bookmarks)
        self.assertFalse("~bookmark" in af)

    def test_set_bookmarks_simple(self):
        af = AudioFile()
        af.bookmarks = [(120, "A mark"), (140, "Mark twain")]
        self.assertEqual(af["~bookmark"], "2:00 A mark\n2:20 Mark twain")

    def test_set_bookmarks_invalid_value(self):
        self.assertRaises(
            ValueError, setattr, AudioFile(), "bookmarks", "huh?")

    def test_set_bookmarks_invalid_time(self):
        self.assertRaises(
            TypeError, setattr, AudioFile(), "bookmarks", [("notint", "!")])

    def test_set_bookmarks_unrealistic_time(self):
        self.assertRaises(
            ValueError, setattr, AudioFile(), "bookmarks", [(-1, "!")])

    def test_has_rating(self):
        song = AudioFile()
        self.assertFalse(song.has_rating)
        song["~#rating"] = 0.5
        self.assertTrue(song.has_rating)
        song.remove_rating()
        self.assertFalse(song.has_rating)

    def test_remove_rating(self):
        song = AudioFile()
        self.assertFalse(song.has_rating)
        song.remove_rating()
        self.assertFalse(song.has_rating)
        song["~#rating"] = 0.5
        self.assertTrue(song.has_rating)
        song.remove_rating()
        self.assertFalse(song.has_rating)

    def test_album_key(self):
        album_key_tests = [
            ({}, ("", (), ())),
            ({"album": "foo"}, ("", ("foo",), ())),
            ({"labelid": "foo"}, ("foo", (), ())),
            ({"musicbrainz_albumid": "foo"}, ("foo", (), ())),
            ({"album": "foo", "labelid": "bar"}, ("bar", ("foo",), ())),
            ({"album": "foo", "labelid": "bar", "musicbrainz_albumid": "quux"},
                ("bar", ("foo",), ())),
            ({"albumartist": "a"}, ("", (), ("a",))),
            ]
        for tags, expected in album_key_tests:
            afile = AudioFile(**tags)
            afile.sanitize(fsnative("/dir/fn"))
            self.assertEqual(afile.album_key, expected)

    def test_eq_ne(self):
        self.assertFalse(AudioFile({"a": "b"}) == AudioFile({"a": "b"}))
        self.assertTrue(AudioFile({"a": "b"}) != AudioFile({"a": "b"}))

    def test_invalid_fs_encoding(self):
        # issue 798
        a = AudioFile()
        if os.name != "nt":
            a["~filename"] = "/\xf6\xe4\xfc/\xf6\xe4\xfc.ogg" # latin 1 encoded
            a.sort_by_func("~filename")(a)
            a.sort_by_func("~basename")(a)
        else:
            # windows
            a["~filename"] = \
                b"/\xf6\xe4\xfc/\xf6\xe4\xfc.ogg".decode("latin-1")
            a.sort_by_func("~filename")(a)
            a.sort_by_func("~basename")(a)
            a.sort_by_func("~dirname")(a)

    def test_sort_key_defaults(self):
        AF = AudioFile
        assert AF().sort_key == AF({"tracknumber": "0"}).sort_key
        assert AF().sort_key != AF({"tracknumber": "1/1"}).sort_key
        assert AF().sort_key < AF({"tracknumber": "2/2"}).sort_key

        assert AF().sort_key == AF({"discnumber": "0"}).sort_key
        assert AF().sort_key != AF({"discnumber": "1/1"}).sort_key
        assert AF().sort_key < AF({"discnumber": "2/2"}).sort_key

    def test_sort_cache(self):
        copy = AudioFile(bar_1_1)

        sort_1 = tuple(copy.sort_key)
        copy["title"] = copy["title"] + "something"
        sort_2 = tuple(copy.sort_key)
        self.assertNotEqual(sort_1, sort_2)

        album_sort_1 = tuple(copy.album_key)
        copy["album"] = copy["album"] + "something"
        sort_3 = tuple(copy.sort_key)
        self.assertNotEqual(sort_2, sort_3)

        album_sort_2 = tuple(copy.album_key)
        self.assertNotEqual(album_sort_1, album_sort_2)

    def test_cache_attributes(self):
        x = AudioFile()
        x.multisong = not x.multisong
        x["a"] = "b" # clears cache
        # attribute should be unchanged
        self.assertNotEqual(AudioFile().multisong, x.multisong)

    def test_sort_func(self):
        tags = [lambda s: s("foo"), "artistsort", "albumsort",
                "~filename", "~format", "discnumber", "~#track"]

        for tag in tags:
            f = AudioFile.sort_by_func(tag)
            f(bar_1_1)
            f(bar_1_2)
            f(bar_2_1)

    def test_sort_func_custom_numeric(self):
        func = AudioFile.sort_by_func("~#year")

        files = [AudioFile({"year": "nope"}), AudioFile({"date": "2038"})]
        assert sorted(files, key=func) == files

    def test_uri(self):
        # On windows where we have unicode paths (windows encoding is utf-16)
        # we need to encode to utf-8 first, then escape.
        # On linux we take the byte stream and escape it.
        # see g_filename_to_uri

        if os.name == "nt":
            f = AudioFile({"~filename": "/\xf6\xe4.mp3", "title": "win"})
            self.assertEqual(f("~uri"), "file:///%C3%B6%C3%A4.mp3")
        else:
            f = AudioFile({
                "~filename": bytes2fsn(b"/\x87\x12.mp3", None),
                "title": "linux",
            })
            self.assertEqual(f("~uri"), "file:///%87%12.mp3")

    def test_reload(self):
        audio = MusicFile(get_data_path("silence-44-s.mp3"))
        audio["title"] = "foo"
        audio.reload()
        self.assertNotEqual(audio.get("title"), "foo")

    def test_reload_externally_modified(self):
        config.set("editing", "save_to_songs", True)
        fn = self.quux("~filename") + ".mp3"
        shutil.copy(get_data_path("silence-44-s.mp3"), fn)
        orig = MusicFile(fn)
        copy = MusicFile(fn)
        orig["~#rating"] = SOME_RATING
        copy["~#rating"] = ANOTHER_RATING
        orig.write()
        orig.reload()
        copy.reload() # should pick up the change to the file
        assert orig("~#rating") == SOME_RATING, "reloading failed"
        assert copy("~#rating") == SOME_RATING, "should have picked up external change"

    def test_reload_fail(self):
        audio = MusicFile(get_data_path("silence-44-s.mp3"))
        audio["title"] = "foo"
        audio.sanitize(fsnative("/dev/null"))
        self.assertRaises(AudioFileError, audio.reload)
        self.assertEqual(audio["title"], "foo")


class TAudioFormats(TestCase):

    def setUp(self):
        with temp_filename() as filename:
            self.filename = filename

    def test_load_non_exist(self):
        for t in format_types:
            if not t.is_file:
                continue
            self.assertRaises(AudioFileError, t, self.filename)

    def test_write_non_existing(self):
        for t in format_types:
            if not t.is_file:
                continue
            instance = AudioFile.__new__(t)
            instance.sanitize(self.filename)
            try:
                instance.write()
            except AudioFileError:
                pass

    def test_reload_non_existing(self):
        for t in format_types:
            if not t.is_file:
                continue
            instance = AudioFile.__new__(t)
            instance.sanitize(self.filename)
            try:
                instance.reload()
            except AudioFileError:
                pass


class Tdecode_value(TestCase):

    def test_main(self):
        self.assertEqual(decode_value("~#foo", 0.25), "0.25")
        self.assertEqual(decode_value("~#foo", 4), "4")
        self.assertEqual(decode_value("~#foo", "bar"), "bar")
        self.assertTrue(isinstance(decode_value("~#foo", "bar"), str))
        path = fsnative("/foobar")
        self.assertEqual(decode_value("~filename", path), fsn2text(path))

    def test_path(self):
        try:
            path = bytes2fsn(b"\xff\xff", "utf-8")
        except ValueError:
            return

        assert decode_value("~filename", path) == fsn2text(path)


class Treplay_gain(TestCase):

    # -6dB is approximately equal to half magnitude
    minus_6db = 0.501187234

    def setUp(self):
        self.rg_data = {"replaygain_album_gain": "-1.00 dB",
                        "replaygain_album_peak": "1.1",
                        "replaygain_track_gain": "+1.0000001 dB",
                        "replaygain_track_peak": "0.9"}
        self.song = AudioFile(self.rg_data)
        self.no_rg_song = AudioFile()

    def test_large(self):
        rg_data = {"replaygain_track_gain": "9999999 dB"}
        song = AudioFile(rg_data)
        assert song.replay_gain(["track"], 0, 0) == 1.0
        assert song.replay_gain([], 0, 99999999999) == 1.0

    def test_no_rg_song(self):
        scale = self.no_rg_song.replay_gain(["track"], 0, -6.0)
        self.assertAlmostEqual(scale, self.minus_6db)

        scale = self.no_rg_song.replay_gain(["track"], +10, +10)
        self.assertEqual(scale, 1.0)

        scale = self.no_rg_song.replay_gain(["track"], -16.0, +10)
        self.assertAlmostEqual(scale, self.minus_6db)

    def test_nogain(self):
        self.assertEqual(self.song.replay_gain(["none", "track"]), 1)

    def test_fallback_track(self):
        del(self.song["replaygain_track_gain"])
        self.assertAlmostEqual(
            self.song.replay_gain(["track"], 0, -6.0), self.minus_6db)

    def test_fallback_album(self):
        del(self.song["replaygain_album_gain"])
        self.assertAlmostEqual(
            self.song.replay_gain(["album"], 0, -6.0), self.minus_6db)

    def test_fallback_and_preamp(self):
        del(self.song["replaygain_track_gain"])
        self.assertEqual(self.song.replay_gain(["track"], 9, -9), 1)

    def test_preamp_track(self):
        self.assertAlmostEqual(
            self.song.replay_gain(["track"], -7.0, 0), self.minus_6db)

    def test_preamp_album(self):
        self.assertAlmostEqual(
            self.song.replay_gain(["album"], -5.0, 0), self.minus_6db)

    def test_preamp_clip(self):
        # Make sure excess pre-amp won't clip a track (with peak data)
        self.assertAlmostEqual(
            self.song.replay_gain(["track"], 12.0, 0), 1.0 / 0.9)

    def test_trackgain(self):
        self.assertTrue(self.song.replay_gain(["track"]) > 1)

    def test_albumgain(self):
        self.assertTrue(self.song.replay_gain(["album"]) < 1)

    def test_invalid(self):
        self.song["replaygain_album_gain"] = "fdsodgbdf"
        self.assertEqual(self.song.replay_gain(["album"]), 1)

    def test_track_fallback(self):
        radio_rg = self.song.replay_gain(["track"])
        del(self.song["replaygain_album_gain"])
        del(self.song["replaygain_album_peak"])
        # verify defaulting to track when album is present
        self.assertAlmostEqual(
            self.song.replay_gain(["album", "track"]), radio_rg)

    def test_numeric_rg_tags(self):
        """Tests fully-numeric (ie no "db") RG tags.  See Issue 865"""
        self.assertTrue(self.song("replaygain_album_gain"), "-1.00 db")
        for key, exp in self.rg_data.items():
            # Hack the nasties off and produce the "real" expected value
            exp = float(exp.split(" ")[0])
            # Compare as floats. Seems fairer.
            album_rg = self.song("~#%s" % key)
            try:
                val = float(album_rg)
            except ValueError:
                self.fail(f"Invalid {key} returned: {album_rg}")
            self.assertAlmostEqual(
                val, exp, places=5,
                msg=f"{key} should be {exp} not {val}")

    def test_human_time_tags(self):
        now = int(time.time())
        tags = {t: now for t in TIME_TAGS}
        tags["~filename"] = "/dev/null"
        af = AudioFile(tags)
        for t in TIME_TAGS:
            assert af(t) == now, "Numeric dates broken"
            assert af(t.replace("~#", "~")) == format_date(now), "Human date broken"
