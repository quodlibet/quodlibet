# Copyright 2013, 2016, 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

from gi.repository import GdkPixbuf

from quodlibet import app

from quodlibet import config
from quodlibet.formats import AudioFile
from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app
from tests import skipIf, TestCase
from tests.helper import menu_item_labels


@skipIf(sys.platform == "darwin", "segfaults..")
class TTrayIcon(PluginTestCase):
    """
    Basic tests for `TrayIcon`
    Currently just covers the standard code paths without any real testing.
    """

    def setUp(self):
        config.init()
        init_fake_app()
        self.plugin = self.plugins["Tray Icon"].cls()

    def tearDown(self):
        destroy_fake_app()
        config.quit()
        del self.plugin

    def test_enable_disable(self):
        self.plugin.enabled()
        self.plugin.disabled()

    def test_popup_menu(self):
        self.plugin.enabled()
        try:
            self.plugin._tray.popup_menu()
        finally:
            self.plugin.disabled()

    def test_get_paused_pixbuf(self):
        get_paused_pixbuf = self.modules["Tray Icon"].systemtray.get_paused_pixbuf

        assert get_paused_pixbuf((1, 1), 0)
        self.assertRaises(ValueError, get_paused_pixbuf, (0, 0), 0)
        self.assertRaises(ValueError, get_paused_pixbuf, (1, 1), -1)

    def test_new_with_paused_emblem(self):
        new_with_paused_emblem = self.modules[
            "Tray Icon"
        ].systemtray.new_with_paused_emblem

        # too small source pixbuf
        for w, h in [(150, 1), (1, 150), (1, 1)]:
            pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, h)
            success, new = new_with_paused_emblem(pb)
            assert not success
            assert new

        # those should work
        for w, h in [(20, 20), (10, 10), (5, 5), (150, 5), (5, 150)]:
            pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, h)
            success, new = new_with_paused_emblem(pb)
            assert success
            assert new


@skipIf(sys.platform == "darwin", "segfaults..")
class TIndicatorMenu(TestCase):
    def setUp(self):
        config.init()
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()
        config.quit()

    def test_menu_has_expected_items(self):
        from quodlibet.ext.events.trayicon.menu import IndicatorMenu

        menu = IndicatorMenu(app)
        labels = menu_item_labels(menu.get_menu_model())
        assert "_Edit…" in labels
        assert "Play_lists" in labels
        assert "_Play" in labels
        assert "_Next" in labels
        assert "Pre_vious" in labels
        assert "_Quit" in labels
        assert "_Rating" in labels

    def test_playlist_menu_populates(self):
        from quodlibet.ext.events.trayicon.menu import IndicatorMenu

        menu = IndicatorMenu(app)
        song = AudioFile({"~filename": "/dev/null"})
        menu.set_song(song)
        assert menu._playlists.submenu.get_n_items()
