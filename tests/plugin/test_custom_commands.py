# Copyright 2012-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import app
from quodlibet.formats._audio import AudioFile

from quodlibet.qltk.data_editors import JSONBasedEditor
from quodlibet.util.collection import Playlist
from quodlibet.util.json_data import JSONObjectDict
from quodlibet import config
from tests import init_fake_app, destroy_fake_app

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
        init_fake_app()

    def tearDown(self):
        config.quit()
        destroy_fake_app()

    def test_JSONBasedEditor(self):
        ed = JSONBasedEditor(Command, self.commands, None, "title")
        ed.show_now()
        ed.destroy()

    def test_playlist_plugin(self):
        pl = Playlist("foo", songs_lib=app.library)
        pl.extend([AudioFile({"~filename": "/dev/null"})])
        self.called_pl = None
        self.called_songs = None

        def proxy(songs, playlist=None):
            self.called_pl = playlist
            self.called_songs = songs

        plugin = self.plugin(playlists=[pl])
        plugin._handle_songs = proxy
        # Test that as a Playlist plugin it delegates correctly
        plugin.plugin_playlist(pl)
        self.assertTrue(self.called_songs)
        self.assertEqual(self.called_pl, pl)
        self.assertEqual(self.called_songs, pl.songs)

    def test_plugin_loads_json_once(self):
        plugin = self.plugin()
        self.assertTrue(plugin._commands)
        # Hack the commands without the plugin noticing
        fake = {"songs": Command(name="bar")}
        self.plugin._commands = fake
        # Try again, to make sure it hasn't reloaded
        plugin = self.plugin()
        self.assertEqual(plugin._commands, fake)
