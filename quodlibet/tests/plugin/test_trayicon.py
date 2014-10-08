# Copyright 2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import sys

from gi.repository import Gtk, Gdk, GdkPixbuf
from quodlibet import config
from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app
from tests import skipIf


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
        self.plugin._popup_menu(self.plugin._icon, Gdk.BUTTON_SECONDARY,
                                Gtk.get_current_event_time())
        self.plugin.disabled()

    def test_get_paused_pixbuf(self):
        get_paused_pixbuf = self.modules["Tray Icon"].get_paused_pixbuf

        self.assertTrue(get_paused_pixbuf((1, 1), 0))
        self.assertRaises(ValueError, get_paused_pixbuf, (0, 0), 0)
        self.assertRaises(ValueError, get_paused_pixbuf, (1, 1), -1)

    def test_new_with_paused_emblem(self):
        new_with_paused_emblem = \
            self.modules["Tray Icon"].new_with_paused_emblem

        # too small source pixbuf
        for w, h in [(150, 1), (1, 150), (1, 1)]:
            pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, h)
            success, new = new_with_paused_emblem(pb)
            self.assertFalse(success)
            self.assertTrue(new)

        # those should work
        for w, h in [(20, 20), (10, 10), (5, 5), (150, 5), (5, 150)]:
            pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, h)
            success, new = new_with_paused_emblem(pb)
            self.assertTrue(success)
            self.assertTrue(new)
