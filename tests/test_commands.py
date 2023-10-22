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


class TCommandBase(TestCase):
    def setUp(self):
        config.init()
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()
        config.quit()

    def _send(self, command):
        command = fsnative(str(command))
        return registry.handle_line(app, command)


class TCommands(TCommandBase):
    def test_query(self):
        self._send(u"query foo")
        self.assertEqual(self._send("print-query-text"), u"foo\n")

    def test_print_playing_elapsed(self):
        app.player.info = AudioFile(
            {"album": "foo", "~filename": fsnative("/dev/null")})
        app.player.seek(123 * 1000)
        assert self._send("print-playing <album~~elapsed>") == "foo - 2:03\n"

    def test_print_playing_elapsed_numeric(self):
        app.player.info = AudioFile(
            {"album": "foo", "~filename": fsnative("/dev/null")})
        app.player.seek(234.56 * 1000)
        assert self._send("print-playing <~#elapsed>") == "234.56\n"

    def test_player(self):
        self._send("previous")
        self._send("force-previous")
        self._send("next")
        self._send("pause")
        self._send("play-pause")
        self._send("play")
        self._send("print-playing <album~~elapsed>")
        self._send("stop")
        self._send("volume +1000")
        self._send("volume 40")
        self._send("volume -10")
        self._send("volume +4.2")

        self._send("seek -10")
        self._send("seek +10")
        self._send("seek 0")

    def test_misc(self):
        with capture_output():
            self._send("play-file /dev/null")
        self._send("dump-playlist")
        self._send("dump-queue")
        self._send("enqueue /dev/null")
        self._send("enqueue-files /dev/null")
        self._send("filter album=test")
        self._send("query '/foobar/'")
        self._send("focus")
        self._send("hide-window")
        self._send("dump-browsers")
        self._send("open-browser SearchBar")
        from quodlibet.qltk.browser import LibraryBrowser
        for window in Gtk.Window.list_toplevels():
            if isinstance(window, LibraryBrowser):
                window.destroy()
        self._send("properties")
        self._send("queue 1")
        self._send("quit")
        self._send("random album")
        self._send("refresh")
        self._send("repeat 0")
        self._send("show-window")
        self._send("song-list 1")
        self._send("stop-after 1")
        self._send("status")
        self._send("toggle-window")
        self._send("unqueue /dev/null")

    def test_set_browser(self):
        self._send("set-browser 1")

    def test_enqueue_files(self):
        songs = [AudioFile({"~filename": fn, "title": fn})
                 for fn in ["one", "two, please", "slash\\.mp3", "four"]]
        app.library.add(songs)

        self.assertFalse(app.window.playlist.q.get())
        self._send("enqueue-files "
                    "one,two\\, please,slash\\\\.mp3,four")
        self.assertEquals(app.window.playlist.q.get(), songs)

    def test_rating(self):
        app.player.song = AudioFile(
            {"album": "foo", "~filename": fsnative("/dev/null")})
        self._send("rating +")
        self.assertAlmostEqual(app.player.song["~#rating"], 0.75)
        self._send("rating 0.4")
        self.assertAlmostEqual(app.player.song["~#rating"], 0.4)
        self._send("rating +0.01")
        self.assertAlmostEqual(app.player.song["~#rating"], 0.41)
        self._send("rating -10")
        self.assertEquals(app.player.song["~#rating"], 0)


class TCommandWithPattern(TCommandBase):
    def setUp(self):
        super().setUp()
        songs = [AudioFile({"~filename": fn, "title": fn.upper()})
                 for fn in ["one", "two, please", "slash\\.mp3", "4.0-four"]]
        app.library.add(songs)

        self.assertFalse(app.window.playlist.q.get())
        self._send("enqueue-files "
                    "one,two\\, please,slash\\\\.mp3,4.0-four")

    def test_old_syntax(self):
        assert self._send("print-query two ") == "two, please\n"

    def test_old_syntax_that_is_a_valid_json(self):
        assert self._send('print-query "one"') == "one\n"
        assert self._send("print-query 4.0") == "4.0-four\n"
        assert self._send("print-query true") == "\n"

    def test_new_syntax(self):
        assert self._send(
            'print-query {"query": "two", "pattern": null}'
        ) == "two, please\n"
        assert self._send(
            'print-query {"query": "two", "pattern": "asdf"}'
        ) == "asdf\n"
        assert self._send(
            'print-query {"query": "slash", "pattern": "<title>"}'
        ) == "SLASH\\.MP3\n"

    def test_query_is_valid_json(self):
        assert self._send(
            'print-query {"query": "\\"one\\"", "pattern": "<title>"}'
        ) == "ONE\n"
        assert self._send(
            'print-query {"query": "4.0", "pattern": "<title>"}'
        ) == "4.0-FOUR\n"

    def test_query_is_not_a_string(self):
        # Query is valid json, but not came from the CLI. (It's not a string.)
        assert self._send(
            'print-query {"query": 4.0, "pattern": "<title>"}'
        ) == "\n"
        assert self._send(
            'print-query {"query": true, "pattern": "<title>"}'
        ) == "\n"

    def test_invalid_args(self):
        assert self._send(
            'print-query {"query": "slash", "unknown": "<title>"}'
        ) == "\n"
