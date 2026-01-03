# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import shlex
from collections.abc import Callable

from senf import bytes2fsn, fsn2bytes

from quodlibet import const
from quodlibet.util import print_d, print_w
from .tcpserver import BaseTCPServer, BaseTCPConnection


class AckError:
    NOT_LIST = 1
    ARG = 2
    PASSWORD = 3
    PERMISSION = 4
    UNKNOWN = 5
    NO_EXIST = 50
    PLAYLIST_MAX = 51
    SYSTEM = 52
    PLAYLIST_LOAD = 53
    UPDATE_ALREADY = 54
    PLAYER_SYNC = 55
    EXIST = 56


class Permissions:
    PERMISSION_NONE = 0
    PERMISSION_READ = 1
    PERMISSION_ADD = 2
    PERMISSION_CONTROL = 4
    PERMISSION_ADMIN = 8
    PERMISSION_ALL = (
        PERMISSION_NONE
        | PERMISSION_READ
        | PERMISSION_ADD
        | PERMISSION_CONTROL
        | PERMISSION_ADMIN
    )


TAG_MAPPING = [
    ("Artist", "artist"),
    ("ArtistSort", "artistsort"),
    ("Album", "album"),
    ("AlbumArtist", "albumartist"),
    ("AlbumArtistSort", "albumartistsort"),
    ("Title", "title"),
    ("Track", "tracknumber"),
    ("Genre", "genre"),
    ("Date", "~year"),
    ("Composer", "composer"),
    ("Performer", "performer"),
    ("Comment", "commend"),
    ("Disc", "discnumber"),
    ("Name", "~basename"),
    ("MUSICBRAINZ_ARTISTID", "musicbrainz_artistid"),
    ("MUSICBRAINZ_ALBUMID", "musicbrainz_albumid"),
    ("MUSICBRAINZ_ALBUMARTISTID", "musicbrainz_albumartistid"),
    ("MUSICBRAINZ_TRACKID", "musicbrainz_trackid"),
]


def format_tags(song):
    """Gives a tag list message for a song"""

    lines = []
    for mpd_key, ql_key in TAG_MAPPING:
        value = song.comma(ql_key) or None

        if value is not None:
            lines.append(f"{mpd_key}: {value}")

    return "\n".join(lines)


class ParseError(Exception):
    pass


def parse_command(line):
    """Parses a MPD command (without trailing newline)

    Returns (command, [arguments]) or raises ParseError in case of an error.
    """

    assert isinstance(line, bytes)

    parts = re.split(b"[ \\t]+", line, maxsplit=1)
    if not parts:
        raise ParseError("empty command")
    command = parts[0]

    if len(parts) > 1:
        lex = shlex.shlex(bytes2fsn(parts[1], "utf-8"), posix=True)
        lex.whitespace_split = True
        lex.commenters = ""
        lex.quotes = '"'
        lex.whitespace = " \t"
        args = [fsn2bytes(a, "utf-8") for a in lex]
    else:
        args = []

    try:
        command = command.decode("utf-8")
    except ValueError as e:
        raise ParseError(e) from e

    dec_args = []
    for arg in args:
        try:
            arg = arg.decode("utf-8")
        except ValueError as e:
            raise ParseError(e) from e
        dec_args.append(arg)

    return command, dec_args


