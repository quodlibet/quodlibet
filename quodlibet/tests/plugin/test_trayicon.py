# Copyright 2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from gi.repository import Gtk, Gdk
from quodlibet import config
from tests import add
from tests.plugin import PluginTestCase


class TTrayIcon(PluginTestCase):
    """
    Basic tests for `TrayIcon`
    Currently just covers the standard code paths without any real testing.
    """

    @classmethod
    def setUpClass(cls):
        config.init()

    @classmethod
    def tearDownClass(cls):
        config.quit()

    def setUp(self):
        self.plugin = self.plugins["Tray Icon"].cls()

    def test_enable_disable(self):
        self.plugin.enabled()
        self.plugin.disabled()

    def test_popup_menu(self):
        self.plugin.enabled()
        self.plugin._popup_menu(self.plugin._icon, Gdk.BUTTON_SECONDARY,
                                Gtk.get_current_event_time())
        self.plugin.disabled()

add(TTrayIcon)
