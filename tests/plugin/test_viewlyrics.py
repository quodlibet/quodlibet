# Copyright 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import app
from quodlibet.formats import AudioFile
from quodlibet.util.songwrapper import SongWrapper
from tests import init_fake_app, destroy_fake_app
from tests.plugin import PluginTestCase

AUDIO_FILE = AudioFile({"~filename": "/tmp/foobar",
                        "lyrics": "Never gonna give you up"})


class TViewlyrics(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["View Lyrics"]
        init_fake_app()
        self.plugin = self.mod.ViewLyrics()
        self.plugin.enabled()

    def tearDown(self):
        destroy_fake_app()
        del self.mod

    def test_no_song_started(self):
        self.plugin.plugin_on_song_started(None)

    def test_song_started(self):
        self.plugin.plugin_on_song_started(SongWrapper(AUDIO_FILE))

    def test_on_changed_stopped(self):
        self.plugin.plugin_on_changed([])
        tb = self.plugin.textbuffer
        actual = tb.get_text(tb.get_start_iter(), tb.get_end_iter(), True)
        # en_US is the default for tests so shouldn't need translation
        self.assertEqual(actual, "No active song")

    def test_on_changed(self):
        app.player.info = AUDIO_FILE
        self.plugin.plugin_on_changed([SongWrapper(AUDIO_FILE)])
        tb = self.plugin.textbuffer
        actual = tb.get_text(tb.get_start_iter(), tb.get_end_iter(), True)
        self.assertEqual(actual, AUDIO_FILE("lyrics"))

    def test_startup_playing_then_edit(self):
        app.player.info = AUDIO_FILE
        self.plugin.enabled()
        self.plugin._edit_button.emit("clicked")
