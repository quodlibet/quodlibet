# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from quodlibet import app, config, player
from quodlibet.formats import AudioFile
from quodlibet.library import SongFileLibrary, SongLibrarian
from quodlibet.qltk.notif import TaskController
from quodlibet.qltk.quodlibetwindow import QuodLibetWindow, PlaybackErrorDialog
from tests import TestCase, init_fake_app
from tests.helper import send_key_click, visible


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
        QuodLibetWindow.windows.clear()
        config.quit()

    def test_window(self):
        lib = SongFileLibrary()
        lib.librarian = SongLibrarian()
        pl = player.init_player("nullbe", lib.librarian)
        window = QuodLibetWindow(lib, pl, headless=True)
        assert window in window.windows
        window.destroy()

    def test_space_toggles_play_pause_only(self):
        app.player.song = AudioFile({"~filename": "/dev/null"})
        app.player.paused = False
        app.window.stop_after.set_active(False)

        with visible(app.window):
            assert send_key_click(app.window, "space")
            assert app.player.paused
            assert not app.window.stop_after.get_active()

            app.player.paused = False
            assert send_key_click(app.window, "<shift>space")
            assert app.player.paused
            assert not app.window.stop_after.get_active()

    def test_playback_error_dialog(self):
        error = player.PlayerError("\xf6\xe4\xfc", "\xf6\xe4\xfc")
        PlaybackErrorDialog(None, error)