class MPDService:
    """This is the actual shared MPD service which the clients talk to"""

    version = (0, 17, 0)

    def __init__(self, app, config):
        self._app = app
        self._connections = set()
        self._idle_subscriptions = {}
        self._idle_queue = {}
        self._pl_ver = 0

        self._config = config
        self._options = app.player_options

        if not self._config.config_get("password"):
            self.default_permission = Permissions.PERMISSION_ALL
        else:
            self.default_permission = Permissions.PERMISSION_NONE

        def options_changed(*args):
            self.emit_changed("options")

        self._options.connect("notify::shuffle", options_changed)
        self._options.connect("notify::repeat", options_changed)
        self._options.connect("notify::single", options_changed)

        self._player_sigs = []

        def volume_changed(*args):
            self.emit_changed("mixer")

        id_ = app.player.connect("notify::volume", volume_changed)
        self._player_sigs.append(id_)

        def player_changed(*args):
            self.emit_changed("player")

        id_ = app.player.connect("paused", player_changed)
        self._player_sigs.append(id_)
        id_ = app.player.connect("unpaused", player_changed)
        self._player_sigs.append(id_)
        id_ = app.player.connect("seek", player_changed)
        self._player_sigs.append(id_)

        def playlist_changed(*args):
            self._pl_ver += 1
            self.emit_changed("playlist")

        id_ = app.player.connect("song-started", playlist_changed)
        self._player_sigs.append(id_)

    def _get_id(self, info):
        # XXX: we need a unique 31 bit ID, but don't have one.
        # Given that the heap is continuous and each object is >16 bytes
        # this should work
        return (id(info) & 0xFFFFFFFF) >> 1

    def destroy(self):
        for id_ in self._player_sigs:
            self._app.player.disconnect(id_)
        del self._options
        del self._app

    def add_connection(self, connection):
        self._connections.add(connection)
        self._idle_queue[connection] = set()

    def remove_connection(self, connection):
        self._idle_subscriptions.pop(connection, None)
        self._idle_queue.pop(connection, None)
        self._connections.remove(connection)

    def register_idle(self, connection, subsystems):
        self._idle_subscriptions[connection] = set(subsystems)
        self.flush_idle()

    def flush_idle(self):
        flushed = []
        for conn, subs in self._idle_subscriptions.items():
            # figure out which subsystems to report for each connection
            queued = self._idle_queue[conn]
            if subs:
                to_send = subs & queued
            else:
                to_send = queued
            queued -= to_send

            # send out the response and remove the idle status for affected
            # connections
            for subsystem in to_send:
                conn.write_line(f"changed: {subsystem}")
            if to_send:
                flushed.append(conn)
                conn.ok()
                conn.start_write()

        for conn in flushed:
            self._idle_subscriptions.pop(conn, None)

    def unregister_idle(self, connection):
        self._idle_subscriptions.pop(connection, None)

    def emit_changed(self, subsystem):
        for _conn, subs in self._idle_queue.items():
            subs.add(subsystem)
        self.flush_idle()

    def play(self):
        self._app.player.playpause()

    def playid(self, songid):
        self.play()

    def pause(self, value=None):
        if value is None:
            self._app.player.paused = not self._app.player.paused
        else:
            self._app.player.paused = value

    def stop(self):
        self._app.player.stop()

    def next(self):
        self._app.player.next()

    def previous(self):
        self._app.player.previous()

    def seek(self, songpos, time_):
        """time_ in seconds"""

        self._app.player.seek(time_ * 1000)

    def seekid(self, songid, time_):
        """time_ in seconds"""

        self._app.player.seek(time_ * 1000)

    def seekcur(self, value, relative):
        if relative:
            pos = self._app.player.get_position()
            self._app.player.seek(pos + value * 1000)
        else:
            self._app.player.seek(value * 1000)

    def setvol(self, value):
        """value: 0..100"""

        self._app.player.volume = value / 100.0

    def repeat(self, value):
        self._options.repeat = value

    def random(self, value):
        self._options.shuffle = value

    def single(self, value):
        self._options.single = value

    def stats(self):
        has_song = int(bool(self._app.player.info))
        return [
            ("artists", has_song),
            ("albums", has_song),
            ("songs", has_song),
            ("uptime", 1),
            ("playtime", 1),
            ("db_playtime", 1),
            ("db_update", 1252868674),
        ]

    def status(self):
        app = self._app
        info = app.player.info

        if info:
            if app.player.paused:
                state = "pause"
            else:
                state = "play"
        else:
            state = "stop"

        status = [
            ("volume", int(app.player.volume * 100)),
            ("repeat", int(self._options.repeat)),
            ("random", int(self._options.shuffle)),
            ("single", int(self._options.single)),
            ("consume", 0),
            ("playlist", self._pl_ver),
            ("playlistlength", int(bool(app.player.info))),
            ("mixrampdb", 0.0),
            ("state", state),
        ]

        if info:
            status.append(
                (
                    "audio",
                    "%d:%d:%d"
                    % (
                        info("~#samplerate") or 0,
                        info("~#bitdepth") or 0,
                        info("~#channels") or 0,
                    ),
                )
            )
            total_time = int(info("~#length"))
            elapsed_time = int(app.player.get_position() / 1000)
            elapsed_exact = "%1.3f" % (app.player.get_position() / 1000.0)
            status.extend(
                [
                    ("song", 0),
                    ("songid", self._get_id(info)),
                ]
            )

            if state != "stop":
                status.extend(
                    [
                        ("time", "%d:%d" % (elapsed_time, total_time)),
                        ("elapsed", elapsed_exact),
                        ("bitrate", info("~#bitrate")),
                    ]
                )

        return status

    def currentsong(self):
        info = self._app.player.info
        if info is None:
            return None

        parts = []
        parts.append(f"file: {info('~filename')}")
        parts.append(format_tags(info))
        parts.append(f"Time: {int(info('~#length')):d}")
        parts.append(f"Pos: {0:d}")
        parts.append(f"Id: {self._get_id(info):d}")

        return "\n".join(parts)

    def playlistinfo(self, start=None, end=None):
        if start is not None and start > 1:
            return None

        return self.currentsong()

    def playlistid(self, songid=None):
        return self.currentsong()

    def plchanges(self, version):
        if version != self._pl_ver:
            return self.currentsong()
        return None

    def plchangesposid(self, version):
        info = self._app.player.info
        if version != self._pl_ver and info:
            parts = []
            parts.append(f"file: {info('~filename')}")
            parts.append(f"Pos: {0:d}")
            parts.append(f"Id: {self._get_id(info):d}")
            return "\n".join(parts)
        return None


