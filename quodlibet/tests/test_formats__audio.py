# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path

import os
import io
from senf import fsnative, fsn2text, bytes2fsn, mkstemp, mkdtemp

from quodlibet import config
from quodlibet.compat import PY2, text_type, long, listkeys, PY3
from quodlibet.formats import AudioFile, types as format_types, AudioFileError
from quodlibet.formats._audio import NUMERIC_ZERO_DEFAULT
from quodlibet.formats import decode_value, MusicFile, FILESYSTEM_TAGS
from quodlibet.util.tags import _TAGS as TAGS
from quodlibet.util.path import normalize_path, mkdir, get_home_dir, unquote, \
                                escape_filename, RootPathFile

from .helper import temp_filename


bar_1_1 = AudioFile({
    "~filename": fsnative(u"/fakepath/1"),
    "title": "A song",
    "discnumber": "1/2", "tracknumber": "1/3",
    "artist": "Foo", "album": "Bar"})
bar_1_2 = AudioFile({
    "~filename": fsnative(u"/fakepath/2"),
    "title": "Perhaps another",
    "titlesort": "Titles don't sort",
    "discnumber": "1", "tracknumber": "2/3",
    "artist": "Lali-ho!", "album": "Bar",
    "date": "2004-12-12", "originaldate": "2005-01-01",
    "~#filesize": 1024 ** 2, "~#bitrate": 128})
bar_2_1 = AudioFile({
    "~filename": fsnative(u"does not/exist"),
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
    "performer": "Jay-Z"})

num_call = AudioFile({"custom": "0.3"})


