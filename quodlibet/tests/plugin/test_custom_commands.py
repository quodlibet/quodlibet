# -*- coding: utf-8 -*-
# Copyright 2012, 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
from quodlibet.formats._audio import AudioFile

from quodlibet.qltk.data_editors import JSONBasedEditor
from quodlibet.util.collection import Playlist
from quodlibet.util.json_data import JSONObjectDict
from quodlibet import config

from tests.plugin import PluginTestCase


CustomCommands = Command = None


class TCustomCommands(PluginTestCase):
    """Test CustomCommands plugin and associated classes"""

    def setUp(self):
        module = self.modules["CustomCommands"]
        globals().update(vars(module))
        self.plugin = self.plugins["CustomCommands"].cls
        config.init()
        self.cmd_list = CustomCommands.DEFAULT_COMS
        self.commands = JSONObjectDict.from_list(self.cmd_list)

    def tearDown(self):
        config.quit()

    def test_JSONBasedEditor(self):
        ed = JSONBasedEditor(Command, self.commands, None, "title")
        ed.show_now()
        ed.destroy()

    def test_playlist_plugin(self):
        pl = Playlist("foo")
        pl.extend([AudioFile({"~filename": "/dev/null"})])
        self.called_pl = None
        self.called_songs = None

        def proxy(songs, playlist=None):
            self.called_pl = playlist
            self.called_songs = songs

        plugin = self.plugin()
        plugin._handle_songs = proxy
        # Test that as a Playlist plugin it delegates correctly
        plugin.plugin_playlist(pl)
        self.failUnless(self.called_songs)
        self.assertEqual(self.called_pl, pl)
        self.assertEqual(self.called_songs, pl.songs)
