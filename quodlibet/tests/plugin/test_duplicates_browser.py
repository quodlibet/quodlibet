# -*- coding: utf-8 -*-
# Copyright 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from quodlibet import app
from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.plugins import PM
from quodlibet.util.songwrapper import SongWrapper
from tests import init_fake_app, destroy_fake_app
from tests.plugin import PluginTestCase


class TDuplicates(PluginTestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = cls.modules["Duplicates"]
        cls.kind = cls.plugins["Duplicates"].cls
        cls.song = AudioFile({'~filename': '/dev/null',
                              'artist': 'foo BAR',
                              'title': 'no!'})
        cls.song2 = AudioFile({'~filename': '/dev/null',
                               'artist': 'föo bár',
                               'title': 'no?...'})

    @classmethod
    def tearDownClass(cls):
        del cls.mod
        del cls.kind

    def setUp(self):
        init_fake_app()
        self._turn_all_options_on()
        app.library.songs = [self.song, self.song2, self.song]
        self.plugin = self.kind([self.song], None)

    def _turn_all_options_on(self):
        for name in ['REMOVE_WHITESPACE', 'REMOVE_DIACRITICS',
                     'REMOVE_PUNCTUATION', 'CASE_INSENSITIVE']:
            # Get the actual values, don't hard-code here (kinda)
            cfg_name = getattr(self.mod.Duplicates, "_CFG_%s" % name)
            config.set(PM.CONFIG_SECTION,
                       self.kind._get_config_option(cfg_name),
                       True)

    # TODO: proper logic tests...

    def tearDown(self):
        self.plugin.destroy()
        del self.plugin
        destroy_fake_app()

    def test_starts_up(self):
        sws = [SongWrapper(s) for s in app.library.songs]
        self.plugin.plugin_songs(sws)
