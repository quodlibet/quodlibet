# Copyright 2017 Christoph Reiter
#           2018 Nick Boultbee, Fredrik Strupe
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config, app
from quodlibet.formats import AudioFile
from quodlibet.util import is_osx
from quodlibet.util.songwrapper import SongWrapper
from quodlibet.util.path import normalize_path
from tests import destroy_fake_app, init_fake_app, mkstemp, skipIf
from . import PluginTestCase
from ..helper import temp_filename
import os

A_TITLE = 'First Track'
AN_ARTIST = 'The Artist'
AN_ALBUM_ARTIST = "Album Artist"
ANOTHER_ARTIST = "New Artist"


class TExport(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["ExportMeta"]

    def tearDown(self):
        del self.mod

    def test_main(self):
        export_metadata = self.mod.export_metadata

        with temp_filename() as fn:
            export_metadata([a_dummy_song()], fn)

            with open(fn) as h:
                assert h.read()


def a_dummy_song():
    """Looks like the real thing"""
    fd, filename = mkstemp()
    os.close(fd)
    return AudioFile({
        '~#length': 234, '~filename': normalize_path(filename, True),
        'artist': AN_ARTIST, 'album': 'An Example Album',
        'title': A_TITLE, 'tracknumber': 1,
        'date': '2010-12-31',
    })


def wrap_songs(songs):
    return [SongWrapper(s) for s in songs]


class TImport(PluginTestCase):

    def setUp(self):
        config.init()
        init_fake_app()

        self.changed = []
        self.songs = [a_dummy_song()]
        self.Plugin = self.plugins["ImportMeta"].cls
        self.plugin = self.Plugin(self.songs)
        app.library.add(self.songs)
        self.sig = app.library.connect("changed", self.on_song_changed)

    def tearDown(self):
        for song in self.songs:
            os.remove(song["~filename"])
        app.library.disconnect(self.sig)
        del self.plugin
        destroy_fake_app()
        config.quit()

    def test_updating(self):
        metadata = [{"artist": [ANOTHER_ARTIST],
                     "albumartist": [AN_ALBUM_ARTIST]}]
        names = [s("~filename") for s in self.songs]

        # Run just the rename, skipping the UI...
        self.plugin.update_files(wrap_songs(self.songs),
                                 metadata, names, append=True)

        for name in names:
            assert name in app.library
            song = app.library[name]
            assert song('title') == A_TITLE
            assert set(song.list("artist")) == {ANOTHER_ARTIST, AN_ARTIST}
            assert song.list("albumartist") == [AN_ALBUM_ARTIST]

        # See #3068
        assert self.changed == self.songs, "Library wasn't notified correctly"

    def test_replacing(self):
        metadata = [{"artist": [ANOTHER_ARTIST],
                     "albumartist": [AN_ALBUM_ARTIST]}]
        names = [s("~filename") for s in self.songs]

        self.plugin.update_files(wrap_songs(self.songs),
                                 metadata, names, append=False)

        song = app.library[names[0]]
        assert song.list("artist") == [ANOTHER_ARTIST]

        # See #3068
        assert self.changed == self.songs, "Library wasn't notified correctly"

    @skipIf(is_osx(), "TODO: Fix for osx")
    def test_file_rename(self):
        metadata = [{"artist": [ANOTHER_ARTIST],
                     "albumartist": [AN_ALBUM_ARTIST]}]
        old_names = [s("~filename") for s in self.songs]
        new_names = [old_name + '_new' for old_name in old_names]

        # Sanity check
        for old, new in zip(old_names, new_names):
            assert old in app.library
            assert new not in app.library

        self.plugin.update_files(wrap_songs(self.songs), metadata, new_names,
                                 append=False, rename=True)

        for old, new in zip(old_names, new_names):
            assert new in app.library
            assert old not in app.library
            song = app.library[new]
            assert song("~filename") == new

    def on_song_changed(self, library, songs):
        self.changed.extend(songs)
