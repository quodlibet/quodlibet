# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.formats import AudioFile
from quodlibet.util.songwrapper import SongWrapper
from tests.plugin import PluginTestCase

AUDIO_FILE = SongWrapper(AudioFile({'~filename': "/tmp/foobar"}))


class TConsole(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["Python Console Sidebar"]

    def tearDown(self):
        del self.mod

    def test_sidebar_plugin(self):
        plugin = self.mod.PyConsoleSidebar()
        plugin.enabled()
        self.failUnless(isinstance(plugin.create_sidebar(), Gtk.Widget), True)
        plugin.plugin_on_songs_selected([AUDIO_FILE])
        self.failUnlessEqual(plugin.console.namespace.get('songs'),
                             [AUDIO_FILE])
        plugin.disabled()
