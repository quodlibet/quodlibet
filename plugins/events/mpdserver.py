# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os
import re
import shlex
import socket

from quodlibet import app
from quodlibet.plugins.events import EventPlugin

from gi.repository import Gtk, Gio, GLib


def pack_list(data):
    l = []
    for k, v in data:
        l.append("%s: %s\n" % (k, v))
    return "".join(l)


def handle_line(line):
    try:
        command, args = parse_command(line)
    except ParseError:
        return "ACK [42@0] {unknown} couldn't parse command %r\n" % line

    if command == "play":
        app.player.paused = False
        return "OK\n"

    if command == "pause":
        app.player.paused = True
        return "OK\n"

    if command == "next":
        app.player.next()
        return "OK\n"

    if command == "previous":
        app.player.previous()
        return "OK\n"

    if command == "setvol":
        if args:
            try:
                volume = int(args[0]) / 100.0
            except ValueError:
                pass
            else:
                app.player.volume = volume
        return "OK\n"

    if command == "idle":
        return None

    if command == "status":
        data = pack_list([
            ['repeat', 0],
            ['random', 0],
            ['single', 0],
            ['consume', 0],
            ['playlist', 0],
            ['playlistlength', 0],
            ['xfade', 0],
            ['state', "stop" if app.player.paused else "play"],
            ["song", 0],
            ["songid", 0],
            ["time", "0"],
            ["volume", int(app.player.volume * 100)],
        ])

        return data + "OK\n"
    elif command == "currentsong":
        data = pack_list([
            ["file", "/dev/null"],
            ['Artist', "artist"],
            ['Title', "title"],
            ['Album', "album"],
            ['Track', "track"],
            ['Genre', "genre"],
            ['Pos', "1"],
            ['Id', "42"],
        ])

        return data + "OK\n"
    elif command == "count":
        data = pack_list([
            ["songs", "0"],
            ['playtime', "0"],
        ])

        return data + "OK\n"
    else:
        return "OK\n"


class ParseError(Exception):
    pass


def parse_command(line):
    """Parses a MPD command (without trailing newline)

    Returns (command, [arguments]) or raises ParseError in case of an error.
    """

    assert isinstance(line, bytes)

    parts = re.split("[ \\t]+", line, maxsplit=1)
    if not parts:
        raise ParseError("empty command")
    command = parts[0]

    if len(parts) > 1:
        lex = shlex.shlex(parts[1], posix=True)
        lex.whitespace_split = True
        lex.commenters = ""
        lex.quotes = "\""
        lex.whitespace = " \t"
        args = list(lex)
    else:
        args = []

    try:
        command = command.decode("utf-8")
    except ValueError as e:
        raise ParseError(e)

    dec_args = []
    for arg in args:
        try:
            arg = arg.decode("utf-8")
        except ValueError as e:
            raise ParseError(e)
        dec_args.append(arg)

    return command, dec_args


class BaseConnection(object):

    connections = []
    """all open connections"""

    def __init__(self, sock):
        self._in_id = None
        self._out_id = None
        self.sock = sock
        self.connections.append(self)
        self._closed = False

    @classmethod
    def close_all(cls):
        for conn in cls.connections:
            conn.close()
        del cls.connections[:]

    def close(self):
        self._closed = True

        if self._in_id is not None:
            GLib.source_remove(self._in_id)
            self._in_id = None
        if self._out_id is not None:
            GLib.source_remove(self._out_id)
            self._out_id = None

        if self._closed:
            return
        self.handle_close()
        self.connections.remove(self)
        self.sock.close()

    def handle_init(self, server):
        raise NotImplementedError

    def handle_read(self, data):
        raise NotImplementedError

    def handle_write(self):
        raise NotImplementedError

    def can_write(self):
        raise NotImplementedError

    def handle_close(self):
        raise NotImplementedError


class MPDServer(object):
    """not much"""

    version = (0, 12)


class MPDConnection(BaseConnection):

    def handle_init(self, server):
        str_version = ".".join(map(str, server.version))
        self.buf = bytearray("OK MPD %s\n" % str_version)

    def handle_read(self, data):
        # FIXME: everything
        try:
            resp = handle_line(data.splitlines()[0])
        except ParseError:
            return
        if resp is not None:
            self.buf.extend(resp)

    def handle_write(self):
        data = self.buf[:]
        del self.buf[:]
        return data

    def can_write(self):
        return bool(self.buf)

    def handle_close(self):
        pass


class MPDServerPlugin(EventPlugin):
    PLUGIN_ID = "mpd_server"
    PLUGIN_NAME = _("MPD Server")
    PLUGIN_DESC = _("Provides a MPD server interface")
    PLUGIN_ICON = Gtk.STOCK_CONNECT

    PORT = 6600

    def enabled(self):
        self.server = MPDServer()
        service = Gio.SocketService.new()
        service.add_inet_port(self.PORT, None) # FIXME: can raise
        service.connect("incoming", self._incoming_connection_cb)
        self.service = service
        service.start()

    def disabled(self):
        if self.service.is_active():
            self.service.stop()
        del self.service

        BaseConnection.close_all()
        del self.server

    def _incoming_connection_cb(self, service, connection, *args):
        fd = connection.get_socket().get_fd()
        sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(0)

        mpd = MPDConnection(sock)
        mpd.handle_init(self.server)

        write_buffer = bytearray()

        def can_write_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                mpd.close()
                return False

            if flags & GLib.IOCondition.OUT:
                if mpd.can_write():
                    write_buffer.extend(mpd.handle_write())
                if not write_buffer:
                    mpd._out_id = None
                    return False

                result = sock.send(write_buffer)
                # FIXME: handle error
                del write_buffer[:result]

            return True

        def can_read_cb(sock, flags, *args):
            if flags & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                mpd.close()
                return False

            if flags & GLib.IOCondition.IN:
                data = sock.recv(4096)
                # FIXME: handle eagain etc.
                if not data:
                    mpd.close()
                    return False

                mpd.handle_read(data)

                if mpd._out_id is None and mpd.can_write():
                    mpd._out_id = GLib.io_add_watch(
                        sock, 0,
                        GLib.IOCondition.OUT | GLib.IOCondition.ERR |
                            GLib.IOCondition.HUP,
                        can_write_cb)

            return True

        # pass unneeded `connection` to keep the reference
        mpd._in_id = GLib.io_add_watch(
            sock, 0,
            GLib.IOCondition.IN | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
            can_read_cb, connection)

        mpd._out_id = GLib.io_add_watch(
            sock, 0,
            GLib.IOCondition.OUT | GLib.IOCondition.ERR | GLib.IOCondition.HUP,
            can_write_cb)
