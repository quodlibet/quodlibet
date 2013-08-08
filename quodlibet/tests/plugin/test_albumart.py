# Copyright 2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from gi.repository import Gtk
from quodlibet.qltk.quodlibetwindow import QuodLibetWindow
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.cover import ALBUM_ART_PLUGIN_ID
from tests import add
from tests.plugin import PluginTestCase

from quodlibet import library, config, browsers, player
from quodlibet import app

A_SONG = AudioFile({'~filename': '/dev/null', 'album': 'Bars of Foo'})


class TAlbumArt(PluginTestCase):

    @classmethod
    def setUpClass(cls):
        app.library = library.init()
        config.init()
        browsers.init()
        backend = player.init("nullbe")
        app.player = backend.init(app.librarian)
        app.window = QuodLibetWindow(app.library, app.player)

    @classmethod
    def tearDownClass(cls):
        app.window.destroy()
        config.quit()

    def setUp(self):
        self.songs = [A_SONG]
        self.plugin = self.plugins[ALBUM_ART_PLUGIN_ID](self.songs, library,
                                                        app.window)

    def testPluginAlbum(self):
        songs = [A_SONG]
        self.plugin.plugin_album(songs)

add(TAlbumArt)
