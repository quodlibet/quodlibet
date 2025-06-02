# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import glob

from gi.repository import Gtk, GObject

from tests import TestCase, mkdtemp

from senf import fsnative

from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.qltk.renamefiles import (
    StripDiacriticals,
    StripNonASCII,
    Lowercase,
    SpacesToUnderscores,
    StripWindowsIncompat,
    RenameFiles,
    ReplaceColons,
)


class TFilter(TestCase):
    def setUp(self):
        self.c = self.Kind()

    def tearDown(self):
        self.c.destroy()


class TFilterMixin:
    def test_mix_empty(self):
        empty = fsnative("")
        v = self.c.filter(empty, "")
        self.assertEqual(v, "")
        assert isinstance(v, str)

    def test_mix_safe(self):
        empty = fsnative("")
        safe = "safe"
        self.assertEqual(self.c.filter(empty, safe), safe)


class TSpacesToUnderscores(TFilter, TFilterMixin):
    Kind = SpacesToUnderscores

    def test_conv(self):
        self.assertEqual(self.c.filter("", "foo bar "), "foo_bar_")


class TStripWindowsIncompat(TFilter, TFilterMixin):
    Kind = StripWindowsIncompat

    def test_conv(self):
        if os.name == "nt":
            self.assertEqual(self.c.filter("", 'foo\\:*?;"<>|/'), "foo\\_________")
        else:
            self.assertEqual(self.c.filter("", 'foo\\:*?;"<>|/'), "foo_________/")

    def test_type(self):
        empty = fsnative("")
        assert isinstance(self.c.filter(empty, empty), fsnative)

    def test_ends_with_dots_or_spaces(self):
        empty = fsnative("")
        v = self.c.filter(empty, fsnative("foo. . "))
        self.assertEqual(v, fsnative("foo. ._"))
        assert isinstance(v, fsnative)

        if os.name == "nt":
            self.assertEqual(self.c.filter(empty, "foo. \\bar ."), "foo._\\bar _")
        else:
            self.assertEqual(self.c.filter(empty, "foo. /bar ."), "foo._/bar _")


class TReplaceColons(TFilter, TFilterMixin):
    Kind = ReplaceColons

    def test_leaves_colons_without_space(self):
        assert self.unaffected("Nu:Tone & others - mix.flac")
        assert self.unaffected("Elastica - 2:1.mp3")

    def test_replaces_colons_as_delimiters(self):
        assert self.conv("ii: allegro") == "ii - allegro"

    def test_replaces_semicolons_as_delimiters(self):
        assert self.conv("Mozart; Requiem in D minor") == "Mozart - Requiem in D minor"

    def test_replaces_colons_with_lots_of_spaces(self):
        assert self.conv("Cello Suite No 1  :  Prelude") == self.conv(
            "Cello Suite No 1 - Prelude"
        )

    def test_replaces_colons_with_non_word(self):
        assert self.conv('No. 1 "Minute": Molto vivace') == self.conv(
            'No. 1 "Minute" - Molto vivace'
        )

    def test_type(self):
        empty = fsnative("")
        assert isinstance(self.c.filter(empty, empty), fsnative)

    def conv(self, s: str):
        return self.c.filter(fsnative(""), s)

    def unaffected(self, s: str) -> bool:
        return self.conv(s) == s


class TStripDiacriticals(TFilter, TFilterMixin):
    Kind = StripDiacriticals

    def test_conv(self):
        empty = fsnative("")
        test = "\u00c1 test"
        out = "A test"
        v = self.c.filter(empty, test)
        self.assertEqual(v, out)
        assert isinstance(v, str)


class TStripNonASCII(TFilter, TFilterMixin):
    Kind = StripNonASCII

    def test_conv(self):
        empty = fsnative("")
        in_ = "foo \u00c1 \u1234"
        out = "foo _ _"
        v = self.c.filter(empty, in_)
        self.assertEqual(v, out)
        assert isinstance(v, str)


class TLowercase(TFilter, TFilterMixin):
    Kind = Lowercase

    def test_conv(self):
        empty = fsnative("")

        v = self.c.filter(empty, fsnative("foobar baz"))
        self.assertEqual(v, fsnative("foobar baz"))
        assert isinstance(v, fsnative)

        v = self.c.filter(empty, fsnative("Foobar.BAZ"))
        self.assertEqual(v, fsnative("foobar.baz"))
        assert isinstance(v, fsnative)


class Renamer(Gtk.Box):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self, *args, **kwargs):
        super().__init__()

        from quodlibet.library import SongLibrary

        self.library = SongLibrary()
        box = Gtk.Box()
        self.renamer = RenameFiles(self.library, box)
        box.add(self.renamer)

        self.renamer.test_mode = True

    def add_songs(self, songs):
        self.library.add(songs)

    def rename(self, pattern, songs):
        self.renamer.combo.get_child().set_text(pattern)
        self.renamer._preview(songs)
        self.renamer._rename(self.library)


