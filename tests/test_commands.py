# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from quodlibet.formats import AudioFile
from tests import TestCase, init_fake_app, destroy_fake_app
from .helper import capture_output

from gi.repository import Gtk

from quodlibet import config
from quodlibet import app

from quodlibet.commands import registry


class TCommands(TestCase):
    def setUp(self):
        config.init()
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()
        config.quit()

    def __send(self, command):
        command = fsnative(str(command))
        return registry.handle_line(app, command)

    def test_query(self):
        self.__send(u"query foo")
        self.assertEqual(self.__send("print-query-text"), u"foo\n")

    def test_print_playing_elapsed(self):
        app.player.info = AudioFile(
            {"album": "foo", "~filename": fsnative("/dev/null")})
        app.player.seek(123 * 1000)
        assert self.__send("print-playing <album~~elapsed>") == "foo - 2:03\n"

    def test_print_playing_elapsed_numeric(self):
        app.player.info = AudioFile(
            {"album": "foo", "~filename": fsnative("/dev/null")})
        app.player.seek(234.56 * 1000)
        assert self.__send("print-playing <~#elapsed>") == "234.56\n"

    def test_player(self):
        self.__send("previous")
        self.__send("force-previous")
        self.__send("next")
        self.__send("pause")
        self.__send("play-pause")
        self.__send("play")
        self.__send("print-playing <album~~elapsed>")
        self.__send("stop")
        self.__send("volume +1000")
        self.__send("volume 40")
        self.__send("volume -10")
        self.__send("volume +4.2")

        self.__send("seek -10")
        self.__send("seek +10")
        self.__send("seek 0")

    def test_misc(self):
        with capture_output():
            self.__send("play-file /dev/null")
        self.__send("dump-playlist")
        self.__send("dump-queue")
        self.__send("enqueue /dev/null")
        self.__send("enqueue-files /dev/null")
        self.__send("filter album=test")
        self.__send("query '/foobar/'")
        self.__send("focus")
        self.__send("hide-window")
        self.__send("dump-browsers")
        self.__send("open-browser SearchBar")
        from quodlibet.qltk.browser import LibraryBrowser
        for window in Gtk.Window.list_toplevels():
            if isinstance(window, LibraryBrowser):
                window.destroy()
        self.__send("properties")
        self.__send("queue 1")
        self.__send("quit")
        self.__send("random album")
        self.__send("refresh")
        self.__send("repeat 0")
        self.__send("show-window")
        self.__send("song-list 1")
        self.__send("stop-after 1")
        self.__send("status")
        self.__send("toggle-window")
        self.__send("unqueue /dev/null")

    def test_set_browser(self):
        self.__send("set-browser 1")

    def test_enqueue_files(self):
        songs = [AudioFile({"~filename": fn, "title": fn})
                 for fn in ["one", "two, please", "slash\\.mp3", "four"]]
        app.library.add(songs)

        self.assertFalse(app.window.playlist.q.get())
        self.__send("enqueue-files "
                    "one,two\\, please,slash\\\\.mp3,four")
        self.assertEquals(app.window.playlist.q.get(), songs)

    def test_rating(self):
        app.player.song = AudioFile(
            {"album": "foo", "~filename": fsnative("/dev/null")})
        self.__send("rating +")
        self.assertAlmostEqual(app.player.song['~#rating'], 0.75)
        self.__send("rating 0.4")
        self.assertAlmostEqual(app.player.song['~#rating'], 0.4)
        self.__send("rating +0.01")
        self.assertAlmostEqual(app.player.song['~#rating'], 0.41)
        self.__send("rating -10")
        self.assertEquals(app.player.song['~#rating'], 0)
