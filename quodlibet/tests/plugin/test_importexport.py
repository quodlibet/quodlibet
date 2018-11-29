# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#           2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import random

from quodlibet import config, app
from quodlibet.formats import AudioFile
from tests import destroy_fake_app, init_fake_app
from . import PluginTestCase
from ..helper import temp_filename

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
    return AudioFile({
        '~#length': 234, '~filename': ("/tmp/%d" % random.randint(1, 100_000)),
        'artist': AN_ARTIST, 'album': 'An Example Album',
        'title': A_TITLE, 'tracknumber': 1,
        'date': '2010-12-31',
    })


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
        app.library.disconnect(self.sig)
        del self.plugin
        destroy_fake_app()
        config.quit()

    def test_updating(self):
        metadata = [{"artist": [ANOTHER_ARTIST],
                     "albumartist": [AN_ALBUM_ARTIST]}]
        names = [s("~filename") for s in self.songs]

        # Run just the rename, skipping the UI...
        self.plugin.update_files(self.songs, metadata, names, append=True)

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

        self.plugin.update_files(self.songs, metadata, names, append=False)

        song = app.library[names[0]]
        assert song.list("artist") == [ANOTHER_ARTIST]

        # See #3068
        assert self.changed == self.songs, "Library wasn't notified correctly"

    def on_song_changed(self, library, songs):
        self.changed.extend(songs)
