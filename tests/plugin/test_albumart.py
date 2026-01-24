# Copyright 2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import AudioFile
from quodlibet.qltk.cover import ALBUM_ART_PLUGIN_ID
from tests.plugin import PluginTestCase

from quodlibet import library, config
from quodlibet import app

A_SONG = AudioFile(
    {"~filename": "/dev/null", "artist": "Mr Man", "album": "Bars of Foo"}
)

# Keep IDEs happy
DownloadAlbumArt = AlbumArtWindow = CoverArea = None


# TODO: Some real tests.
class TAlbumArt(PluginTestCase):
    @classmethod
    def setUpClass(cls):
        app.library = library.init()
        config.init()

    @classmethod
    def tearDownClass(cls):
        config.quit()

    def setUp(self):
        globals().update(vars(self.modules[ALBUM_ART_PLUGIN_ID]))
        self.songs = [A_SONG]
        self.plugin = DownloadAlbumArt(self.songs, library)

    def testAlbumArtWindow(self):
        win = AlbumArtWindow(self.songs)
        # GTK4: destroy() removed, widgets cleaned up automatically

    def testCoverArea(self):
        win = CoverArea(None, self.songs[0])
        # GTK4: destroy() removed, widgets cleaned up automatically
