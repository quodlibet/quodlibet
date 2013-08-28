# Copyright 2013 Christoph Reiter, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk
from quodlibet.plugins.songsmenu import SongsMenuPlugin

from tests import add
from tests.plugin import PluginTestCase
from quodlibet import config
from quodlibet.qltk.songsmenu import SongsMenuPluginHandler
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian

SONGS = [
    AudioFile({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
    AudioFile({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
    ]
SONGS.sort()

for song in SONGS:
    song.sanitize()


class TPluginsSongsMenu(PluginTestCase):
    def setUp(self):
        config.init()
        self.h = SongsMenuPluginHandler(lambda msg: True)
        library = SongLibrary()
        library.librarian = SongLibrarian()
        self.lib = library
        self.parent = Gtk.Window()

    def tearDown(self):
        self.lib.destroy()
        self.parent.destroy()
        config.quit()

    def test_init(self):
        for id_, plugin in self.plugins.iteritems():
            if self.h.plugin_handle(plugin):
                self.h.plugin_enable(plugin, None)
                self.h.handle(id_, None, None, [])
                self.h.plugin_disable(plugin)

    def test_handle_single(self):
        self.skipTest("Pops up windows and needs user input.. so disabled."
                      "Still worth keeping whilst we don't have unit tests "
                      "for all plugins.")
        # Ignored...
        for id_, plugin in self.plugins.iteritems():
            if self.h.plugin_handle(plugin):
                self.h.plugin_enable(plugin, None)
                self.h.handle(id_, self.lib, self.parent, SONGS)
                self.h.plugin_disable(plugin)

    def test_handles_albums(self):
        for id_, plugin in self.plugins.iteritems():
            if isinstance(plugin, SongsMenuPlugin):
                ha = plugin.handles_albums
                self.failIf(hasattr(plugin, "plugin_single_album") and not ha)
                self.failIf(hasattr(plugin, "plugin_plugin_album") and not ha)
                self.failIf(hasattr(plugin, "plugin_albums") and not ha)

add(TPluginsSongsMenu)