class MPDServer(BaseTCPServer):
    def __init__(self, app, config, port):
        self._app = app
        self._config = config
        super().__init__(port, MPDConnection, const.DEBUG)

    def handle_init(self):
        print_d("Creating the MPD service")
        self.service = MPDService(self._app, self._config)

    def handle_idle(self):
        print_d("Destroying the MPD service")
        del self.service

    def log(self, msg):
        print_d(msg)


class MPDRequestError(Exception):
    def __init__(self, msg, code=AckError.UNKNOWN, index=None):
        self.msg = msg
        self.code = code
        self.index = index


class MPDConnection(BaseTCPConnection):
    #  ------------ connection interface  ------------

    def handle_init(self, server):
        service = server.service
        self.service = service
        service.add_connection(self)

        str_version = ".".join(map(str, service.version))
        self._buf = bytearray(f"OK MPD {str_version}\n".encode())
        self._read_buf = bytearray()

        # begin - command processing state
        self._use_command_list = False
        # everything below is only valid if _use_command_list is True
        self._command_list_ok = False
        self._command_list = []
        self._command = None
        # end - command processing state

        self.permission = self.service.default_permission

        self.start_write()
        self.start_read()

    def handle_read(self, data):
        self._feed_data(data)

        while 1:
            line = self._get_next_line()
            if line is None:
                break

            self.log(f"-> {line!r}")

            try:
                cmd, args = parse_command(line)
            except ParseError:
                # TODO: not sure what to do here re command lists
                continue

            try:
                self._handle_command(cmd, args)
            except MPDRequestError as e:
                self._error(e.msg, e.code, e.index)
                self._use_command_list = False
                del self._command_list[:]

    def handle_write(self):
        data = self._buf[:]
        del self._buf[:]
        return data

    def can_write(self):
        return bool(self._buf)

    def handle_close(self):
        self.log("connection closed")
        self.service.remove_connection(self)
        del self.service

    #  ------------ rest ------------

    def authenticate(self, password):
        if password == self.service._config.config_get("password"):
            self.permission = Permissions.PERMISSION_ALL
        else:
            self.permission = self.service.default_permission
            raise MPDRequestError("Password incorrect", AckError.PASSWORD)

    def log(self, msg):
        if const.DEBUG:
            print_d(f"[{self.name}] {msg}")

    def _feed_data(self, new_data):
        """Feed new data into the read buffer"""

        self._read_buf.extend(new_data)

    def _get_next_line(self):
        """Returns the next line from the read buffer or None"""

        try:
            index = self._read_buf.index(b"\n")
        except ValueError:
            return None

        line = bytes(self._read_buf[:index])
        del self._read_buf[: index + 1]
        return line

    def write_line(self, line):
        """Writes a line to the client"""

        assert isinstance(line, str)
        self.log(f"<- {line!r}")

        self._buf.extend(line.encode("utf-8", errors="replace") + b"\n")

    def ok(self):
        self.write_line("OK")

    def _error(self, msg, code, index):
        error = []
        error.append(f"ACK [{code:d}")
        if index is not None:
            error.append(f"@{index:d}")
        assert self._command is not None
        error.append(f"] {{{self._command}}}")
        if msg is not None:
            error.append(f" {msg}")
        self.write_line("".join(error))

    def _handle_command(self, command, args):
        self._command = command

        if command == "command_list_end":
            if not self._use_command_list:
                self._error("list_end without begin", 0, 0)
                return

            for i, (cmd, args) in enumerate(self._command_list):
                try:
                    self._exec_command(cmd, args)
                except MPDRequestError as e:
                    # reraise with index
                    raise MPDRequestError(e.msg, e.code, i) from e

            self.ok()
            self._use_command_list = False
            del self._command_list[:]
            return

        if command in ("command_list_begin", "command_list_ok_begin"):
            if self._use_command_list:
                raise MPDRequestError("begin without end")

            self._use_command_list = True
            self._command_list_ok = command == "command_list_ok_begin"
            assert not self._command_list
            return

        if self._use_command_list:
            self._command_list.append((command, args))
        else:
            self._exec_command(command, args)

    def _exec_command(self, command, args, no_ack=False):
        self._command = command

        if command not in self._commands:
            print_w(f"Unhandled command {command!r}, sending OK.")
            command = "ping"

            # Unhandled command, default to OK for now..
            if not self._use_command_list:
                self.ok()
            elif self._command_list_ok:
                self.write_line("list_OK")
            return

        cmd, do_ack, permission = self._commands[command]
        if permission != (self.permission & permission):
            raise MPDRequestError("Insufficient permission", AckError.PERMISSION)

        cmd(self, self.service, args)

        if self._use_command_list:
            if self._command_list_ok:
                self.write_line("list_OK")
        elif do_ack:
            self.ok()

    _commands: dict[str, tuple[Callable, bool, int]] = {}

    @classmethod
    def Command(cls, name, ack=True, permission=Permissions.PERMISSION_ADMIN):
        def wrap(func):
            assert name not in cls._commands, name
            cls._commands[name] = (func, ack, permission)
            return func

        return wrap

    @classmethod
    def list_commands(cls):
        """A list of supported commands"""

        return cls._commands.keys()


