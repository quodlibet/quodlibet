# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, Gtk

from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app


class TToggleMenuBar(PluginTestCase):
    def setUp(self):
        init_fake_app()
        self.plugin = self.plugins["ToggleMenuBar"].cls()
        self.plugin.enabled()
        self.menubar = self.plugin._menubar

    def tearDown(self):
        self.plugin.disabled()
        destroy_fake_app()

    def test_alt_toggles_the_hidden_menu_bar(self):
        assert isinstance(self.menubar, Gtk.PopoverMenuBar)
        assert not self.menubar.get_visible()
        self.plugin._key_controller.emit("key-released", Gdk.KEY_Alt_L, 0, 0)
        assert self.menubar.get_visible()
        self.plugin._key_controller.emit("key-released", Gdk.KEY_Alt_L, 0, 0)
        assert not self.menubar.get_visible()

    def test_disabling_shows_the_menu_bar(self):
        self.plugin.disabled()
        assert self.menubar.get_visible()
        self.plugin.enabled()
