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
    NONE = 0
    READ = 1
    ADD = 2
    CONTROL = 4
    ADMIN = 8
    ALL = (
        NONE
        | READ
        | ADD
        | CONTROL
        | ADMIN
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

        # Queue-as-playlist note: when the queue is empty but playback is
        # sourced from the main song list, MPD clients will see an empty
        # playlist (playlistlength=0, playlist/playlistinfo empty) while
        # currentsong still reports the active track.
        self._queue_model = None
        self._queue_sigs = []

        self._config = config
        self._options = app.player_options

        # If no password is set, all clients get full permissions by default.
        if not self._config.config_get("password"):
            self.default_permission = Permissions.ALL
        else:
            self.default_permission = Permissions.NONE

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

        # Queue support design notes:
        # - We treat the QL queue as the MPD "current playlist".
        # - MPD song IDs are derived from the song object's identity (see _get_id),
        #   so they are process-local and change if the backing object changes.
        # - Playlist version (_pl_ver) increments on queue mutations so MPD
        #   clients using idle can observe playlist changes.
        self._queue_model = self._get_queue_model()
        if self._queue_model is not None:
            for signal_name in ("row-inserted", "row-deleted", "rows-reordered"):
                self._queue_sigs.append(
                    self._queue_model.connect(signal_name, self._queue_changed)
                )

    def _get_queue_model(self):
        window = getattr(self._app, "window", None)
        qexpander = getattr(window, "qexpander", None)
        return getattr(qexpander, "model", None)

    def _queue_changed(self, *args):
        self._pl_ver += 1
        self.emit_changed("playlist")

    def _get_id(self, info):
        # XXX: we need a unique 31 bit ID, but don't have one.
        # Given that the heap is continuous and each object is >16 bytes
        # this should work
        return (id(info) & 0xFFFFFFFF) >> 1

    def destroy(self):
        for id_ in self._player_sigs:
            self._app.player.disconnect(id_)
        for id_ in self._queue_sigs:
            if self._queue_model is not None:
                self._queue_model.disconnect(id_)
        self._queue_sigs = []
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

        queue_length = self.queue_length()

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
            ("playlistlength", queue_length),
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

    def queue_songs(self):
        if self._queue_model is None:
            return []
        return [row[0] for row in self._queue_model]

    def queue_length(self):
        if self._queue_model is None:
            return 0
        return len(self._queue_model)

    def queue_songinfo(self, start=None, end=None):
        start, _end, songs = self._slice_queue(start, end)

        info = []
        for index, song in enumerate(songs, start=start):
            info.append(self._format_queue_song(song, index))
        return info

    def queue_songinfo_by_id(self, songid):
        info = []
        for index, song in enumerate(self.queue_songs()):
            if self._get_id(song) != songid:
                continue
            info.append(self._format_queue_song(song, index))
        return info

    def _format_queue_song(self, song, index):
        parts = []
        parts.append(f"file: {song('~filename')}")
        tag_info = format_tags(song)
        if tag_info:
            parts.append(tag_info)
        parts.append(f"Time: {int(song('~#length') or 0):d}")
        parts.append(f"Pos: {index:d}")
        parts.append(f"Id: {self._get_id(song):d}")
        return "\n".join(parts)

    def queue_song_by_pos(self, songpos):
        songs = self.queue_songs()
        if songpos < 0 or songpos >= len(songs):
            raise MPDRequestError("No such song", AckError.NO_EXIST)
        return songs[songpos]

    def queue_playlist(self, start=None, end=None):
        _start, _end, songs = self._slice_queue(start, end)
        return [f"file: {song('~filename')}" for song in songs]

    def queue_posid_info(self):
        info = []
        for index, song in enumerate(self.queue_songs()):
            parts = [
                f"file: {song('~filename')}",
                f"Pos: {index:d}",
                f"Id: {self._get_id(song):d}",
            ]
            info.append("\n".join(parts))
        return info

    def _slice_queue(self, start, end):
        songs = self.queue_songs()
        if start is None and end is None:
            return 0, len(songs), songs
        start = 0 if start is None else start
        end = len(songs) if end is None else end
        return start, end, songs[start:end]

    def queue_remove_positions(self, positions):
        if self._queue_model is None:
            raise MPDRequestError("No queue", AckError.NO_EXIST)
        for pos in sorted(positions, reverse=True):
            if pos < 0 or pos >= len(self._queue_model):
                raise MPDRequestError("No such song", AckError.NO_EXIST)
            iter_ = self._queue_model.get_iter((pos,))
            self._queue_model.remove(iter_)

    def queue_insert(self, songs, position=None):
        if self._queue_model is None:
            raise MPDRequestError("No queue", AckError.NO_EXIST)
        if position is None or position >= len(self._queue_model):
            self._queue_model.append_many(songs)
            return
        if position < 0:
            raise MPDRequestError("No such song", AckError.NO_EXIST)
        for offset, song in enumerate(songs):
            self._queue_model.insert(position + offset, row=[song])

    def playlistinfo(self, start=None, end=None):
        if start is not None and start > 1:
            return None

        return self.currentsong()

    def playlistid(self, songid=None):
        return self.currentsong()

    def plchanges(self, version):
        if version != self._pl_ver:
            return self.queue_songinfo()
        return []

    def plchangesposid(self, version):
        if version != self._pl_ver:
            return self.queue_posid_info()
        return []


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
        self.service.destroy()
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
            self.permission = Permissions.ALL
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
    def Command(cls, name, permission=Permissions.ADMIN, ack=True):
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


def _parse_songpos(arg):
    pos = _parse_int(arg)
    if pos < 0:
        raise MPDRequestError("No such song", AckError.NO_EXIST)
    return pos


@MPDConnection.Command("idle", ack=False)
def _cmd_idle(conn, service, args):
    service.register_idle(conn, args)


@MPDConnection.Command("ping", Permissions.NONE)
def _cmd_ping(conn, service, args):
    return


@MPDConnection.Command("password", Permissions.NONE)
def _cmd_password(conn, service, args):
    _verify_length(args, 1)
    conn.authenticate(args[0])


@MPDConnection.Command("noidle")
def _cmd_noidle(conn, service, args):
    service.unregister_idle(conn)


@MPDConnection.Command("close", Permissions.NONE, ack=False)
def _cmd_close(conn, service, args):
    conn.close()


@MPDConnection.Command("play", Permissions.CONTROL)
def _cmd_play(conn, service, args):
    if args:
        _verify_length(args, 1)
        songpos = _parse_songpos(args[0])
        song = service.queue_song_by_pos(songpos)
        service._app.player.go_to(song, explicit=True, source=service._queue_model)
        service._app.player.paused = False
    else:
        service.play()


@MPDConnection.Command("listplaylists", Permissions.READ)
def _cmd_listplaylists(conn, service, args):
    pass


@MPDConnection.Command("list", Permissions.READ)
def _cmd_list(conn, service, args):
    pass


@MPDConnection.Command("playid", Permissions.CONTROL)
def _cmd_playid(conn, service, args):
    _verify_length(args, 1)
    songid = _parse_int(args[0])
    for song in service.queue_songs():
        if service._get_id(song) == songid:
            service._app.player.go_to(song, explicit=True, source=service._queue_model)
            service._app.player.paused = False
            return
    raise MPDRequestError("No such song", AckError.NO_EXIST)


@MPDConnection.Command("pause", Permissions.CONTROL)
def _cmd_pause(conn, service, args):
    value = None
    if args:
        _verify_length(args, 1)
        value = _parse_bool(args[0])
    service.pause(value)


@MPDConnection.Command("stop", Permissions.CONTROL)
def _cmd_stop(conn, service, args):
    service.stop()


@MPDConnection.Command("next", Permissions.CONTROL)
def _cmd_next(conn, service, args):
    service.next()


@MPDConnection.Command("previous", Permissions.CONTROL)
def _cmd_previous(conn, service, args):
    service.previous()


@MPDConnection.Command("repeat", Permissions.CONTROL)
def _cmd_repeat(conn, service, args):
    _verify_length(args, 1)
    value = _parse_bool(args[0])
    service.repeat(value)


@MPDConnection.Command("random", Permissions.CONTROL)
def _cmd_random(conn, service, args):
    _verify_length(args, 1)
    value = _parse_bool(args[0])
    service.random(value)


@MPDConnection.Command("single", Permissions.CONTROL)
def _cmd_single(conn, service, args):
    _verify_length(args, 1)
    value = _parse_bool(args[0])
    service.single(value)


@MPDConnection.Command("setvol", Permissions.CONTROL)
def _cmd_setvol(conn, service, args):
    _verify_length(args, 1)
    value = _parse_int(args[0])
    service.setvol(value)


@MPDConnection.Command("status", Permissions.READ)
def _cmd_status(conn, service, args):
    status = service.status()
    for k, v in status:
        conn.write_line(f"{k}: {v}")


@MPDConnection.Command("stats", Permissions.READ)
def _cmd_stats(conn, service, args):
    status = service.stats()
    for k, v in status:
        conn.write_line(f"{k}: {v}")


@MPDConnection.Command("currentsong", Permissions.READ)
def _cmd_currentsong(conn, service, args):
    stats = service.currentsong()
    if stats is not None:
        conn.write_line(stats)


@MPDConnection.Command("count", Permissions.READ)
def _cmd_count(conn, service, args):
    conn.write_line("songs: 0")
    conn.write_line("playtime: 0")


@MPDConnection.Command("plchanges", Permissions.READ)
def _cmd_plchanges(conn, service, args):
    _verify_length(args, 1)
    version = _parse_int(args[0])
    changes = service.plchanges(version)
    for entry in changes:
        conn.write_line(entry)


@MPDConnection.Command("plchangesposid", Permissions.READ)
def _cmd_plchangesposid(conn, service, args):
    _verify_length(args, 1)
    version = _parse_int(args[0])
    changes = service.plchangesposid(version)
    for entry in changes:
        conn.write_line(entry)


@MPDConnection.Command("listallinfo", Permissions.READ)
def _cmd_listallinfo(*args):
    _cmd_currentsong(*args)


@MPDConnection.Command("seek", Permissions.CONTROL)
def _cmd_seek(conn, service, args):
    _verify_length(args, 2)
    songpos = _parse_int(args[0])
    time_ = _parse_int(args[1])
    service.seek(songpos, time_)


@MPDConnection.Command("seekid", Permissions.CONTROL)
def _cmd_seekid(conn, service, args):
    _verify_length(args, 2)
    songid = _parse_int(args[0])
    time_ = _parse_int(args[1])
    service.seekid(songid, time_)


@MPDConnection.Command("seekcur", Permissions.CONTROL)
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


@MPDConnection.Command("outputs", Permissions.READ)
def _cmd_outputs(conn, service, args):
    conn.write_line("outputid: 0")
    conn.write_line("outputname: dummy")
    conn.write_line("outputenabled: 1")


@MPDConnection.Command("commands", Permissions.NONE)
def _cmd_commands(conn, service, args):
    for name in conn.list_commands():
        conn.write_line(f"command: {name!s}")


@MPDConnection.Command("tagtypes", Permissions.READ)
def _cmd_tagtypes(conn, service, args):
    for mpd_key, _ql_key in TAG_MAPPING:
        conn.write_line(mpd_key)


@MPDConnection.Command("lsinfo", Permissions.READ)
def _cmd_lsinfo(conn, service, args):
    _verify_length(args, 1)


@MPDConnection.Command("playlistinfo", Permissions.READ)
def _cmd_playlistinfo(conn, service, args):
    if args:
        _verify_length(args, 1)
        start, end = _parse_range(args[0])
    else:
        start = end = None
    for entry in service.queue_songinfo(start, end):
        conn.write_line(entry)


@MPDConnection.Command("playlistid", Permissions.READ)
def _cmd_playlistid(conn, service, args):
    if args:
        songid = _parse_int(args[0])
        matches = service.queue_songinfo_by_id(songid)
    else:
        matches = service.queue_songinfo()
    for entry in matches:
        conn.write_line(entry)


@MPDConnection.Command("playlist", Permissions.READ)
def _cmd_playlist(conn, service, args):
    if args:
        _verify_length(args, 1)
        start, end = _parse_range(args[0])
    else:
        start = end = None
    for entry in service.queue_playlist(start, end):
        conn.write_line(entry)


@MPDConnection.Command("clear", Permissions.ADD)
def _cmd_clear(conn, service, args):
    _verify_length(args, 0)
    if service._queue_model is None:
        raise MPDRequestError("No queue", AckError.NO_EXIST)
    service._queue_model.clear()


@MPDConnection.Command("delete", Permissions.ADD)
def _cmd_delete(conn, service, args):
    _verify_length(args, 1)
    pos = _parse_songpos(args[0])
    service.queue_remove_positions([pos])


@MPDConnection.Command("add", Permissions.ADD)
def _cmd_add(conn, service, args):
    _verify_length(args, 1)
    filename = args[0]
    song = service._app.library.add_filename(filename, add=False)
    if song is None:
        raise MPDRequestError("No such song", AckError.NO_EXIST)
    service.queue_insert([song])


@MPDConnection.Command("addid", Permissions.ADD)
def _cmd_addid(conn, service, args):
    _verify_length(args, 1)
    filename = args[0]
    song = service._app.library.add_filename(filename, add=False)
    if song is None:
        raise MPDRequestError("No such song", AckError.NO_EXIST)
    service.queue_insert([song])
    conn.write_line(f"Id: {service._get_id(song):d}")