def _verify_length(args, length):
    if not len(args) >= length:
        raise MPDRequestError("Wrong arg count")


def _parse_int(arg):
    try:
        return int(arg)
    except ValueError as e:
        raise MPDRequestError("invalid arg") from e


def _parse_bool(arg):
    try:
        value = int(arg)
        if value not in (0, 1):
            raise ValueError
    except ValueError as e:
        raise MPDRequestError("invalid arg") from e
    else:
        return bool(value)


def _parse_range(arg):
    try:
        values = [int(v) for v in arg.split(":")]
    except ValueError as e:
        raise MPDRequestError("arg in range not a number") from e

    if len(values) == 1:
        return (values[0], values[0] + 1)
    if len(values) == 2:
        return values
    raise MPDRequestError("invalid range")


@MPDConnection.Command("idle", ack=False)
def _cmd_idle(conn, service, args):
    service.register_idle(conn, args)


@MPDConnection.Command("ping", permission=Permissions.PERMISSION_NONE)
def _cmd_ping(conn, service, args):
    return


@MPDConnection.Command("password", permission=Permissions.PERMISSION_NONE)
def _cmd_password(conn, service, args):
    _verify_length(args, 1)
    conn.authenticate(args[0])


@MPDConnection.Command("noidle")
def _cmd_noidle(conn, service, args):
    service.unregister_idle(conn)


@MPDConnection.Command("close", ack=False, permission=Permissions.PERMISSION_NONE)
def _cmd_close(conn, service, args):
    conn.close()


@MPDConnection.Command("play")
def _cmd_play(conn, service, args):
    service.play()


@MPDConnection.Command("listplaylists")
def _cmd_listplaylists(conn, service, args):
    pass


@MPDConnection.Command("list")
def _cmd_list(conn, service, args):
    pass


@MPDConnection.Command("playid")
def _cmd_playid(conn, service, args):
    _verify_length(args, 1)
    songid = _parse_int(args[0])
    service.playid(songid)


@MPDConnection.Command("pause")
def _cmd_pause(conn, service, args):
    value = None
    if args:
        _verify_length(args, 1)
        value = _parse_bool(args[0])
    service.pause(value)


@MPDConnection.Command("stop")
def _cmd_stop(conn, service, args):
    service.stop()