class TAudioFile(TestCase):

    def setUp(self):
        config.RATINGS = config.HardCodedRatingsPrefs()
        fd, filename = mkstemp()
        os.close(fd)
        self.quux = AudioFile({
            "~filename": normalize_path(filename, True),
            "album": u"Quuxly"
        })

    def tearDown(self):
        try:
            os.unlink(self.quux["~filename"])
        except EnvironmentError:
            pass

    def test_format_type(self):
        for t in format_types:
            i = AudioFile.__new__(t)
            assert isinstance(i("~format"), text_type)

    def test_tag_text_types(self):
        for t in format_types:
            i = AudioFile.__new__(t)
            i["~filename"] = fsnative(u"foo")
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
                        assert isinstance(i(name), text_type)

    def test_sort(self):
        l = [self.quux, bar_1_2, bar_2_1, bar_1_1]
        l.sort()
        self.assertEqual(l, [bar_1_1, bar_1_2, bar_2_1, self.quux])
        self.assertEqual(self.quux, self.quux)
        self.assertEqual(bar_1_1, bar_1_1)
        self.assertNotEqual(bar_2_1, bar_1_2)

    def test_realkeys(self):
        self.failIf("artist" in self.quux.realkeys())
        self.failIf("~filename" in self.quux.realkeys())
        self.failUnless("album" in self.quux.realkeys())

    def test_iterrealitems(self):
        af = AudioFile({
            "~filename": fsnative(u"foo"),
            "album": u"Quuxly"
        })
        assert list(af.iterrealitems()) == [('album', u'Quuxly')]

    def test_language(self):
        self.assertEqual(bar_va("~language"), "German\nEnglish")
        self.assertEqual(bar_va.list("~language"), ['German', 'English'])
        self.assertEqual(bar_1_1("~language", default="foo"), "foo")
        self.assertEqual(bar_1_1.list("~language"), [])

    def test_trackdisc(self):
        self.failUnlessEqual(bar_1_1("~#track"), 1)
        self.failUnlessEqual(bar_1_1("~#disc"), 1)
        self.failUnlessEqual(bar_1_1("~#tracks"), 3)
        self.failUnlessEqual(bar_1_1("~#discs"), 2)
        self.failIf(bar_1_2("~#discs"))
        self.failIf(bar_2_1("~#tracks"))

    def test_setitem_keys(self):
        af = AudioFile()
        af[u"foo"] = u"bar"
        assert "foo" in af
        assert isinstance(listkeys(af)[0], str)
        af.clear()
        af[u"öäü"] = u"bar"
        assert u"öäü" in af
        assert isinstance(listkeys(af)[0], text_type)

        with self.assertRaises(TypeError):
            af[42] = u"foo"

        if PY3:
            with self.assertRaises(TypeError):
                af[b"foo"] = u"bar"
        else:
            with self.assertRaises(ValueError):
                af[b"\xff"] = u"bar"

    def test_call(self):
        # real keys should lookup the same
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1[key], bar_1_1(key))

        # fake/generated key checks
        af = AudioFile()
        self.failIf(af("not a key"))
        self.failUnlessEqual(af("not a key", "foo"), "foo")
        self.failUnlessEqual(af("artist"), "")

        assert self.quux("~basename")
        assert self.quux("~dirname") == os.path.dirname(self.quux("~filename"))
        assert self.quux("title") == \
            "%s [Unknown]" % fsn2text(self.quux("~basename"))

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

    def test_filesize(self):
        self.failUnlessEqual(bar_1_2("~filesize"), "1.00 MB")
        self.failUnlessEqual(bar_1_2("~#filesize"), 1024 ** 2)
        assert isinstance(bar_1_2("~filesize"), text_type)

    def test_bitrate(self):
        self.assertEqual(bar_1_2("~#bitrate"), 128)
        self.assertEqual(bar_1_2("~bitrate"), "128 kbps")

    def test_originalyear(self):
        self.failUnlessEqual(bar_1_2("~originalyear"), "2005")
        self.failUnlessEqual(bar_1_2("~#originalyear"), 2005)
        self.failUnlessEqual(bar_1_1("~#originalyear", 1999), 1999)

    def test_call_people(self):
        af = AudioFile()
        self.failUnlessEqual(af("~people"), "")
        self.failUnlessEqual(bar_1_1("~people"), "Foo")
        self.failUnlessEqual(bar_1_2("~people"), "Lali-ho!")
        self.failUnlessEqual(bar_2_1("~people"), "Foo\nI have two artists")
        # See Issue 1034
        self.failUnlessEqual(bar_va("~people"),
                             "Foo\nI have two artists\nVarious Artists\nJay-Z")

    def test_call_multiple(self):
        for song in [self.quux, bar_1_1, bar_2_1]:
            self.failUnlessEqual(song("~~people"), song("~people"))
            self.failUnlessEqual(song("~title~people"), song("title"))
            self.failUnlessEqual(
                song("~title~~people"), song("~title~artist"))

    def test_tied_filename_numeric(self):
        self.assertEqual(
            bar_1_2("~~filename~~#originalyear"), u'/fakepath/2 - 2005')

    def test_call_numeric(self):
        self.failUnlessAlmostEqual(num_call("~#custom"), 0.3)
        self.failUnlessEqual(num_call("~#blah~foo", 0), 0)

    def test_list(self):
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1.list(key), [bar_1_1(key)])

        af = AudioFile({"~filename": fsnative(u"foo")})
        self.failUnlessEqual(af.list("artist"), [])
        self.failUnlessEqual(af.list("title"), [af("title")])
        self.failUnlessEqual(af.list("not a key"), [])

        self.failUnlessEqual(len(bar_2_1.list("artist")), 2)
        self.failUnlessEqual(bar_2_1.list("artist"),
                             bar_2_1["artist"].split("\n"))

    def test_list_tied_tags(self):
        expected = ["%s - %s" % (bar_1_1("artist"), bar_1_1("title"))]
        self.failUnlessEqual(bar_1_1.list("~artist~title"), expected)

    def test_list_multiple_tied_tags(self):
        expected = ["%s - %s" % (bar_2_1.comma("artist"), bar_2_1("title"))]
        self.failUnlessEqual(bar_2_1.list("~artist~title"), expected)

    def test_list_sort(self):
        self.failUnlessEqual(bar_1_1.list_sort("title"),
                             [("A song", "A song")])
        self.failUnlessEqual(bar_1_1.list_sort("artist"),
                             [("Foo", "Foo")])

        af = AudioFile({"~filename": fsnative(u"foo")})
        self.failUnlessEqual(af.list_sort("artist"), [])
        self.failUnlessEqual(af.list_sort("title"),
                             [(af("title"), af("title"))])
        self.failUnlessEqual(af.list_sort("not a key"), [])

        self.failUnlessEqual(bar_1_2.list_sort("title"),
                             [("Perhaps another", "Perhaps another")])
        self.failUnlessEqual(bar_2_1.list_sort("artist"),
                             [("Foo", "Foosort"),
                              ("I have two artists", "I have two artists")])
        self.failUnlessEqual(bar_2_1.list_sort("~#track"),
                             [('1', '1')])

    def test_list_sort_empty_sort(self):
        # we don't want to care about empty sort values, make sure we ignore
        # them
        s = AudioFile({"artist": "x\ny\nz", "artistsort": "c\n\nd"})
        self.assertEqual(
            s.list_sort("artist"), [("x", "c"), ("y", "y"), ("z", "d")])

    def test_list_sort_noexist(self):
        self.failUnlessEqual(bar_1_1.list_sort("nopenopenope"), [])

    def test_list_separate_noexist(self):
        self.failUnlessEqual(bar_1_1.list_separate("nopenopenope"), [])

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
        self.failUnlessEqual(bar_1_1.list_separate("title"),
                             [("A song", "A song")])
        self.failUnlessEqual(bar_1_1.list_separate("artist"),
                             [("Foo", "Foo")])

        self.failUnlessEqual(bar_2_1.list_separate("~artist~album"),
                             [('Foo', 'Foosort'),
                              ('I have two artists', 'I have two artists'),
                              ('Bar', 'Bar')])

        self.failUnlessEqual(bar_2_1.list_separate("~artist~~#track"),
                             [('Foo', 'Foosort'),
                              ('I have two artists', 'I have two artists'),
                              ('1', '1')])

    def test_list_list_separate_types(self):
        res = bar_2_1.list_separate("~~#track~artist~~filename")
        self.assertEqual(res, [(u'1', u'1'), (u'Foo', u'Foosort'),
                               (u'I have two artists', u'I have two artists'),
                               (u'does not/exist', u'does not/exist')])

    def test_list_numeric(self):
        self.assertEqual(bar_1_2.list('~#bitrate'), [128])

    def test_comma(self):
        for key in bar_1_1.realkeys():
            self.failUnlessEqual(bar_1_1.comma(key), bar_1_1(key))
        self.failUnless(", " in bar_2_1.comma("artist"))

    def test_comma_filename(self):
        self.assertTrue(isinstance(bar_1_1.comma("~filename"), text_type))

    def test_comma_mountpoint(self):
        assert not bar_1_1("~mountpoint")
        assert isinstance(bar_1_1.comma("~mountpoint"), text_type)
        assert bar_1_1.comma("~mountpoint") == u""

    def test_exist(self):
        self.failIf(bar_2_1.exists())
        self.failUnless(self.quux.exists())

    def test_valid(self):
        self.failIf(bar_2_1.valid())

        quux = self.quux
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
        af = AudioFile()
        self.failIf(af.can_change("~foobar"))
        self.failIf(af.can_change("=foobar"))
        self.failIf(af.can_change("foo=bar"))
        self.failIf(af.can_change(""))
        self.failUnless(af.can_change("foo bar"))

    def test_is_writable(self):
        self.assertTrue(self.quux.is_writable())
        os.chmod(self.quux["~filename"], 0o444)
        self.assertFalse(self.quux.is_writable())
        os.chmod(self.quux["~filename"], 0o644)
        self.assertTrue(self.quux.is_writable())

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
            self.failUnlessRaises(
                ValueError, self.quux.rename, fsnative(u"/dev/null"))

        with temp_filename() as new_file:
            with self.assertRaises(ValueError):
                self.quux.rename(new_file)

    def test_lyric_filename(self):
        song = AudioFile()
        song["~filename"] = fsnative(u"filename")
        self.assertTrue(isinstance(song.lyric_filename, fsnative))
        song["title"] = u"Title"
        song["artist"] = u"Artist"
        self.assertTrue(isinstance(song.lyric_filename, fsnative))
        song["lyricist"] = u"Lyricist"
        self.assertTrue(isinstance(song.lyric_filename, fsnative))

    def test_lyric_filename_search(self):

        def assertEqual(a, b):
            # pass custom error message to avoid truncation!
            a2 = os.path.realpath(a).lower()
            b2 = os.path.realpath(b).lower()
            msg_fail = str("item1: %s !=\nitem2: %s" % (a2, b2))
            self.assertEqual(a2, b2, msg_fail)

        with temp_filename() as filename:
            s = AudioFile()
            s.sanitize(filename)

            artist = s['artist'] = "SpongeBob SquarePants"
            title = s['title'] = "Theme Tune"

            # test built-in default
            root = os.path.join(get_home_dir(), ".lyrics")
            fp = os.path.join(root, artist, title + ".lyric")
            p = os.path.dirname(fp)
            mkdir(p)
            with io.open(fp, "w", encoding='utf-8') as f:
                f.write(u"")
            search = unquote(s.lyric_filename)
            os.remove(fp)
            os.rmdir(p)
            assertEqual(search, fp)

            # test built-in default local path
            root = os.path.dirname(filename)
            fp = os.path.join(root, artist + " - " + title + ".lyric")
            with io.open(fp, "w", encoding='utf-8') as f:
                f.write(u"")
            search = s.lyric_filename
            os.remove(fp)
            assertEqual(search, fp)

            # custom lyrics file location / naming
            config.set("memory", "lyric_filenames",
                           "<artist>.-.<title>,<artist> - <title>.lyrics_mod")
            root = os.path.dirname(filename)
            config.set("memory", "lyric_rootpaths", root)

            # test custom default (fnf fallback!)
            fp = os.path.join(root, artist + ".-." + title)
            search = unquote(s.lyric_filename)
            assertEqual(search, fp)

            # test user defined
            fp = os.path.join(root, artist + " - " + title + ".lyric")
            with io.open(fp, "w", encoding='utf-8') as f:
                f.write(u"")
            search = s.lyric_filename
            os.remove(fp)
            assertEqual(search, fp)

            # test order priority
            root2 = os.path.join(get_home_dir(), ".lyrics") # built-in default
            fp2 = os.path.join(root2, artist + " - " + title + ".lyric")
            p2 = os.path.dirname(fp2)
            mkdir(p2)
            with io.open(fp2, "w", encoding='utf-8') as f:
                f.write(u"")
            fp = os.path.join(root, artist + " - " + title + ".lyric")
            with io.open(fp, "w", encoding='utf-8') as f:
                f.write(u"")
            mkdir(p2)
            search = s.lyric_filename
            os.remove(fp2)
            os.rmdir(p2)
            os.remove(fp)
            assertEqual(search, fp)

            # test modified extension fallback search
            fp = os.path.join(root, artist + " - " + title + ".txt")
            with io.open(fp, "w", encoding='utf-8') as f:
                f.write(u"")
            search = s.lyric_filename
            os.remove(fp)
            assertEqual(search, fp)

            # reset to pickup default (no <attr>) templates
            config.remove_option("memory", "lyric_filenames")

            # test '<' and/or '>' in name
            # (not parsed (transparent to test))
            path_variants = \
                ['<oldskool>'] if (os.name == "nt") \
                               else ['\<artist\>', '\<artist>', '<artist\>']
            for path_variant in path_variants:
                s['artist'] = path_variant + " SpongeBob SquarePants"
                parts = [root, s['artist'] + " - " + s['title'] + ".lyric"]
                rpf = RootPathFile(root, os.path.sep.join(parts))
                if not rpf.is_valid:
                    rpf = RootPathFile(rpf.root, rpf.pathfile_escaped)
                self.assertTrue(rpf.is_valid,
                                "even escaped target file is not valid")
                with io.open(rpf.pathfile, "w", encoding='utf-8') as f:
                    f.write(u"")
                search = s.lyric_filename
                os.remove(rpf.pathfile)
                assertEqual(search, rpf.pathfile)

            # test '<' and '>' in name across path
            # (not parsed (transparent to test))
            s['artist'] = "a < b"
            s['title'] = "b > a"
            parts = [root, s['artist'], s['title'] + ".lyric"]
            rpf = RootPathFile(root, os.path.sep.join(parts))
            rootp = root
            rmdirs = []
            # ensure valid dir existence
            for p in rpf.end.split(os.path.sep)[:-1]:
                rootp = os.path.sep.join([root, p])
                if not RootPathFile(root, rootp).is_valid:
                    rootp = os.path.sep.join([root, escape_filename(p)])
                self.assertTrue(RootPathFile(root, rootp).is_valid,
                                "even escaped target dir part is not valid!")
                if not os.path.exists(rootp):
                    mkdir(rootp)
                    rmdirs.append(rootp)

            if not rpf.is_valid:
                rpf = RootPathFile(rpf.root, rpf.pathfile_escaped)

            with io.open(rpf.pathfile, "w", encoding='utf-8') as f:
                f.write(u"")
            # search for lyric file
            search = s.lyric_filename
            # clean up test lyric file / path
            os.remove(rpf.pathfile)
            for p in rmdirs:
                os.rmdir(p)
            # test whether the 'found' file is the test lyric file
            assertEqual(search, rpf.pathfile)

        # reset config - other tests expect different defaults!
        config.remove_option("memory", "lyric_rootpaths")
        config.remove_option("memory", "lyric_filenames")

    def test_lyrics_from_file(self):
        with temp_filename() as filename:
            af = AudioFile(artist='Motörhead', title='this: again')
            af.sanitize(filename)
            lyrics = "blah!\nblasé 😬\n"
            lyrics_dir = os.path.dirname(af.lyric_filename)
            mkdir(lyrics_dir)
            with io.open(af.lyric_filename, "w", encoding='utf-8') as lf:
                lf.write(text_type(lyrics))
            self.failUnlessEqual(af("~lyrics").splitlines(),
                                 lyrics.splitlines())
            os.remove(af.lyric_filename)
            os.rmdir(lyrics_dir)

    def test_mountpoint(self):
        song = AudioFile()
        song["~filename"] = fsnative(u"filename")
        song.sanitize()
        assert isinstance(song["~mountpoint"], fsnative)
        assert isinstance(song.comma("~mointpoint"), text_type)

    def test_sanitize(self):
        q = AudioFile(self.quux)
        b = AudioFile(bar_1_1)
        q.sanitize()
        b.pop('~filename')
        self.failUnlessRaises(ValueError, b.sanitize)
        n = AudioFile({"artist": u"foo\0bar", "title": u"baz\0",
                       "~filename": fsnative(u"whatever")})
        n.sanitize()
        self.failUnlessEqual(n["artist"], "foo\nbar")
        self.failUnlessEqual(n["title"], "baz")

    def test_performers(self):
        q = AudioFile([("performer:vocals", "A"), ("performer:guitar", "B"),
                       ("performer", "C")])
        self.failUnlessEqual(set(q.list("~performers")), {"A", "B", "C"})
        self.failUnlessEqual(set(q.list("~performers:roles")),
                             {"A (Vocals)", "B (Guitar)", "C (Performance)"})

    def test_performers_multi_value(self):
        q = AudioFile([
            ("performer:vocals", "X\nA\nY"),
            ("performer:guitar", "Y\nB\nA"),
            ("performer", "C\nF\nB\nA"),
        ])

        self.failUnlessEqual(
            set(q.list("~performer")), {"A", "B", "C", "F", "X", "Y"})

        self.failUnlessEqual(
            set(q.list("~performer:roles")), {
                    "A (Guitar, Performance, Vocals)",
                    "C (Performance)",
                    "B (Guitar, Performance)",
                    "X (Vocals)",
                    "Y (Guitar, Vocals)",
                    "F (Performance)",
                })

    def test_people(self):
        q = AudioFile([("performer:vocals", "A"), ("performer:guitar", "B"),
                       ("performer", "C"), ("arranger", "A"),
                       ("albumartist", "B"), ("artist", "C")])
        self.failUnlessEqual(q.list("~people"), ["C", "B", "A"])
        self.failUnlessEqual(q.list("~people:roles"),
            ["C (Performance)", "B (Guitar)", "A (Arrangement, Vocals)"])

    def test_people_mix(self):
        q = AudioFile([
            ("performer:arrangement", "A"),
            ("arranger", "A"),
            ("performer", "A"),
            ("performer:foo", "A"),
        ])
        self.failUnlessEqual(q.list("~people"), ["A"])
        self.failUnlessEqual(q.list("~people:roles"),
            ["A (Arrangement, Arrangement, Foo, Performance)"])

    def test_people_multi_value(self):
        q = AudioFile([
            ("arranger", "A\nX"),
            ("performer", "A\nY"),
            ("performer:foo", "A\nX"),
        ])

        self.failUnlessEqual(q.list("~people"), ["A", "Y", "X"])
        self.failUnlessEqual(q.list("~people:roles"),
            ["A (Arrangement, Foo, Performance)", "Y (Performance)",
             "X (Arrangement, Foo)"])

    def test_people_individuals(self):
        q = AudioFile({"artist": "A\nX", "albumartist": "Various Artists"})
        self.failUnlessEqual(q.list("~people:real"), ["A", "X"])

        lonely = AudioFile({"artist": "various artists", "title": "blah"})
        self.failUnlessEqual(lonely.list("~people:real"),
                             ["various artists"])

        lots = AudioFile({"artist": "Various Artists", "albumartist": "V.A."})
        self.failUnlessEqual(lots.list("~people:real"),
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
        self.failUnlessEqual(q.list("~peoplesort"),
                             ["B, The", "C, The", "A, The"])
        self.failUnlessEqual(q.list("~peoplesort:roles"),
            ["B, The (Guitar)", "C, The (Performance)", "A, The (Vocals)"])

    def test_to_dump(self):
        dump = bar_1_1.to_dump()
        num = len(set(bar_1_1.keys()) | NUMERIC_ZERO_DEFAULT)
        self.failUnlessEqual(dump.count(b"\n"), num + 2)
        for key, value in bar_1_1.items():
            self.failUnless(key.encode("utf-8") in dump)
            self.failUnless(value.encode("utf-8") in dump)
        for key in NUMERIC_ZERO_DEFAULT:
            self.failUnless(key.encode("utf-8") in dump)

        n = AudioFile()
        n.from_dump(dump)
        self.failUnless(
            set(dump.split(b"\n")) == set(n.to_dump().split(b"\n")))

    def test_to_dump_long(self):
        if not PY2:
            return
        b = AudioFile(bar_1_1)
        b["~#length"] = long(200000000000)
        dump = b.to_dump()
        num = len(set(bar_1_1.keys()) | NUMERIC_ZERO_DEFAULT)
        self.failUnlessEqual(dump.count("\n"), num + 2, msg=dump)

        n = AudioFile()
        n.from_dump(dump)
        self.failUnless(set(dump.split("\n")) == set(n.to_dump().split("\n")))

    def test_to_dump_unicode(self):
        b = AudioFile(bar_1_1)
        b[u"öäü"] = u"öäü"
        dump = b.to_dump()
        n = AudioFile()
        n.from_dump(dump)
        self.assertEqual(n[u"öäü"], u"öäü")

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

    def test_remove_unknown(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.remove("foo", "not in list")
        song.remove("nope")
        self.failUnlessEqual(song.list("foo"), ["bar"])

    def test_remove_all(self):
        song = AudioFile()
        song.add("foo", "bar")
        song.add("foo", "another")
        song.add("foo", "one more")
        song.remove("foo")
        self.assertFalse("foo" in song)

    def test_remove_empty(self):
        song = AudioFile()
        song.add("foo", u"")
        song.remove("foo", u"")
        self.assertFalse("foo" in song)

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
            ({}, ((), (), '')),
            ({'album': 'foo'}, (('foo',), (), '')),
            ({'labelid': 'foo'}, ((), (), 'foo')),
            ({'musicbrainz_albumid': 'foo'}, ((), (), 'foo')),
            ({'album': 'foo', 'labelid': 'bar'}, (('foo',), (), 'bar')),
            ({'album': 'foo', 'labelid': 'bar', 'musicbrainz_albumid': 'quux'},
                (('foo',), (), 'bar')),
            ({'albumartist': 'a'}, ((), ('a',), '')),
            ]
        for tags, expected in album_key_tests:
            afile = AudioFile(**tags)
            afile.sanitize(fsnative(u'/dir/fn'))
            self.failUnlessEqual(afile.album_key, expected)

    def test_eq_ne(self):
        self.failIf(AudioFile({"a": "b"}) == AudioFile({"a": "b"}))
        self.failUnless(AudioFile({"a": "b"}) != AudioFile({"a": "b"}))

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
        assert AF().sort_key == AF({"tracknumber": "1"}).sort_key
        assert AF().sort_key == AF({"tracknumber": "1/1"}).sort_key
        assert AF().sort_key < AF({"tracknumber": "2/2"}).sort_key

        assert AF().sort_key == AF({"discnumber": "1"}).sort_key
        assert AF().sort_key == AF({"discnumber": "1/1"}).sort_key
        assert AF().sort_key < AF({"discnumber": "2/2"}).sort_key

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
            f = AudioFile({"~filename": u"/\xf6\xe4.mp3", "title": "win"})
            self.failUnlessEqual(f("~uri"), "file:///%C3%B6%C3%A4.mp3")
        else:
            f = AudioFile({
                "~filename": bytes2fsn(b"/\x87\x12.mp3", None),
                "title": "linux",
            })
            self.failUnlessEqual(f("~uri"), "file:///%87%12.mp3")

    def test_reload(self):
        audio = MusicFile(get_data_path('silence-44-s.mp3'))
        audio["title"] = u"foo"
        audio.reload()
        self.assertNotEqual(audio.get("title"), u"foo")

    def test_reload_fail(self):
        audio = MusicFile(get_data_path('silence-44-s.mp3'))
        audio["title"] = u"foo"
        audio.sanitize(fsnative(u"/dev/null"))
        self.assertRaises(AudioFileError, audio.reload)
        self.assertEqual(audio["title"], u"foo")


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
        self.assertEqual(decode_value("~#foo", 0.25), u"0.25")
        self.assertEqual(decode_value("~#foo", 4), u"4")
        self.assertEqual(decode_value("~#foo", "bar"), u"bar")
        self.assertTrue(isinstance(decode_value("~#foo", "bar"), text_type))
        path = fsnative(u"/foobar")
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
        self.failUnlessAlmostEqual(scale, self.minus_6db)

        scale = self.no_rg_song.replay_gain(["track"], +10, +10)
        self.failUnlessEqual(scale, 1.0)

        scale = self.no_rg_song.replay_gain(["track"], -16.0, +10)
        self.failUnlessAlmostEqual(scale, self.minus_6db)

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
        """Tests fully-numeric (ie no "db") RG tags.  See Issue 865"""
        self.failUnless(self.song("replaygain_album_gain"), "-1.00 db")
        for key, exp in self.rg_data.items():
            # Hack the nasties off and produce the "real" expected value
            exp = float(exp.split(" ")[0])
            # Compare as floats. Seems fairer.
            album_rg = self.song("~#%s" % key)
            try:
                val = float(album_rg)
            except ValueError:
                self.fail("Invalid %s returned: %s" % (key, album_rg))
            self.failUnlessAlmostEqual(
                val, exp, places=5,
                msg="%s should be %s not %s" % (key, exp, val))
