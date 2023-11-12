# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import os

from quodlibet import config
from quodlibet.formats import AudioFileError
from quodlibet.library import SongLibrary, SongFileLibrary
from tests import get_data_path, run_gtk_loop
from tests.helper import get_temp_copy, capture_output
from tests.test_library_libraries import (TLibrary, FakeSong, FSrange, FakeSongFile,
                                          FSFrange)
from tests.test_util_collection import NUMERIC_SONGS


class TSongLibrary(TLibrary):
    Fake = FakeSong
    Frange = staticmethod(FSrange)
    Library = SongLibrary

    def test_rename_dirty(self):
        self.library.dirty = False
        song = self.Fake(10)
        self.library.add([song])
        self.assertTrue(self.library.dirty)
        self.library.dirty = False
        self.library.rename(song, 20)
        self.assertTrue(self.library.dirty)

    def test_rename(self):
        song = self.Fake(10)
        self.library.add([song])
        self.library.rename(song, 20)
        run_gtk_loop()
        self.assertTrue(song in self.changed)
        self.assertTrue(song in self.library)
        self.assertTrue(song.key in self.library)
        self.assertEqual(song.key, 20)

    def test_rename_changed(self):
        song = self.Fake(10)
        self.library.add([song])
        changed = set()
        self.library.rename(song, 20, changed=changed)
        self.assertEqual(len(changed), 1)
        self.assertTrue(song in changed)

    def test_tag_values(self):
        self.library.add(self.Frange(30))
        del self.added[:]
        self.assertEqual(
            sorted(self.library.tag_values(10)), list(range(10)))
        self.assertEqual(sorted(self.library.tag_values(0)), [])
        self.assertFalse(self.changed or self.added or self.removed)


class TSongFileLibrary(TSongLibrary):
    Fake = FakeSongFile
    Frange = staticmethod(FSFrange)
    Library = SongFileLibrary

    def test__load_exists_invalid(self):
        new = self.Fake(100)
        new._valid = False
        changed, removed = self.library._load_item(new)
        self.assertFalse(removed)
        self.assertTrue(changed)
        self.assertTrue(new._valid)
        self.assertTrue(new in self.library)

    def test__load_not_exists(self):
        new = self.Fake(100)
        new._valid = False
        new._exists = False
        changed, removed = self.library._load_item(new)
        self.assertFalse(removed)
        self.assertFalse(changed)
        self.assertFalse(new._valid)
        self.assertFalse(new in self.library)

    def test__load_error_during_reload(self):
        try:
            from quodlibet import util
            print_exc = util.print_exc
            util.print_exc = lambda *args, **kwargs: None
            new = self.Fake(100)

            def error():
                raise AudioFileError

            new.reload = error
            new._valid = False
            changed, removed = self.library._load_item(new)
            self.assertTrue(removed)
            self.assertFalse(changed)
            self.assertFalse(new._valid)
            self.assertFalse(new in self.library)
        finally:
            util.print_exc = print_exc

    def test__load_not_mounted(self):
        new = self.Fake(100)
        new._valid = False
        new._exists = False
        new._mounted = False
        changed, removed = self.library._load_item(new)
        self.assertFalse(removed)
        self.assertFalse(changed)
        self.assertFalse(new._valid)
        self.assertFalse(new in self.library)
        self.assertTrue(self.library.masked(new))

    def __get_file(self):
        return get_temp_copy(get_data_path("empty.flac"))

    def test_add_filename(self):
        config.init()
        try:
            filename = self.__get_file()
            ret = self.library.add_filename(filename)
            self.assertTrue(ret)
            self.assertEqual(len(self.library), 1)
            self.assertEqual(len(self.added), 1)
            ret = self.library.add_filename(filename)
            self.assertTrue(ret)
            self.assertEqual(len(self.added), 1)
            os.unlink(filename)

            filename = self.__get_file()
            ret = self.library.add_filename(filename, add=False)
            self.assertTrue(ret)
            self.assertFalse(ret in self.library)
            self.assertEqual(len(self.added), 1)
            self.library.add([ret])
            self.assertTrue(ret in self.library)
            self.assertEqual(len(self.added), 2)
            self.assertEqual(2, len(self.library))
            os.unlink(filename)

            with capture_output():
                ret = self.library.add_filename("")
            self.assertFalse(ret)
            self.assertEqual(len(self.added), 2)
            self.assertEqual(len(self.library), 2)

        finally:
            config.quit()

    def test_contains_filename(self):
        filename = self.__get_file()
        try:
            assert not self.library.contains_filename(filename)
            assert self.library.add_filename(filename, add=False)
            assert not self.library.contains_filename(filename)
            assert self.library.add_filename(filename)
            assert self.library.contains_filename(filename)
        finally:
            os.unlink(filename)

    def test_add_filename_normalize_path(self):
        if not os.name == "nt":
            return

        config.init()
        filename = self.__get_file()

        # create a equivalent path different from the original one
        if filename.upper() == filename:
            other = filename.lower()
        else:
            other = filename.upper()

        song = self.library.add_filename(filename)
        other_song = self.library.add_filename(other)
        self.assertTrue(song is other_song)
        os.unlink(filename)
        config.quit()

    def test_playlists_featuring(self):
        pl_lib = self.library.playlists
        pl = pl_lib.create("playlist1")
        pl.extend(NUMERIC_SONGS)
        playlists = pl_lib.playlists_featuring(NUMERIC_SONGS[0])
        assert set(playlists) == {pl}
        # Now add a second one, check that instance tracking works
        pl2 = pl_lib.create("playlist2")
        pl2.append(NUMERIC_SONGS[0])
        playlists = pl_lib.playlists_featuring(NUMERIC_SONGS[0])
        assert set(playlists) == {pl, pl2}, "didn't register playlist2"
        assert set(pl_lib.playlists_featuring(NUMERIC_SONGS[1])) == {pl}
