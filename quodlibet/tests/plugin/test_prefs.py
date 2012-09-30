# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from tests import TestCase, add
from tests.plugin import PluginTestCase
from quodlibet import config

class TPrefs(PluginTestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_all(self):
        for id_, plugin in self.plugins.iteritems():
            if hasattr(plugin, "PLUGIN_INSTANCE"):
                plugin = plugin()
            if hasattr(plugin, "PluginPreferences"):
                plugin.PluginPreferences(gtk.Window())

add(TPrefs)
