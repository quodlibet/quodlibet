# Copyright 2018 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from unittest import mock

from quodlibet.ext.songsmenu.cover_download import DownloadCoverArt, Config
from quodlibet.formats import AudioFile
from quodlibet.plugins import PluginManager
from quodlibet.qltk import get_children
from quodlibet.util.cover.manager import CoverData
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

    def test_found_cover_is_shown(self):
        win = self.mod.CoverArtWindow(
            self.songs, app.cover_manager, config=Config(), headless=True
        )
        result = CoverData("https://example.com/cover.jpg", "test", "1x1")
        with mock.patch.object(self.mod, "download"):
            win._covers_found(app.cover_manager, "test", [result])
        assert len(get_children(win.flow_box)) == 1
        win.destroy()
