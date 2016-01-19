# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os
import socket

from gi.repository import Gtk

from quodlibet.formats import AudioFile
from quodlibet import app
from quodlibet import config
from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app
from tests import skipIf


@skipIf(os.name == "nt", "mpd server not supported under Windows")
class TMPDServer(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["mpd_server"]

    def test_parse_command(self):
        parse = self.mod.main.parse_command

        self.assertEqual(parse("foo bar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\tbar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\t bar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\t bar quux"), ("foo", ["bar", "quux"]))
        self.assertEqual(
            parse("foo\t bar \"q 2\" x"), ("foo", ["bar", "q 2", "x"]))
        self.assertEqual(parse("foo 'bar  quux'"), ("foo", ["'bar", "quux'"]))
        self.assertEqual(
            parse("foo \xc3\xb6\xc3\xa4\xc3\xbc"), ("foo", [u"\xf6\xe4\xfc"]))

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

        MPDServerPlugin = self.mod.MPDServerPlugin
        MPDConnection = self.mod.main.MPDConnection
        MPDService = self.mod.main.MPDService

        class Server(object):
            service = MPDService(app, MPDServerPlugin())

            def _remove_connection(self, conn):
                pass

        server = Server()
        s, c = socket.socketpair()
        self.s = s
        c.setblocking(False)
        s.settimeout(1)
        self.conn = MPDConnection(server, c)
        self.conn.handle_init(server)
        while Gtk.events_pending():
            Gtk.main_iteration_do(True)
        self.s.recv(9999)

    def _cmd(self, data):
        self.s.send(data)
        while Gtk.events_pending():
            Gtk.main_iteration_do(True)
        if data.strip() != "idle":
            return self.s.recv(99999)

    def tearDown(self):
        destroy_fake_app()
        config.quit()

    def test_commands(self):
        skip = ["close", "idle", "noidle"]
        cmds = [c for c in self.conn.list_commands() if c not in skip]
        for cmd in cmds:
            self._cmd(cmd + b"\n")

    def test_idle_close(self):
        for cmd in ["idle", "noidle", "close"]:
            self._cmd(cmd + b"\n")
