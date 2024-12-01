# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
from collections import defaultdict
from os.path import exists
from pathlib import Path
from xml.etree.ElementTree import ElementTree

import pytest

from quodlibet import config, app
from quodlibet.formats import AudioFile as Fakesong
from quodlibet.formats._audio import NUMERIC_ZERO_DEFAULT, PEOPLE, AudioFile
from quodlibet.library.file import FileLibrary
from quodlibet.library.playlist import PlaylistLibrary
from quodlibet.util import format_rating
from quodlibet.util.collection import (Album, Playlist, avg, bayesian_average,
                                       FileBackedPlaylist, XSPFBackedPlaylist,
                                       XSPF_NS)
from senf import fsnative, uri2fsn
from tests import TestCase, mkdtemp

config.RATINGS = config.HardCodedRatingsPrefs()

NUMERIC_SONGS = [
    Fakesong({"~filename": fsnative("fake1-\xf0.mp3"),
              "~#length": 4, "~#added": 5, "~#lastplayed": 1,
              "~#bitrate": 200, "date": "100", "~#rating": 0.1,
              "originaldate": "2004-01-01", "~#filesize": 101}),
    Fakesong({"~filename": fsnative("fake2.mp3"),
              "~#length": 7, "~#added": 7, "~#lastplayed": 88,
              "~#bitrate": 220, "date": "99", "~#rating": 0.3,
              "originaldate": "2002-01-01", "~#filesize": 202}),
    Fakesong({"~filename": fsnative("fake3.mp3"),
              "~#length": 1, "~#added": 3, "~#lastplayed": 43,
              "~#bitrate": 60, "date": "33", "~#rating": 0.5,
              "tracknumber": "4/6", "discnumber": "1/2"})
]
AMAZING_SONG = Fakesong({"~#length": 123, "~#rating": 1.0})


