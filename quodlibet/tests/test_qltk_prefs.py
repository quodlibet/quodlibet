# -*- coding: utf-8 -*-
from tests import TestCase, init_fake_app, destroy_fake_app

from quodlibet.qltk.prefs import PreferencesWindow
from quodlibet.qltk.songlist import set_columns
from quodlibet import config


class TPreferencesWindow(TestCase):

    def setUp(self):
        config.init()
        init_fake_app()
        # Avoid warnings when running with empty config
        set_columns(["artist", "title"])
        self.win = PreferencesWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        destroy_fake_app()
        self.win.destroy()
        config.quit()
