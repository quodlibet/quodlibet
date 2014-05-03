# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import re
import shlex

from gi.repository import GLib, GObject

from quodlibet import const
from .tcpserver import BaseTCPServer, BaseTCPConnection


class AckError(object):
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


TAG_MAPPING = [
    (u"Artist", "artist"),
    (u"ArtistSort", "artistsort"),
    (u"Album", "album"),
    (u"AlbumArtist", "albumartist"),
    (u"AlbumArtistSort", "albumartistsort"),
    (u"Title", "title"),
    (u"Track", "~#track"),
    (u"Name", ""),
    (u"Genre", "genre"),
    (u"Date", "~year"),
    (u"Composer", "composer"),
    (u"Performer", "performer"),
    (u"Comment", "commend"),
    (u"Disc", "~#disc"),
    (u"MUSICBRAINZ_ARTISTID", "musicbrainz_artistid"),
    (u"MUSICBRAINZ_ALBUMID", "musicbrainz_albumid"),
    (u"MUSICBRAINZ_ALBUMARTISTID", "musicbrainz_albumartistid"),
    (u"MUSICBRAINZ_TRACKID", "musicbrainz_trackid"),
]


def format_tags(song):
    """Gives a tag list message for a song"""

    lines = []
    for mpd_key, ql_key in TAG_MAPPING:
        if not ql_key:
            continue

        if ql_key.startswith("~#"):
            value = song(ql_key, None)
            if value is not None:
                value = str(value)
        else:
            value = song.comma(ql_key) or None

        if value is not None:
            lines.append(u"%s: %s" % (mpd_key, value))

    return u"\n".join(lines)


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



class PlayerOptions(GObject.Object):
    """Provides a simplified interface for playback options.

    This should probably go into the core.
    """

    __gsignals__ = {
        'random-changed': (GObject.SignalFlags.RUN_LAST, None, tuple()),
        'repeat-changed': (GObject.SignalFlags.RUN_LAST, None, tuple()),
    }

    def __init__(self, app):
        super(PlayerOptions, self).__init__()

        self._repeat = app.window.repeat
        self._rid = self._repeat.connect(
            "toggled", lambda *x: self.emit("repeat-changed"))

        self._order = app.window.order
        self._oid = self._order.connect(
            "changed", lambda *x: self.emit("random-changed"))

    def destroy(self):
        self._repeat.disconnect(self._rid)
        del self._repeat
        self._order.disconnect(self._oid)
        del self._order

    def get_random(self):
        return self._order.get_active_name() == "shuffle"

    def set_random(self, value):
        if value:
            self._order.set_active("shuffle")
        else:
            self._order.set_active("inorder")

    def get_repeat(self):
        return self._repeat.get_active()

    def set_repeat(self, value):
        self._repeat.set_active(value)


