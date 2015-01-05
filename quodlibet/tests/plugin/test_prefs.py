# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app
from quodlibet import config


class TPrefs(PluginTestCase):
    def setUp(self):
        config.init()
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()
        config.quit()

    def test_all(self):
        tested_any = False

        for id_, plugin in self.plugins.iteritems():
            plugin = plugin.cls
            if hasattr(plugin, "PLUGIN_INSTANCE"):
                plugin = plugin()
            if hasattr(plugin, "PluginPreferences"):
                tested_any = True
                plugin.PluginPreferences(Gtk.Window())

        self.assertTrue(tested_any)