class Song(AudioFile):
    """A mock AudioFile belong to one of three albums,
    based on a single number"""

    def __init__(self, target, num):
        super().__init__()

        self["title"] = "title_%d" % (num + 1)
        self["artist"] = "artist"
        self["album"] = "album"
        self["labelid"] = self["album"]
        self["~filename"] = fsnative(os.path.join(target, self["title"] + ".mp3"))


class TMoveArt(TestCase):
    Kind = Renamer

    def setUp(self):
        self.renamer = self.Kind()

    def tearDown(self):
        self.renamer.destroy()

    def reset_environment(self):
        config.init()
        self.root_path = mkdtemp()
        self.filenames = ["cover.jpg", "info.jpg", "title.jpg", "title2.jpg"]

    def generate_songs(self, path, quantity):
        return [Song(path, num) for num in range(quantity)]

    def generate_files(self, path, filenames):
        pathfiles = []
        for f in filenames:
            pathfile = os.path.join(path, f)
            if not os.path.isdir(os.path.dirname(pathfile)):
                os.makedirs(os.path.dirname(pathfile))
            with open(pathfile, "w") as fh:
                fh.write(f)
            pathfiles.append(pathfile)

        return pathfiles

    def art_set(self, path):
        return self.generate_files(path, self.filenames)

    def song_set(self, path):
        songs = self.generate_songs(path, 1)
        files = self.generate_files(
            path, [os.path.basename(song["~filename"]) for song in songs]
        )
        return files, songs

    def source_target(self, root_path, album, artist):
        return (
            os.path.join(root_path, album, artist),
            os.path.join(root_path + "_2", album, artist),
        )

    def moveart_set(
        self,
        artist="artist",
        album="album",
        source=None,
        target=None,
        file_pattern="<title>",
    ):
        source2, target2 = self.source_target(self.root_path, artist, album)
        if not source:
            source = source2
        if not target:
            target = target2
        self.art_set(source)
        song_files, songs = self.song_set(source)
        self.renamer.add_songs(songs)
        pattern = os.path.join(target, file_pattern)
        self.renamer.rename(pattern, songs)
        return (source, target)

    def test_no_move(self):
        self.reset_environment()

        # move art not set, no art files should move
        count_expected = 0
        source, target = self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_move_defaults(self):
        self.reset_environment()
        config.set("rename", "move_art", True)

        # single match for default search_filenames
        # "cover.jpg,folder.jpg,.folder.jpg"
        count_expected = 1
        source, target = self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_move_all_wildcard(self):
        self.reset_environment()
        config.set("rename", "move_art", True)
        config.set("albumart", "search_filenames", "*.jpg")

        # wildcard added to search_filenames for catchall"
        count_expected = 4
        source, target = self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_move_escape_glob_characters(self):
        self.reset_environment()
        config.set("rename", "move_art", True)
        config.set("albumart", "search_filenames", "*.jpg")
        self.filenames = ["artist_[x].jpg"]

        # test whether we cope with non-escaped special glob characters"
        count_expected = 1
        source, target = self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_relative_pattern(self):
        self.reset_environment()
        config.set("rename", "move_art", True)
        config.set("albumart", "search_filenames", "*.jpg")

        # should be a no-op"
        count_expected = 4
        source, target = self.moveart_set(target="")
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_selective_pattern(self):
        self.reset_environment()
        config.set("rename", "move_art", True)
        config.set("albumart", "search_filenames", "<artist>.jpg")
        self.filenames = ["cover.jpg", "artist.jpg"]

        # should be a no-op
        count_expected = 1
        source, target = self.moveart_set(target="")
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_overwrite(self):
        self.reset_environment()
        config.set("rename", "move_art", True)
        config.set("albumart", "search_filenames", "*.jpg")
        self.filenames = ["art.jpg"]

        # move set
        source, target = self.moveart_set()
        # fail as target audio already exists
        self.assertRaises(Exception, self.moveart_set())

        # remove audio
        os.remove(os.path.join(target, "title_1.mp3"))

        # move exising target art to .orig suffix
        count_expected = 2
        self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*jpg*"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

        # remove audio
        os.remove(os.path.join(target, "title_1.mp3"))
        os.remove(os.path.join(target, "art.jpg.orig"))
        config.set("rename", "move_art_overwrite", True)

        # overwrite existing target arg
        count_expected = 1
        self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*jpg*"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)

    def test_multi_source(self):
        self.reset_environment()
        config.set("rename", "move_art", True)
        config.set("albumart", "search_filenames", "*.jpg")

        source, target = self.source_target(self.root_path, "artist", "album")
        source2, target2 = self.source_target(self.root_path, "artist", "album2")

        self.filenames = ["art.jpg"]
        self.art_set(source)
        self.filenames = ["art2.jpg"]
        self.art_set(source2)

        song_files, songs = self.song_set(source)
        song_files2, songs2 = self.song_set(source2)

        self.renamer.add_songs(songs + songs2)

        # avoid audio file clashes
        pattern = os.path.join(target, "[<album>] artist - <title>")
        self.renamer.rename(pattern, songs + songs2)

        # album art sets merged
        count_expected = 2
        self.moveart_set()
        target_files = glob.glob(os.path.join(target, "*.jpg"))
        count_target = len(target_files)
        self.assertEqual(count_target, count_expected)
