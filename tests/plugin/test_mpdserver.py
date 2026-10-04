# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#           2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import socket

from gi.repository import Gtk

from quodlibet.formats import AudioFile
from quodlibet import app
from quodlibet import config
from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app
from tests import skipIf, run_gtk_loop, get_data_path


@skipIf(os.name == "nt", "mpd server not supported under Windows")
class TMPDServer(PluginTestCase):
    def setUp(self):
        self.mod = self.modules["mpd_server"]

    def test_parse_command(self):
        parse = self.mod.main.parse_command

        self.assertEqual(parse(b"foo bar"), ("foo", ["bar"]))
        self.assertEqual(parse(b"foo\tbar"), ("foo", ["bar"]))
        self.assertEqual(parse(b"foo\t bar"), ("foo", ["bar"]))
        self.assertEqual(parse(b"foo\t bar quux"), ("foo", ["bar", "quux"]))
        self.assertEqual(parse(b'foo\t bar "q 2" x'), ("foo", ["bar", "q 2", "x"]))
        self.assertEqual(parse(b"foo 'bar  quux'"), ("foo", ["'bar", "quux'"]))
        self.assertEqual(
            parse(b"foo \xc3\xb6\xc3\xa4\xc3\xbc"), ("foo", ["\xf6\xe4\xfc"])
        )

    def test_format_tags(self):
        format_tags = self.mod.main.format_tags

        def getline(key, value):
            song = AudioFile({"~filename": "/dev/null"})
            song.sanitize()
            song[key] = value
            lines = format_tags(song).splitlines()
            if not lines:
                return ""
            if len(lines) == 1:
                return lines[0]
            # hackery since title defaults to the filename..
            for l in lines:
                if not l.startswith("Title"):
                    return l
            return None

        self.assertEqual(getline("artist", "foo"), "Artist: foo")
        self.assertEqual(getline("genre", "foo\nbar"), "Genre: foo, bar")
        self.assertEqual(getline("artistsort", "foo"), "ArtistSort: foo")
        self.assertEqual(getline("tracknumber", "2/3"), "Track: 2/3")
        self.assertEqual(getline("discnumber", "2/3"), "Disc: 2/3")
        self.assertEqual(getline("date", "2009-03-04"), "Date: 2009")