class MPDService(object):
    """This is the actual shared MPD service which the clients talk to"""

    version = (0, 17, 0)

    def __init__(self, app):
        self._app = app
        self._connections = set()
        self._idle_subscriptions = {}
        self._pl_ver = 0

        self._options = PlayerOptions(app)

        def options_changed(*args):
            self.emit_changed("options")

        self._options.connect("random-changed", options_changed)
        self._options.connect("repeat-changed", options_changed)

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

    def _get_id(self):
        info = self._app.player.info
        if info is None:
            return
        return id(info)

    def _change_playlist(self):
        self._pl_ver += 1
        self.emit_changed("playlist")

    def destroy(self):
        for id_ in self._player_sigs:
            self._app.player.disconnect(id_)
        self._options.destroy()
        del self._app
        del self._options

    def add_connection(self, connection):
        self._connections.add(connection)

    def remove_connection(self, connection):
        self._idle_subscriptions.pop(connection, None)
        self._connections.remove(connection)

    def register_idle(self, connection, subsystems):
        self._idle_subscriptions[connection] = subsystems

    def unregister_idle(self, connection):
        del self._idle_subscriptions[connection]

    def emit_changed(self, subsystem):
        for conn, subs in self._idle_subscriptions.iteritems():
            if not subs or subsystem in subs:
                conn.write_line(u"changed: %s" % subsystem)
                conn.ok()
                conn.start_write()

    def play(self):
        if not self._app.player.song:
            self._app.player.reset()
            self._change_playlist()
        else:
            self._app.player.paused = False

    def playid(self, songid):
        # -1 is any
        self.play()

    def pause(self):
        self._app.player.paused = True

    def stop(self):
        self._app.player.stop()

    def next(self):
        self._app.player.next()
        self._change_playlist()

    def previous(self):
        self._app.player.previous()
        self._change_playlist()

    def seek(self, songpos, time_):
        """time_ in seconds"""

        self._app.player.seek(time_ * 1000)

    def seekid(self, songid, time_):
        """time_ in seconds"""

        self._app.player.seek(time_ * 1000)

    def seekcur(self, value, relative):
        if relative:
            pos = self._app.player.get_position()
            self._app.player.seek(pos + value)
        else:
            self._app.player.seek(value)

    def setvol(self, value):
        """value: 0..100"""

        self._app.player.volume = value / 100.0

    def repeat(self, value):
        self._options.set_repeat(value)

    def random(self, value):
        self._options.set_random(value)

    def stats(self):
        has_song = int(bool(self._app.player.info))
        stats = [
            ("artists", has_song),
            ("albums", has_song),
            ("songs", has_song),
            ("uptime", 1),
            ("playtime", 1),
            ("db_playtime", 1),
            ("db_update", 1252868674),
        ]

        return stats

    def status(self):
        app = self._app
        info = app.player.info

        if info:
            if app.player.paused:
                # XXX: should be pause, MPDroid doesn't like it
                state = "stop"
            else:
                state = "play"
        else:
            state = "stop"

        status = [
            ("volume", int(app.player.volume * 100)),
            ("repeat", int(self._options.get_repeat())),
            ("random", int(self._options.get_random())),
            ("single", 0),
            ("consume", 0),
            ("playlist", self._pl_ver),
            ("playlistlength", int(bool(app.player.info))),
            ("state", state),
        ]

        if info:
            total_time = int(info("~#length"))
            elapsed_time = int(app.player.get_position() / 1000)
            elapsed_exact = "%1.3f" % (app.player.get_position() / 1000.0)

            status.extend([
                ("song", 0),
                ("songid", self._get_id()),
                ("time", "%d:%d" % (elapsed_time, total_time)),
                ("elapsed", elapsed_exact),
            ])

        return status

    def currentsong(self):
        song = self._app.player.info
        if song is None:
            return None

        parts = []
        parts.append(u"file: file://%s" % song("~basename"))
        parts.append(format_tags(song))
        parts.append(u"Pos: %d" % 0)
        parts.append(u"Id: %d" % self._get_id())
        # TODO: modified time

        return u"\n".join(parts)

    def playlistinfo(self, start, end):
        song = self._app.player.info
        if song is None:
            return None

        if start > 1:
            return None

        parts = []
        parts.append(format_tags(song))
        parts.append(u"Pos: %d" % 0)
        parts.append(u"Id: %d" % self._get_id())
        return u"\n".join(parts)

    def playlistid(self, songid=None):
        return self.playlistinfo(0, 1)


class MPDServer(BaseTCPServer):

    def __init__(self, app, port):
        self._app = app
        super(MPDServer, self).__init__(port, MPDConnection, const.DEBUG)

    def handle_init(self):
        print_d("Creating the MPD service")
        self.service = MPDService(self._app)

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
        self._buf = bytearray("OK MPD %s\n" % str_version)
        self._read_buf = bytearray()

        # begin - command processing state
        self._use_command_list = False
        # everything below is only valid if _use_command_list is True
        self._command_list_ok = False
        self._command_list = []
        self._command = None
        # end - command processing state

        self.start_write()
        self.start_read()

    def handle_read(self, data):
        self._feed_data(data)

        line = self._get_next_line()
        if line is None:
            return

        self.log(repr(line))

        try:
            cmd, args = parse_command(line)
        except ParseError:
            # TODO: not sure what to do here re command lists
            return

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

    def log(self, msg):
        if const.DEBUG:
            print_d("[%s] %s" % (self.name, msg))

    def _feed_data(self, new_data):
        """Feed new data into the read buffer"""

        self._read_buf.extend(new_data)

    def _get_next_line(self):
        """Returns the next line from the read buffer or None"""

        try:
            index = self._read_buf.index("\n")
        except ValueError:
            return None, []

        line = bytes(self._read_buf[:index])
        del self._read_buf[:index + 1]
        return line

    def write_line(self, line):
        """Writes a line to the client"""

        assert isinstance(line, unicode)

        self._buf.extend(line.encode("utf-8", errors="replace") + "\n")

    def ok(self):
        self.write_line(u"OK")

    def _error(self, msg, code, index):
        error = []
        error.append(u"ACK [%d" % code)
        if index is not None:
            error.append(u"@%d" % index)
        assert self._command is not None
        error.append("u] {%s}" % self._command)
        if msg is not None:
            error.append(u" %s" % msg)
        self.write_line(u"".join(error))

    def _handle_command(self, command, args):
        self._command = command

        if command == u"command_list_end":
            if not self._use_command_list:
                self._error(u"list_end without begin")
                return

            for i, (cmd, args) in enumerate(self._command_list):
                try:
                    self._exec_command(cmd, args)
                except MPDRequestError as e:
                    # reraise with index
                    raise MPDRequestError(e.msg, e.code, i)

                if self._command_list_ok:
                    self.write_line(U"list_OK")

            self.ok()
            self._use_command_list = False
            del self._command_list[:]
            return

        if command in (u"command_list_begin", u"command_list_ok_begin"):
            if self._use_command_list:
                raise MPDRequestError(u"begin without end")

            self._use_command_list = True
            self._command_list_ok = command == u"command_list_ok_begin"
            assert not self._command_list
            return

        if self._use_command_list:
            self._command_list.append((command, args))
        else:
            self._exec_command(command, args)

    def _exec_command(self, command, args):
        self._command = command

        if command not in self._commands:
            # Unhandled command, default to OK for now..
            self.ok()
            return

        cmd, do_ack = self._commands[command]
        cmd(self, self.service, args)
        if do_ack:
            self.ok()

    _commands = {}

    @classmethod
    def Command(cls, name, ack=True):

        def wrap(func):
            assert name not in cls._commands, name
            cls._commands[name] = (func, ack)
            return func

        return wrap

    @classmethod
    def list_commands(cls):
        """A list of supported commands"""

        return cls._commands.keys()


