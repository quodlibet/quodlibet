#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import shutil
from os import urandom
from pathlib import Path

from gi.repository import Gio

from quodlibet.util.path import normalize_path
from senf import fsnative

from quodlibet import config
from quodlibet.ext.covers.artwork_url import ArtworkUrlCover
from quodlibet.formats import AudioFile
from quodlibet.plugins import Plugin
from quodlibet.util.cover.http import escape_query_value
from quodlibet.util.cover.manager import CoverManager
from tests import TestCase, mkdtemp

bar_2_1 = AudioFile(
    {
        "~filename": fsnative("does not/exist"),
        "title": "more songs",
        "discnumber": "2/2",
        "tracknumber": "1",
        "artist": "Foo\nI have two artists",
        "album": "Bar",
        "lyricist": "Foo",
        "composer": "Foo",
        "performer": "I have two artists",
    }
)


class TCoverManager(TestCase):
    def setUp(self):
        config.init()

        self.manager = CoverManager()
        self.dir: Path = Path(mkdtemp())
        self.song = self.an_album_song()

        # Safety check
        assert not list(self.dir.glob("*.jpg"))
        paths = [self.full_path("12345.jpg"), self.full_path("nothing.jpg")]
        for p in paths:
            p.write_bytes(urandom(1024))

    def an_album_song(self, fn="asong.ogg"):
        return AudioFile(
            {
                "~filename": str(self.full_path(fn)),
                "album": "AlbumName",
                "artist": "Some One",
            }
        )

    def tearDown(self):
        shutil.rmtree(self.dir)
        config.quit()

    def _find_cover(self, song: AudioFile):
        return self.manager.get_cover(song)

    def full_path(self, fn: str) -> Path:
        return (self.dir / fn).resolve()

    def test_dir_not_exist(self):
        assert not self._find_cover(bar_2_1)

    def test_nothing(self):
        assert not self._find_cover(self.song)

    def test_labelid(self):
        self.song["labelid"] = "12345"
        actual = Path(self._find_cover(self.song).name)
        assert actual == self.full_path("12345.jpg")
        del self.song["labelid"]

    def test_regular(self):
        for fn in [
            "cover.png",
            "folder.jpg",
            "AlbumName - front.png",
            "AlbumName_front_folder_cover.gif",
        ]:
            p = self.add_file(fn)
            cover = self._find_cover(self.song)
            assert cover, f"No cover found after adding {fn}"
            assert Path(cover.name).absolute() == p
        self.test_labelid()  # labelid must work with other files present

    def test_file_encoding(self):
        p = self.add_file(fsnative("öäü - AlbumName - cover.jpg"))
        assert isinstance(self.song("album"), str)
        h = self._find_cover(self.song)
        assert h, "Nothing found"
        assert Path(h.name) == p

    def test_glob(self):
        config.set("albumart", "force_filename", str(True))
        config.set("albumart", "filename", "foo.*")
        for fn in ["foo.jpg", "foo.png"]:
            p = self.add_file(fn)
            actual = Path(self._find_cover(self.song).name)
            assert actual == p
            (Path(self.dir) / fn).unlink()

    def test_invalid_glob(self):
        config.set("albumart", "force_filename", str(True))
        config.set("albumart", "filename", "[a-2].jpg")

        # Invalid glob range: should not match anything
        self.add_file("a.jpg")
        assert self._find_cover(self.song) is None

    def test_invalid_glob_path(self):
        config.set("albumart", "force_filename", str(True))
        config.set("albumart", "filename", "*.jpg")

        # Make a dir which contains an invalid glob
        path = self.full_path("[a-2]") / "cover.jpg"
        path.parent.mkdir()
        p = self.add_file(path)

        # Change the song's path to contain the invalid glob
        old_song_path = self.song["~filename"]
        new_song_path = path.parent / Path(old_song_path).name
        self.song["~filename"] = new_song_path

        # The glob in the dirname should be ignored, while the
        # glob in the filename/basename is honored
        assert Path(self._find_cover(self.song).name) == p

        self.song["~filename"] = old_song_path

    def test_multiple_entries(self):
        config.set("albumart", "force_filename", str(True))
        # the order of these is important, since bar should be
        # preferred to both 'foo' files
        # the spaces after the comma and last name are intentional
        config.set("albumart", "filename", "bar*,foo.png, foo.jpg ")

        for fn in ["foo.jpg", "foo.png", "bar.jpg"]:
            p = self.add_file(fn)
            actual = Path(self._find_cover(self.song).name)
            assert actual == p, f"{p.name} should have trumped, not {actual.name}"

    def test_back_excluded(self):
        self.add_file("AlbumName - back.jpg")
        assert not self._find_cover(self.song)

    def test_intelligent(self):
        song = self.song
        song["artist"] = "Q-Man"
        song["title"] = "First Q falls hardest"
        fns = [
            "AlbumName.jpg",
            "folder.jpeg",
            "q-MAN - albumname.jpg",
            "Q-man - AlbumName (FRONT).jpg",
        ]
        for fn in fns:
            p = self.add_file(fn)
            cover = self._find_cover(song)
            actual = normalize_path(cover.name)
            assert actual == normalize_path(str(p))

    def test_embedded_special_cover_words(self):
        """Tests that words incidentally containing embedded "special" words
        album keywords (e.g. cover, disc, back) don't trigger
        See Issue 818"""

        song = AudioFile(
            {
                "~filename": str(self.full_path("asong.ogg")),
                "album": "foobar",
                "title": "Ode to Baz",
                "artist": "Q-Man",
            }
        )
        data = [
            ("back.jpg", False),
            ("discovery.jpg", False),
            ("Pharell - frontin'.jpg", False),
            ("nickelback - Curb.jpg", False),
            ("foobar.jpg", True),
            ("folder.jpg", True),  # Though this order is debatable
            ("Q-Man - foobar.jpg", True),
            ("Q-man - foobar (cover).jpg", True),
        ]
        for fn, should_find in data:
            p = self.add_file(fn)
            cover = self._find_cover(song)
            if cover:
                actual = Path(cover.name).resolve()
                assert actual == p, f"{p.name!r} should trump {actual.name!r}"
            else:
                assert not should_find, f"Couldn't find {p} for {song('~filename')}"

    def add_file(self, fn: str | Path) -> Path:
        p = self.dir / fn
        p.write_bytes(urandom(1024))
        return p.resolve()

    def test_multiple_people(self):
        song = AudioFile(
            {
                "~filename": str(self.dir / "asong.ogg"),
                "album": "foobar",
                "title": "Ode to Baz",
                "performer": "The Performer",
                "artist": "The Composer\nThe Conductor",
                "composer": "The Composer",
            }
        )
        for fn in [
            "foobar.jpg",
            "The Performer - foobar.jpg",
            "The Composer - The Performer - foobar.jpg",
            "The Composer - The Conductor, The Performer - foobar.jpg",
        ]:
            p = self.add_file(fn)
            cover = self._find_cover(song)
            assert cover
            actual = Path(cover.name).resolve()
            cover.close()
            assert actual == p, f'"{p}" should trump "{actual}"'

    def test_get_thumbnail(self):
        assert self.manager.get_pixbuf(self.song, 10, 10) is None
        self.assertTrue(self.manager.get_pixbuf_many([self.song], 10, 10) is None)

    def test_get_many(self):
        songs = [
            AudioFile({"~filename": str(self.dir / "song.ogg"), "title": "Ode to Baz"}),
            self.an_album_song(),
        ]
        plugin = Plugin(ArtworkUrlCover)
        self.manager.plugin_handler.plugin_enable(plugin)
        self.add_file("cover.jpg")
        cover = self.manager.get_cover_many(songs)
        assert cover

    def test_search_missing_artist(self):
        titled_album_song = self.an_album_song("z.ogg")
        titled_album_song["artist"] = "foo"
        album_songs = [
            self.an_album_song("x.ogg"),
            titled_album_song,
            self.an_album_song(),
        ]
        self.manager.search_cover(Gio.Cancellable(), album_songs)


class THttp(TestCase):
    def test_escape(self):
        assert escape_query_value("foo bar") == "foo%20bar"
        assert escape_query_value("foo?") == "foo%3F"
        assert escape_query_value("foo&bar") == "foo%26bar"
        assert escape_query_value("¿fübàr?") == "¿fübàr%3F"