@skipIf(os.name == "nt", "mpd server not supported under Windows")
class TMPDCommands(PluginTestCase):
    def setUp(self):
        self.mod = self.modules["mpd_server"]
        config.init()
        init_fake_app()

        filename = get_data_path("silence-44-s.mp3")
        song = AudioFile({"~filename": fsnative(filename)})
        song.sanitize()
        app.library.add([song])

        MPDServerPlugin = self.mod.MPDServerPlugin
        MPDConnection = self.mod.main.MPDConnection
        MPDService = self.mod.main.MPDService

        class Server:
            def __init__(self) -> None:
                super().__init__()
                self.service = MPDService(app, MPDServerPlugin())

            def _remove_connection(self, conn):
                pass

        server = Server()
        s, c = socket.socketpair()
        self.s = s
        c.setblocking(False)
        s.settimeout(1)
        self.conn = MPDConnection(server, c)
        self.conn.handle_init(server)
        run_gtk_loop()
        self.s.recv(9999)

    def _cmd(self, data):
        self.s.send(data)
        while Gtk.events_pending():
            Gtk.main_iteration_do(True)
        if data.strip() != b"idle":
            return self.s.recv(99999)
        return None

    def tearDown(self):
        destroy_fake_app()
        config.quit()

    def test_currentsong_length(self):
        assert app.player is not None
        app.player.go_to(
            AudioFile(
                {
                    "~filename": "",
                    "~#length": 12.25,
                }
            )
        )

        response = self._cmd(b"currentsong\n")
        assert response is not None
        assert b"Time: 12\n" in response

    def test_tagtypes(self):
        response = self._cmd(b"tagtypes\n")
        assert response is not None
        assert b"Time\n" not in response

    def test_commands(self):
        skip = [
            "add",
            "addid",
            "close",
            "delete",
            "idle",
            "list",
            "listplaylists",
            "lsinfo",
            "noidle",
            "password",
            "playid",
            "plchanges",
            "plchangesposid",
            "search",
            "searchadd",
            "searchcount",
            "seek",
            "seekcur",
            "seekid",
        ]
        cmds = [c for c in self.conn.list_commands() if c not in skip]
        for cmd in cmds:
            self._cmd(cmd.encode("ascii") + b"\n")

    def test_seekcur(self):
        # Ensure we can handle both integer and float arguments.
        for cmd in ["seekcur 1", "seekcur 1.5"]:
            self._cmd(cmd.encode("ascii") + b"\n")

    def test_idle_close(self):
        for cmd in ["idle", "noidle", "close"]:
            self._cmd(cmd.encode("ascii") + b"\n")

    def test_queue_add_list_delete(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(f"add {filename}\n".encode())
        assert response is not None
        assert b"OK\n" in response

        response = self._cmd(b"playlist\n")
        assert response is not None
        assert f"file: {filename}".encode() in response

        response = self._cmd(b"delete 0\n")
        assert response is not None
        assert b"OK\n" in response

        response = self._cmd(b"playlist\n")
        assert response is not None
        assert f"file: {filename}".encode() not in response

    def test_queue_addid_and_plchanges(self):
        filename = get_data_path("silence-44-s.mp3")

        status = self._cmd(b"status\n")
        assert status is not None
        before = None
        for line in status.splitlines():
            if line.startswith(b"playlist:"):
                before = int(line.split(b":", 1)[1].strip())
                break
        assert before is not None

        response = self._cmd(f"addid {filename}\n".encode())
        assert response is not None
        assert b"Id:" in response

        response = self._cmd(f"plchanges {before}\n".encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_and_searchcount(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(f"search file {filename}\n".encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

        response = self._cmd(f"searchcount file {filename}\n".encode())
        assert response is not None
        assert b"songs: 1" in response

    def test_searchadd(self):
        filename = get_data_path("silence-44-s.mp3")

        response = self._cmd(f"searchadd file {filename}\n".encode())
        assert response is not None
        assert b"OK\n" in response

        response = self._cmd(b"playlist\n")
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_invalid_args(self):
        response = self._cmd(b"search artist\n")
        assert response is not None
        assert b"ACK" in response

    def test_search_any(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(f"search any {filename}\n".encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_expression(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(f'search "(file contains \\"{filename}\\")"\n'.encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_and_expression(self):
        filename = get_data_path("silence-44-s.mp3")
        mpd_query = '((file contains \\"silence-44-s\\") AND (file contains \\"mp3\\"))'
        response = self._cmd(f'search "{mpd_query}"\n'.encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_single_quotes(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(f"search \"(file contains '{filename}')\"\n".encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_escaped_quotes(self):
        song = AudioFile(
            {
                "~filename": fsnative("/dev/null"),
                "artist": "foo'bar\"",
            }
        )
        song.sanitize()
        app.library.add([song])

        response = self._cmd(b'search "(artist == \\"foo\\\'bar\\\\\\"\\")"\n')
        assert response is not None
        assert b"Artist: foo'bar\"" in response

    def test_search_filter_parentheses_in_value(self):
        song = AudioFile(
            {
                "~filename": fsnative("/dev/null"),
                "artist": "foo (bar) baz",
            }
        )
        song.sanitize()
        app.library.add([song])

        response = self._cmd(b'search "(artist == \\"foo (bar) baz\\")"\n')
        assert response is not None
        assert b"Artist: foo (bar) baz" in response

    def test_search_window(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(
            f'search "(file contains \\"{filename}\\")" window 0:1\n'.encode()
        )
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_starts_with(self):
        filename = get_data_path("silence-44-s.mp3")
        prefix = os.path.dirname(filename)
        response = self._cmd(f'search "(file starts_with \\"{prefix}\\")"\n'.encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_eq_ci_fallback(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(f'search "(file eq_ci \\"{filename}\\")"\n'.encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_regex_fallback(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(b'search "(file =~ "silence-44-s\\.mp3$")"\n')
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_not_contains(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(b'search "(file !contains \\"nope\\")"\n')
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_base(self):
        filename = get_data_path("silence-44-s.mp3")
        base = os.path.dirname(filename)
        response = self._cmd(f'search "(base \\"{base}\\")"\n'.encode())
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_added_since(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(b'search "(added-since \\"0\\")"\n')
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_modified_since(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(b'search "(modified-since \\"0\\")"\n')
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_sort_parsing(self):
        filename = get_data_path("silence-44-s.mp3")

        response = self._cmd(
            b'search "(file contains \\"silence-44-s\\")" sort artist\n'
        )
        assert response is not None
        assert f"file: {filename}".encode() in response

        response = self._cmd(
            b'search "(file contains \\"silence-44-s\\")" sort -artist\n'
        )
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_filter_sort_invalid(self):
        response = self._cmd(b'search "(file contains \\"silence-44-s\\")" sort -\n')
        assert response is not None
        assert b"ACK" in response

    def test_search_position(self):
        filename = get_data_path("silence-44-s.mp3")
        response = self._cmd(
            f'search "(file contains \\"{filename}\\")" position 0\n'.encode()
        )
        assert response is not None
        assert f"file: {filename}".encode() in response

    def test_search_window_term_in_filter(self):
        response = self._cmd(b'search "(album contains window)"\n')
        assert response is not None

    def test_search_requires_parentheses(self):
        response = self._cmd(b"search album contains foo\n")
        assert response is not None
        assert b"ACK" in response
