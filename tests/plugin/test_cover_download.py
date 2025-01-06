# Copyright 2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.ext.songsmenu.cover_download import DownloadCoverArt, Config
from quodlibet.formats import AudioFile
from quodlibet.plugins import PluginManager
from tests import init_fake_app, destroy_fake_app
from tests.plugin import PluginTestCase

from quodlibet import config
from quodlibet import app

A_SONG = AudioFile(
    {"~filename": "/dev/null", "artist": "Mr Man", "album": "Bars of Foo"}
)


class TAlbumArt(PluginTestCase):
    @classmethod
    def setUpClass(cls):
        config.init()
        init_fake_app()

    @classmethod
    def tearDownClass(cls):
        config.quit()
        destroy_fake_app()

    def setUp(self):
        self.mod = self.modules[DownloadCoverArt.PLUGIN_ID]
        self.songs = [A_SONG]
        config.add_section(PluginManager.CONFIG_SECTION)
        config.set(
            PluginManager.CONFIG_SECTION,
            f"{DownloadCoverArt.PLUGIN_ID}_preview_size",
            200,
        )

    def test_cover_art_window(self):
        win = self.mod.CoverArtWindow(
            self.songs,
            app.cover_manager,
            transient_for=app.window,
            config=Config(),
            headless=True,
        )
        win.destroy()