@MPDConnection.Command("next")
def _cmd_next(conn, service, args):
    service.next()


@MPDConnection.Command("previous")
def _cmd_previous(conn, service, args):
    service.previous()


@MPDConnection.Command("repeat")
def _cmd_repeat(conn, service, args):
    _verify_length(args, 1)
    value = _parse_bool(args[0])
    service.repeat(value)


@MPDConnection.Command("random")
def _cmd_random(conn, service, args):
    _verify_length(args, 1)
    value = _parse_bool(args[0])
    service.random(value)


@MPDConnection.Command("single")
def _cmd_single(conn, service, args):
    _verify_length(args, 1)
    value = _parse_bool(args[0])
    service.single(value)


@MPDConnection.Command("setvol")
def _cmd_setvol(conn, service, args):
    _verify_length(args, 1)
    value = _parse_int(args[0])
    service.setvol(value)


@MPDConnection.Command("status")
def _cmd_status(conn, service, args):
    status = service.status()
    for k, v in status:
        conn.write_line(f"{k}: {v}")


@MPDConnection.Command("stats")
def _cmd_stats(conn, service, args):
    status = service.stats()
    for k, v in status:
        conn.write_line(f"{k}: {v}")


@MPDConnection.Command("currentsong")
def _cmd_currentsong(conn, service, args):
    stats = service.currentsong()
    if stats is not None:
        conn.write_line(stats)


@MPDConnection.Command("count")
def _cmd_count(conn, service, args):
    conn.write_line("songs: 0")
    conn.write_line("playtime: 0")


@MPDConnection.Command("plchanges")
def _cmd_plchanges(conn, service, args):
    _verify_length(args, 1)
    version = _parse_int(args[0])
    changes = service.plchanges(version)
    if changes is not None:
        conn.write_line(changes)


@MPDConnection.Command("plchangesposid")
def _cmd_plchangesposid(conn, service, args):
    _verify_length(args, 1)
    version = _parse_int(args[0])
    changes = service.plchangesposid(version)
    if changes is not None:
        conn.write_line(changes)


@MPDConnection.Command("listallinfo")
def _cmd_listallinfo(*args):
    _cmd_currentsong(*args)


@MPDConnection.Command("seek")
def _cmd_seek(conn, service, args):
    _verify_length(args, 2)
    songpos = _parse_int(args[0])
    time_ = _parse_int(args[1])
    service.seek(songpos, time_)


@MPDConnection.Command("seekid")
def _cmd_seekid(conn, service, args):
    _verify_length(args, 2)
    songid = _parse_int(args[0])
    time_ = _parse_int(args[1])
    service.seekid(songid, time_)


@MPDConnection.Command("seekcur")
def _cmd_seekcur(conn, service, args):
    _verify_length(args, 1)

    relative = False
    time_ = args[0]
    if time_.startswith(("+", "-")):
        relative = True

    try:
        time_ = float(time_)
    except ValueError as e:
        raise MPDRequestError("arg not a number") from e

    service.seekcur(time_, relative)


@MPDConnection.Command("outputs")
def _cmd_outputs(conn, service, args):
    conn.write_line("outputid: 0")
    conn.write_line("outputname: dummy")
    conn.write_line("outputenabled: 1")


@MPDConnection.Command("commands", permission=Permissions.PERMISSION_NONE)
def _cmd_commands(conn, service, args):
    for name in conn.list_commands():
        conn.write_line(f"command: {name!s}")


@MPDConnection.Command("tagtypes")
def _cmd_tagtypes(conn, service, args):
    for mpd_key, _ql_key in TAG_MAPPING:
        conn.write_line(mpd_key)


@MPDConnection.Command("lsinfo")
def _cmd_lsinfo(conn, service, args):
    _verify_length(args, 1)


@MPDConnection.Command("playlistinfo")
def _cmd_playlistinfo(conn, service, args):
    if args:
        _verify_length(args, 1)
        start, end = _parse_range(args[0])
        result = service.playlistinfo(start, end)
    else:
        result = service.playlistinfo()
    if result is not None:
        conn.write_line(result)


@MPDConnection.Command("playlistid")
def _cmd_playlistid(conn, service, args):
    if args:
        songid = _parse_int(args[0])
    else:
        songid = None
    result = service.playlistid(songid)
    if result is not None:
        conn.write_line(result)
