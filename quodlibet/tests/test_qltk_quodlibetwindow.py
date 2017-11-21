# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.quodlibetwindow import QuodLibetWindow, PlaybackErrorDialog
from quodlibet import library
from quodlibet import player
from quodlibet import config


class TQuodLibetWindow(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_window(self):
        lib = library.init()
        pl = player.init_player("nullbe", lib.librarian)
        window = QuodLibetWindow(lib, pl, headless=True)
        window.destroy()

    def test_playback_error_dialog(self):
        error = player.PlayerError(u'\xf6\xe4\xfc', u'\xf6\xe4\xfc')
        PlaybackErrorDialog(None, error)