class TAlbum(TestCase):
    def setUp(self):
        config.init()

    def test_people_sort(self):
        songs = [
            Fakesong({"albumartist": "aa", "artist": "b\na"}),
            Fakesong({"albumartist": "aa", "artist": "a\na"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        assert album.comma("~people") == "aa, a, b"

    def test_peoplesort_sort(self):
        songs = [
            Fakesong({"albumartistsort": "aa", "artist": "b\na"}),
            Fakesong({"albumartist": "aa", "artistsort": "a\na"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        assert album.comma("~peoplesort") == "aa, a, b"

    def test_tied_tags(self):
        songs = [
            Fakesong({"artist": "a", "title": "c"}),
            Fakesong({"artist": "a", "dummy": "d\ne"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        assert album.comma("~artist~dummy") == "a - d, e"

    def test_tied_num_tags(self):
        songs = [
            Fakesong({"~#length": 5, "title": "c", "~#rating": 0.4}),
            Fakesong({"~#length": 7, "dummy": "d\ne", "~#rating": 0.6}),
            Fakesong({"~#length": 0, "dummy2": 5, "~#rating": 0.5})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        assert album.comma("~foo~~s~~~") == ""
        assert album.comma("~#length~dummy") == "12 - d, e"
        assert album.comma("~#rating~dummy") == "0.50 - d, e"
        assert album.comma("~#length:sum~dummy") == "12 - d, e"
        assert album.comma("~#dummy2") == 5
        assert album.comma("~#dummy3") == ""

    def test_internal_tags(self):
        songs = [
            Fakesong({"~#length": 5, "discnumber": "1", "date": "2038"}),
            Fakesong({"~#length": 7, "dummy": "d\ne", "discnumber": "2"})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        self.assertNotEqual(album.comma("~long-length"), "")
        self.assertNotEqual(album.comma("~tracks"), "")
        self.assertNotEqual(album.comma("~discs"), "")
        assert album.comma("~foo") == ""

        assert album.comma("") == ""
        assert album.comma("~") == ""
        assert album.get("~#") == ""

    def test_numeric_ops(self):
        songs = NUMERIC_SONGS
        album = Album(songs[0])
        album.songs = set(songs)

        assert album.get("~#length") == 12
        assert album.get("~#length:sum") == 12
        assert album.get("~#length:max") == 7
        assert album.get("~#length:min") == 1
        assert album.get("~#length:avg") == 4
        assert album.get("~#length:foo") == 0

        assert album.get("~#added") == 7
        assert album.get("~#lastplayed") == 88
        assert album.get("~#bitrate") == 200
        assert album.get("~#year") == 33
        assert album.get("~#rating") == 0.3
        assert album.get("~#originalyear") == 2002

    def test_numeric_comma(self):
        songs = [Fakesong({
            "~#added": 1,
            "~#rating": 0.5,
            "~#bitrate": 42,
            "~#length": 1,
        })]

        album = Album(songs[0])
        album.songs = set(songs)

        self.assertEqual(album.comma("~#added"), 1)
        self.assertEqual(album.comma("~#rating"), 0.5)
        self.assertEqual(album.comma("~#bitrate"), 42)

    def test_numeric_funcs_text(self):
        songs = NUMERIC_SONGS
        album = Album(songs[0])
        album.songs = set(songs)

        self.assertEqual(album("~length:sum"), "0:12")
        self.assertEqual(album("~length:min"), "0:01")
        self.assertEqual(album("~long-length:min"), "1 second")
        self.assertEqual(album("~tracks:min"), "6 tracks")
        self.assertEqual(album("~discs:min"), "2 discs")
        self.assertEqual(album("~rating:min"), format_rating(0.1))
        self.assertEqual(album("~filesize:min"), "0 B")

    def test_single_rating(self):
        songs = [Fakesong({"~#rating": 0.75})]
        album = Album(songs[0])
        album.songs = set(songs)
        # One song should average to its own rating
        assert album.get("~#rating:avg") == songs[0]("~#rating")
        # BAV should now be default for rating
        assert album.get("~#rating:bav") == album.get("~#rating:avg")

    def test_multiple_ratings(self):
        r1, r2 = 1.0, 0.5
        songs = [Fakesong({"~#rating": r1}), Fakesong({"~#rating": r2})]
        album = Album(songs[0])
        album.songs = set(songs)
        # Standard averaging still available
        assert album("~#rating:avg") == avg([r1, r2])

        # C = 0.0 => emulate arithmetic mean
        config.set("settings", "bayesian_rating_factor", 0.0)
        assert album("~#rating:bav") == album("~#rating:avg")

    def test_bayesian_multiple_ratings(self):
        # separated from above to avoid caching
        c, r1, r2 = 5, 1.0, 0.5
        songs = [Fakesong({"~#rating": r1}), Fakesong({"~#rating": r2})]
        album = Album(songs[0])
        album.songs = set(songs)

        config.set("settings", "bayesian_rating_factor", float(c))
        assert config.getfloat("settings", "bayesian_rating_factor") == float(c)
        expected = avg(c * [config.RATINGS.default] + [r1, r2])
        assert album("~#rating:bav") == expected
        assert album("~#rating") == expected

    def test_bayesian_average(self):
        bav = bayesian_average
        l = [1, 2, 3, 4]
        a = avg(l)
        # c=0 => this becomes a mean regardless of m
        assert bav(l, 0, 0) == a
        assert bav(l, 0, 999) == a
        # c=1, m = a (i.e. just adding another mean score) => no effect
        assert bav(l, 1, a) == a
        # Harder ones
        assert bav(l, 5, 2) == 20.0 / 9
        expected = 40.0 / 14
        assert bav(l, 10, 3) == expected
        # Also check another iterable
        assert bav(tuple(l), 10, 3) == expected

    def test_defaults(self):
        song = Fakesong({})
        album = Album(song)

        assert album("foo", "x") == "x"

        album.songs.add(song)

        assert album("~#length", "x") == song("~#length", "x")
        assert album("~#bitrate", "x") == song("~#bitrate", "x")
        assert album("~#rating", "x") == song("~#rating", "x")
        assert album("~#playcount", "x") == song("~#playcount", "x")
        assert album("~#mtime", "x") == song("~#mtime", "x")
        assert album("~#year", "x") == song("~#year", "x")

        assert album("~#foo", "x") == song("~#foo", "x")
        assert album("foo", "x") == song("foo", "x")
        assert album("~foo", "x") == song("~foo", "x")

        assert album("~people", "x") == song("~people", "x")
        assert album("~peoplesort", "x") == song("~peoplesort", "x")
        assert album("~performer", "x") == song("~performer", "x")
        assert album("~performersort", "x") == song("~performersort", "x")

        assert album("~rating", "x") == song("~rating", "x")

        for p in PEOPLE:
            assert album(p, "x") == song(p, "x")

        for p in NUMERIC_ZERO_DEFAULT:
            assert album(p, "x") == song(p, "x")

    def test_methods(self):
        songs = [
            Fakesong({"b": "bb4\nbb1\nbb1",
                      "c": "cc1\ncc3\ncc3",
                      "#d": 0.1}),
            Fakesong({"b": "bb1\nbb1\nbb4",
                      "c": "cc3\ncc1\ncc3",
                      "#d": 0.2})
        ]

        album = Album(songs[0])
        album.songs = set(songs)

        assert album.list("c") == ["cc3", "cc1"]
        assert album.list("~c~b") == ["cc3", "cc1", "bb1", "bb4"]
        assert album.list("#d") == ["0.1", "0.2"]

        assert album.comma("c") == "cc3, cc1"
        assert album.comma("~c~b") == "cc3, cc1 - bb1, bb4"

    def tearDown(self):
        config.quit()


class PlaylistResource:
    def __init__(self, pl: Playlist):
        self.pl = pl

    def __enter__(self):
        return self.pl

    def __exit__(self, *exc_info):
        self.pl.delete()


class TPlaylist(TestCase):
    TWO_SONGS = [
        Fakesong({"~#length": 5, "discnumber": "1", "date": "2038"}),
        Fakesong({"~#length": 7, "dummy": "d\ne", "discnumber": "2"})
    ]

    class FakeLib:

        def __init__(self):
            self.reset()

        def emit(self, name, songs):
            self.emitted[name].extend(songs)

        def masked(self, songs):
            return False

        def reset(self):
            self.emitted = defaultdict(list)

        @property
        def changed(self):
            return self.emitted.get("changed", [])

        @property
        def playlists(self):
            return PlaylistLibrary(self)

    FAKE_LIB = FakeLib()

    def setUp(self):
        self.FAKE_LIB.reset()
        app.library = self.FAKE_LIB

    def pl(self, name, lib=None) -> Playlist:
        return Playlist(name, lib)

    def wrap(self, name, lib=FAKE_LIB):
        return PlaylistResource(self.pl(name, lib))

    def test_equality(self):
        pl = self.pl("playlist")
        pl2 = self.pl("playlist")
        pl3 = self.pl("playlist")
        self.assertEqual(pl, pl2)
        # Debatable
        self.assertEqual(pl, pl3)
        pl4 = self.pl("foobar")
        self.assertNotEqual(pl, pl4)
        pl.delete()
        pl2.delete()
        pl3.delete()
        pl4.delete()

    def test_index(self):
        with self.wrap("playlist") as pl:
            songs = self.TWO_SONGS
            pl.extend(songs)
            # Just a sanity check...
            self.assertEqual(songs.index(songs[1]), 1)
            # And now the happy paths...
            self.assertEqual(pl.index(songs[0]), 0)
            self.assertEqual(pl.index(songs[1]), 1)
            # ValueError is what we want here
            try:
                pl.index(Fakesong({}))
                self.fail()
            except ValueError:
                pass

    def test_name_tag(self):
        with self.wrap("a playlist") as pl:
            self.assertEqual(pl("~name"), "a playlist")
            self.assertEqual(pl.get("~name"), "a playlist")

    def test_internal_tags(self):
        with self.wrap("playlist") as pl:
            pl.extend(self.TWO_SONGS)

            self.assertNotEqual(pl.comma("~long-length"), "")
            self.assertNotEqual(pl.comma("~tracks"), "")
            self.assertNotEqual(pl.comma("~discs"), "")
            self.assertEqual(pl.comma("~foo"), "")

            self.assertEqual(pl.comma(""), "")
            self.assertEqual(pl.comma("~"), "")
            self.assertEqual(pl.get("~#"), "")

    def test_numeric_ops(self):
        songs = NUMERIC_SONGS
        with self.wrap("playlist") as pl:
            pl.extend(songs)

            self.assertEqual(pl.get("~#length"), 12)
            self.assertEqual(pl.get("~#length:sum"), 12)
            self.assertEqual(pl.get("~#length:max"), 7)
            self.assertEqual(pl.get("~#length:min"), 1)
            self.assertEqual(pl.get("~#length:avg"), 4)
            self.assertEqual(pl.get("~#length:foo"), 0)

            self.assertEqual(pl.get("~#rating:avg"), avg([0.1, 0.3, 0.5]))

            self.assertEqual(pl.get("~#filesize"), 303)

            self.assertEqual(pl.get("~#added"), 7)
            self.assertEqual(pl.get("~#lastplayed"), 88)
            self.assertEqual(pl.get("~#bitrate"), 200)
            self.assertEqual(pl.get("~#year"), 33)
            self.assertEqual(pl.get("~#rating"), 0.3)
            self.assertEqual(pl.get("~#originalyear"), 2002)

    def test_updating_aggregates_extend(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            old_length = pl.get("~#length")
            old_size = pl.get("~#filesize")

            # Double the playlist
            pl.extend(NUMERIC_SONGS)

            new_length = pl.get("~#length")
            new_size = pl.get("~#filesize")
            self.assertTrue(new_length > old_length,
                            msg="Ooops, %d <= %d" % (new_length, old_length))

            self.assertTrue(new_size > old_size,
                            msg="Ooops, %d <= %d" % (new_size, old_size))

    def test_updating_aggregates_append(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            old_rating = pl.get("~#rating")

            pl.append(AMAZING_SONG)

            new_rating = pl.get("~#filesize")
            assert new_rating > old_rating

    def test_updating_aggregates_clear(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            assert pl.get("~#length")

            pl.clear()
            assert not pl.get("~#length")

    def test_updating_aggregates_remove_songs(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            assert pl.get("~#length")

            pl.remove_songs(NUMERIC_SONGS)
            assert not pl.get("~#length")

    def test_listlike(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            self.assertEqual(NUMERIC_SONGS[0], pl[0])
            self.assertEqual(NUMERIC_SONGS[1:2], pl[1:2])
            assert NUMERIC_SONGS[1] in pl

    def test_extend_signals(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            self.assertEqual(self.FAKE_LIB.changed, NUMERIC_SONGS)

    def test_append_signals(self):
        with self.wrap("playlist") as pl:
            song = NUMERIC_SONGS[0]
            pl.append(song)
            self.assertEqual(self.FAKE_LIB.changed, [song])

    def test_clear_signals(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            pl.clear()
            self.assertEqual(self.FAKE_LIB.changed, NUMERIC_SONGS * 2)

    def test_make(self):
        with self.wrap("Does not exist") as pl:
            assert not len(pl)
            self.assertEqual(pl.name, "Does not exist")

    def test_rename_working(self):
        with self.wrap("Foobar") as pl:
            assert pl.name == "Foobar"
            pl.rename("Foo Quuxly")
            assert pl.name == "Foo Quuxly"
            # Rename should not fire signals
            assert not self.FAKE_LIB.changed

    def test_rename_nothing(self):
        with self.wrap("Foobar") as pl:
            self.assertRaises(ValueError, pl.rename, "")

    def test_no_op_rename(self):
        with self.wrap("playlist") as pl:
            pl.rename("playlist")
            self.assertEqual(pl.name, "playlist")

    def test_duplicates_single_item(self):
        with self.wrap("playlist") as pl:
            pl.append(self.TWO_SONGS[0])
            assert not pl.has_duplicates
            pl.append(self.TWO_SONGS[0])
            assert pl.has_duplicates

    def test_duplicates(self):
        with self.wrap("playlist") as pl:
            pl.extend(self.TWO_SONGS)
            pl.extend(self.TWO_SONGS)
            self.assertEqual(len(pl), 4)
            self.assertTrue(pl.has_duplicates,
                            ("Playlist has un-detected duplicates: %s "
                             % "\n".join([str(self) for s in pl._list])))

    def test_remove_leaving_duplicates(self):
        with self.wrap("playlist") as pl:
            pl.extend(self.TWO_SONGS)
            [first, second] = self.TWO_SONGS
            pl.extend(NUMERIC_SONGS + self.TWO_SONGS)
            self.assertEqual(len(self.FAKE_LIB.changed), 7)
            self.FAKE_LIB.reset()
            pl.remove_songs(self.TWO_SONGS, leave_dupes=True)
            assert first in pl
            assert second in pl
            assert not len(self.FAKE_LIB.changed)

    def test_remove_fully(self):
        with self.wrap("playlist") as pl:
            pl.extend(self.TWO_SONGS * 2)
            self.FAKE_LIB.reset()
            pl.remove_songs(self.TWO_SONGS, leave_dupes=False)
            assert not len(pl)
            self.assertEqual(self.FAKE_LIB.changed, self.TWO_SONGS)


class TFileBackedPlaylist(TPlaylist):
    Playlist = FileBackedPlaylist

    def setUp(self):
        super().setUp()
        self.temp = mkdtemp()
        self.temp2 = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp)
        shutil.rmtree(self.temp2)

    def pl(self, name, lib=None):
        fn = self.Playlist.filename_for(name)
        return self.Playlist(self.temp, fn, lib)

    def new_pl(self, name, lib=None):
        return self.Playlist.new(self.temp, name, lib)

    def test_from_songs(self):
        pl = self.Playlist.from_songs(self.temp, NUMERIC_SONGS)
        self.assertEqual(pl.songs, NUMERIC_SONGS)
        pl.delete()

    def test_read(self):
        lib = FileLibrary("foobar")
        lib.add(NUMERIC_SONGS)
        with self.wrap("playlist", lib) as pl:
            pl.extend(NUMERIC_SONGS)
            pl.write()
            self.assertEqual(len(pl), len(NUMERIC_SONGS))

    def test_write(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            pl.extend([fsnative("xf0xf0")])
            pl.write()

            with open(pl.path, "rb") as h:
                self.assertEqual(len(h.read().splitlines()),
                                 len(NUMERIC_SONGS) + 1)

    def test_difficult_names(self):
        lib = FileLibrary("foobar")
        tempdir = mkdtemp()
        self.add_songs_in_temp_dir(lib, tempdir, NUMERIC_SONGS)
        name = 'c:?"problem?" / foo* / 100% ə! COM'
        with self.wrap(name, lib) as pl:
            pl.extend(NUMERIC_SONGS)
            pl.write()
            assert pl.songs == NUMERIC_SONGS
            with self.wrap(name, lib) as pl2:
                assert pl2.songs == NUMERIC_SONGS

    def add_songs_in_temp_dir(self, lib, tempdir, songs):
        for l in songs:
            l["~filename"] = os.path.join(tempdir, l["~filename"])
            l.sanitize()
            lib.add([l])

    def test_symmetric(self):
        pcls = self.Playlist
        for name in ("bar & foo?", "100% cool.now 😀", "COM:", "a/b"):
            new_name = pcls.name_for(pcls.filename_for(name))
            assert new_name == name

    def test_make_dup(self):
        p1 = self.new_pl("Does not exist")
        p2 = self.new_pl("Does not exist")
        self.assertEqual(p1.name, "Does not exist")
        assert p2.name.startswith("Does not exist")
        self.assertNotEqual(p1.name, p2.name)
        p1.delete()
        p2.delete()

    def test_rename_removes(self):
        with self.wrap("foo") as pl:
            pl.rename("bar")
            assert exists(self.path_for("bar"))
            assert not exists(self.path_for("foo"))

    def path_for(self, name: str):
        return os.path.join(self.temp, self.Playlist.filename_for(name))

    def test_rename_fails_if_file_exists(self):
        with self.wrap("foo") as foo:
            with self.wrap("bar"):
                with pytest.raises(ValueError):
                    foo.rename("bar")

    def test_masked_handling(self):
        if os.name == "nt":
            # FIXME: masking isn't properly implemented on Windows
            return
        # playlists can contain songs and paths for masked handling..
        lib = FileLibrary("foobar")
        with self.wrap("playlist", lib) as pl:
            song = Fakesong({"date": "2038", "~filename": fsnative("/fake")})
            song.sanitize()
            lib.add([song])

            # mask and update
            lib.mask("/")
            pl.append(song)
            pl.remove_songs([song])
            assert "/fake" in pl

            pl.extend(self.TWO_SONGS)

            # check if collections can handle the mix
            self.assertEqual(pl("date"), "2038")

            # unmask and update
            lib.unmask("/")
            pl.add_songs(["/fake"], lib)
            assert song in pl

            lib.destroy()

    def test_delete_emits_no_signals(self):
        lib = self.FakeLib()
        with self.wrap("playlist", lib=lib) as pl:
            pl.extend(self.TWO_SONGS)
            # We don't care about changed signals on extend...
            lib.reset()
            pl.delete()
            assert not lib.emitted, "Deleting caused library signals"
        # Second time, just in case
        assert not lib.emitted, "Deleting again caused library signals"


class TXSPFBackedPlaylist(TFileBackedPlaylist):
    Playlist = XSPFBackedPlaylist

    def setUp(self):
        super().setUp()
        self.temp = mkdtemp()
        self.temp2 = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp)
        shutil.rmtree(self.temp2)

    def path_for(self, name: str):
        return os.path.join(self.temp, f"{name}.xspf")

    def test_write(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            some_path = fsnative(os.path.join(self.temp, "xf0xf0"))
            pl.extend([some_path])
            pl.write()

            assert exists(pl.path), "File doesn't exist"
            root = ElementTree().parse(pl.path)
            assert root.tag == "{http://xspf.org/ns/0/}playlist"
            tracks = root.findall(".//track", namespaces={"": XSPF_NS})
            assert len(tracks) == len(NUMERIC_SONGS) + 1, f"Hmm found {tracks}"
            # Should now write compliant local URLs
            last_location = tracks[-1].find("location", namespaces={"": XSPF_NS}).text
            assert uri2fsn(last_location) == some_path

    def test_writes_multiple_line_files(self):
        with self.wrap("playlist") as pl:
            pl.extend(NUMERIC_SONGS)
            pl.write()
            with open(pl.path) as f:
                lines = f.readlines()
                assert len(lines) >= 1 + 2 + len(pl), "Was expecting a semi-pretty-file"

    def test_load_legacy_format_to_xspf(self):
        playlist_fn = "old"
        songs_lib = FileLibrary()
        songs_lib.add(NUMERIC_SONGS)
        old_pl = FileBackedPlaylist(self.temp, playlist_fn)
        old_pl.extend(NUMERIC_SONGS)
        pl = XSPFBackedPlaylist.from_playlist(old_pl, songs_lib=songs_lib, pl_lib=None)
        expected_filenames = {s("~filename") for s in NUMERIC_SONGS}
        assert {s("~filename") for s in pl.songs} == expected_filenames

    def test_v1_load_non_compliant_xspf(self):
        """See #3983"""
        songs_lib = FileLibrary()
        test_filename = ("/music/Funk & Disco/"
                         "Average White Band - Pickin' Up The Pieces/"
                         "Average White Band - Your Love Is a Miracle.flac")
        songs_lib.add([AudioFile({"~filename": test_filename})])
        playlist_fn = "non-compliant.xspf"
        path = str(Path(__file__).parent / "data")
        pl = XSPFBackedPlaylist(path, playlist_fn, songs_lib=songs_lib, pl_lib=None)
        assert {s("~filename") for s in pl.songs}, set(test_filename)