def _verify_length(args, length):
    if not len(args) <= length:
        raise MPDRequestError("Wrong arg count")


def _parse_int(arg):
    try:
        return int(arg)
    except ValueError:
        raise MPDRequestError("invalid arg")


def _parse_bool(arg):
    try:
        value = int(arg)
        if value not in (0, 1):
            raise ValueError
    except ValueError:
        raise MPDRequestError("invalid arg")
    else:
        return bool(value)


def _parse_range(arg):
    try:
        values = [int(v) for v in arg.split(":")]
    except ValueError:
        raise MPDRequestError("arg in range not a number")

    if len(values) == 1:
        return (values[0], values[0] + 1)
    elif len(values) == 2:
        return values
    else:
        raise MPDRequestError("invalid range")


@MPDConnection.Command("idle", ack=False)
def _cmd_idle(conn, service, args):
    service.register_idle(conn, args)


@MPDConnection.Command("noidle")
def _cmd_noidle(conn, service, args):
    service.unregister_idle(conn)


@MPDConnection.Command("close", ack=False)
def _cmd_close(conn, service, args):
    conn.close()


@MPDConnection.Command("play")
def _cmd_play(conn, service, args):
    service.play()


@MPDConnection.Command("playid")
def _cmd_playid(conn, service, args):
    _verify_length(args, 1)
    songid = _parse_int(args[0])
    service.playid(songid)


@MPDConnection.Command("pause")
def _cmd_pause(conn, service, args):
    service.pause()


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



@MPDConnection.Command("setvol")
def _cmd_setvol(conn, service, args):
    _verify_length(args, 1)
    value = _parse_int(args[0])
    service.setvol(value)


@MPDConnection.Command("status")
def _cmd_status(conn, service, args):
    status = service.status()
    for k, v in status:
        conn.write_line(u"%s: %s" % (k, v))


@MPDConnection.Command("stats")
def _cmd_stats(conn, service, args):
    status = service.stats()
    for k, v in status:
        conn.write_line(u"%s: %s" % (k, v))


@MPDConnection.Command("currentsong")
def _cmd_currentsong(conn, service, args):
    stats = service.currentsong()
    if stats is not None:
        conn.write_line(stats)


@MPDConnection.Command("count")
def _cmd_count(conn, service, args):
    conn.write_line(u"songs: 0")
    conn.write_line(u"playtime: 0")


@MPDConnection.Command("plchanges")
def _cmd_plchanges(*args):
    _cmd_currentsong(*args)


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
        time_ = int(time_)
    except ValueError:
        raise MPDRequestError("arg not a number")

    service.seekid(time_, relative)


@MPDConnection.Command("outputs")
def _cmd_outputs(conn, service, args):
    conn.write_line(u"outputid: 0")
    conn.write_line(u"outputname: dummy")
    conn.write_line(u"outputenabled: 1")


@MPDConnection.Command("commands")
def _cmd_commands(conn, service, args):
    for name in conn.list_commands():
        conn.write_line(unicode(name))


@MPDConnection.Command("tagtypes")
def _cmd_tagtypes(conn, service, args):
    for mpd_key, ql_key in TAG_MAPPING:
        if ql_key:
            conn.write_line(mpd_key)


@MPDConnection.Command("lsinfo")
def _cmd_lsinfo(conn, service, args):
    _verify_length(args, 1)


@MPDConnection.Command("playlistinfo")
def _cmd_playlistinfo(conn, service, args):
    _verify_length(args, 1)
    start, end = _parse_range(args[0])
    result = service.playlistinfo(start, end)
    if result is not None:
        conn.write_line(result)


@MPDConnection.Command("playlistid")
def _cmd_playlistid(conn, service, args):
    _verify_length(args, 1)
    songid = _parse_int(args[0])
    result = service.playlistid(songid)
    if result is not None:
        conn.write_line(result)
