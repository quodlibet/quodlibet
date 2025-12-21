# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
from pathlib import Path
from time import sleep

import pytest as pytest

from quodlibet import config, app, print_d
from quodlibet.library import SongFileLibrary
from quodlibet.library.file import FileLibrary
from quodlibet.util.library import get_exclude_dirs
from quodlibet.util.path import normalize_path
from senf import text2fsn
from tests import (
    mkdtemp,
    get_data_path,
    run_gtk_loop,
    _TEMP_DIR,
    init_fake_app,
    destroy_fake_app,
)
from tests.helper import temp_filename
from tests.test_library_libraries import TLibrary, FakeSongFile, FakeAudioFile


class TFileLibrary(TLibrary):
    Fake = FakeSongFile
    Library = FileLibrary

    def test_mask_invalid_mount_point(self):
        new = self.Fake(1)
        self.library.add([new])
        assert not self.library.masked_mount_points
        assert len(self.library)
        self.library.mask("/adsadsafaf")
        assert not self.library.masked_mount_points
        self.library.unmask("/adsadsafaf")
        assert not self.library.masked_mount_points
        assert len(self.library)

    def test_mask_basic(self):
        new = self.Fake(1)
        self.library.add([new])
        assert not self.library.masked_mount_points
        self.library.mask(new.mountpoint)
        self.assertEqual(self.library.masked_mount_points, [new.mountpoint])
        assert not len(self.library)
        self.assertEqual(self.library.get_masked(new.mountpoint), [new])
        assert self.library.masked(new)
        self.library.unmask(new.mountpoint)
        assert len(self.library)
        self.assertEqual(self.library.get_masked(new.mountpoint), [])

    def test_remove_masked(self):
        new = self.Fake(1)
        self.library.add([new])
        self.library.mask(new.mountpoint)
        assert self.library.masked_mount_points
        self.library.remove_masked(new.mountpoint)
        assert not self.library.masked_mount_points

    def test_content_masked(self):
        new = self.Fake(100)
        new._mounted = False
        assert not self.library.get_content()
        self.library._load_init([new])
        assert self.library.masked(new)
        assert self.library.get_content()

    def test_init_masked(self):
        new = self.Fake(100)
        new._mounted = False
        self.library._load_init([new])
        assert not self.library.items()
        assert self.library.masked(new)

    def test_load_init_nonmasked(self):
        new = self.Fake(200)
        new._mounted = True
        self.library._load_init([new])
        self.assertEqual(list(self.library.values()), [new])

    def test_reload(self):
        new = self.Fake(200)
        self.library.add([new])
        changed = set()
        removed = set()
        self.library.reload(new, changed=changed, removed=removed)
        assert new in changed
        assert not removed

    def test_move_root(self):
        # TODO: mountpoint tests too
        self.library.filename = "moving"
        root = Path(normalize_path(mkdtemp(), True))
        other_root = Path(normalize_path(mkdtemp(), True))
        new_root = Path(normalize_path(mkdtemp(), True))
        in_song = FakeAudioFile(str(root / "in file.mp3"))
        out_song = FakeAudioFile(str(other_root / "out file.mp3"))
        # Make sure they exist
        in_song.sanitize()
        out_song.sanitize()
        assert Path(in_song("~dirname")) == root, "test setup wrong"
        assert Path(out_song("~dirname")) == other_root, "test setup wrong"
        self.library.add([out_song, in_song])

        # Run it by draining the generator
        list(self.library.move_root(root, str(new_root)))
        msg = f"Dir wasn't updated in {root!r} -> {new_root!r} for {in_song.key}"
        assert Path(in_song("~dirname")) == new_root, msg
        assert Path(in_song("~filename")) == (new_root / "in file.mp3")
        assert Path(out_song("~dirname")) == other_root, f"{out_song} was wrongly moved"
        assert in_song._written, "Song wasn't written to disk"
        assert not out_song._written, "Excluded songs was written!"

    def test_move_root_gone_source_dir(self):
        # See #3967
        self.library.filename = "moving"
        gone_root = Path(normalize_path("/gone", True))
        new_root = Path(normalize_path(mkdtemp(), True))
        song = FakeAudioFile(str(gone_root / "in file.mp3"))
        assert Path(song("~dirname")) == gone_root, "test setup wrong"
        self.library.add([song])

        # Run it by draining the generator
        list(self.library.move_root(gone_root, str(new_root)))
        assert Path(song("~dirname")) == new_root
        assert song._written, "Song wasn't written to disk"

    def test_remove_roots(self):
        self.library.filename = "removing"
        root = Path(normalize_path(mkdtemp(), True))
        other_root = Path(normalize_path(mkdtemp(), True))
        out_song = FakeAudioFile(str(other_root / "out file.mp3"))
        in_song = FakeAudioFile(str(root / "in file.mp3"))
        in_song.sanitize()
        out_song.sanitize()
        self.library.add([in_song, out_song])
        assert in_song in self.library, "test seems broken"

        # Run it by draining the generator
        list(self.library.remove_roots([root]))

        assert in_song not in self.library
        assert out_song in self.library, "removed too many files"
        assert self.removed == [in_song], "didn't signal the song removal"
        assert not self.changed, "shouldn't have changed any tracks"


