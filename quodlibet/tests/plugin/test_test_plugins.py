# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests.plugin import PluginTestCase


class TTestPlugins(PluginTestCase):
    def test_pickle(self):
        plugin = self.plugins["pickle_test"].cls
        instance = plugin()
        instance.enabled()
        instance.disabled()
