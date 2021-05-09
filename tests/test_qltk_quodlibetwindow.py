# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from quodlibet.library import SongFileLibrary, SongLibrarian
from quodlibet.qltk.notif import TaskController
from tests import TestCase, init_fake_app

from quodlibet.qltk.quodlibetwindow import QuodLibetWindow, PlaybackErrorDialog
from quodlibet import player
from quodlibet import config


class TQuodLibetWindow(TestCase):
    def setUp(self):
        init_fake_app()
        # Ugh
        TaskController.default_instance = TaskController()
        config.init()

    def tearDown(self):
        # Avoid leaking to other tests
        if SongFileLibrary.librarian:
            SongFileLibrary.librarian.destroy()
            SongFileLibrary.librarian = None
        config.quit()

    def test_window(self):
        lib = SongFileLibrary()
        lib.librarian = SongLibrarian()
        pl = player.init_player("nullbe", lib.librarian)
        window = QuodLibetWindow(lib, pl, headless=True)
        assert window.windows
        window.destroy()

    def test_playback_error_dialog(self):
        error = player.PlayerError(u'\xf6\xe4\xfc', u'\xf6\xe4\xfc')
        PlaybackErrorDialog(None, error)