class TWatchedFileLibrary(TLibrary):
    Fake = FakeSongFile
    temp_path = Path(normalize_path(os.path.expanduser(_TEMP_DIR), True)).resolve()

    def setUp(self):
        init_fake_app()
        config.set("library", "watch", True)
        super().setUp()
        # Replace global one with this one
        librarian = app.library.librarian
        app.library.destroy()
        self.library.librarian = librarian
        app.library = self.library
        self.library.filename = "watching"
        librarian.register(self.library, "main")
        assert self.library.librarian.libraries

    def test_test_setup(self):
        assert self.temp_path.is_dir()
        assert self.temp_path.is_absolute()
        assert not self.temp_path.is_symlink(), "Symlinks cause trouble in these tests"
        assert not get_exclude_dirs()

    def tearDown(self):
        destroy_fake_app()

    def Library(self):
        lib = SongFileLibrary()
        dirs = [text2fsn(str(self.temp_path))]
        lib.start_watching(dirs)
        # Setup needs copools
        run_gtk_loop()
        return lib

    def test_monitors(self):
        monitors = self.library._monitors
        assert monitors, "Not monitoring any dirs"
        temp_path = Path(self.temp_path)
        assert temp_path in monitors, f"Not monitoring {temp_path} (but {monitors})"

    @pytest.mark.flaky(max_runs=4, min_passes=2)
    def test_watched_adding_removing(self):
        with temp_filename(dir=self.temp_path, suffix=".mp3", as_path=True) as path:
            shutil.copy(Path(get_data_path("silence-44-s.mp3")), path)
            sleep(0.5)
            run_gtk_loop()
            assert path.exists()
            assert str(path) in self.library, f"{path} should be in [{self.fns}] now"
        assert not path.exists(), "Failed to delete test file"
        sleep(0.5)
        # Deletion now
        run_gtk_loop()
        assert self.removed, "Nothing was automatically removed"
        assert self.added, "Nothing was automatically added"
        assert {Path(af("~filename")) for af in self.added} == {path}
        assert {Path(af("~filename")) for af in self.removed} == {path}
        assert str(path) not in self.library, f"{path} shouldn't be in the library now"

    @pytest.mark.flaky(max_runs=4, min_passes=2)
    def test_watched_adding(self):
        with temp_filename(dir=self.temp_path, suffix=".mp3", as_path=True) as path:
            shutil.copy(Path(get_data_path("silence-44-s.mp3")), path)
            assert self.temp_path in path.parents, "Copied test file incorrectly"
            watch_dirs = self.library._monitors.keys()
            assert path.parent in watch_dirs, "Not monitoring directory of new file"
            run_gtk_loop()
            dirs = [str(p) for p in watch_dirs]
            assert self.library, f"Nothing in library despite watches on {dirs}"
            assert (
                str(path) in self.library
            ), f"{path!s} should have been added to library [{self.fns}]"
            assert str(path) in {af("~filename") for af in self.added}

    def test_watched_moving_song(self):
        with temp_filename(dir=self.temp_path, suffix=".flac", as_path=True) as path:
            shutil.copy(Path(get_data_path("silence-44-s.flac")), path)
            sleep(0.2)
            assert path.exists()
            run_gtk_loop()
            assert str(path) in self.library, f"New path {path!s} didn't get added"
            assert len(self.added) == 1
            assert self.added[0]("~basename") == path.name
            self.added.clear()

            # Now move it...
            new_path = path.parent / f"moved-{path.name}"
            path.rename(new_path)
            sleep(0.2)
            assert not path.exists(), "test should have removed old file"
            assert new_path.exists(), "test should have renamed file"
            print_d(f"New test file at {new_path}")
            run_gtk_loop()
            p = normalize_path(str(new_path), True)
            assert p in self.library, f"New path {new_path} not in library [{self.fns}]"
            msg = "Inconsistent events: should be (added and removed) or nothing at all"
            assert not (bool(self.added) ^ bool(self.removed)), msg

    def test_watched_moving_dir(self):
        temp_dir = self.temp_path / "old"
        temp_dir.mkdir(exist_ok=False)
        sleep(0.2)
        run_gtk_loop()
        assert temp_dir in self.library._monitors
        with temp_filename(dir=temp_dir, suffix=".flac", as_path=True) as path:
            shutil.copy(Path(get_data_path("silence-44-s.flac")), path)
            sleep(0.2)
            assert path.exists()
            run_gtk_loop()
            assert str(path) in self.library, f"New path {path!s} didn't get added"
            assert len(self.added) == 1
            self.added.clear()
            assert self.library

            # Now move the directory...
            new_dir = path.parent.parent / "new"
            temp_dir.rename(new_dir)
            assert new_dir.is_dir(), "test should have moved to new dir"
            sleep(0.2)
            run_gtk_loop()

            new_path = new_dir / path.name
            assert new_path.is_file()
            msg = f"New path {new_path} not in library [{self.fns}]. Did move_root run?"
            assert str(new_path) in self.library, msg
            assert not self.removed, "A file was removed"

    @property
    def fns(self) -> str:
        return ", ".join(s("~filename") for s in self.library)
