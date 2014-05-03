# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import re
import shlex

from quodlibet import app
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


class MPDService(object):
    """This is the actual shared MPD service which the clients talk to"""

    version = (0, 17, 0)

    def play(self):
        if not app.player.song:
            app.player.reset()
        else:
            app.player.paused = False

    def playid(self, songid):
        # -1 is any
        self.play()

    def pause(self):
        app.player.paused = True

    def stop(self):
        app.player.stop()

    def next(self):
        app.player.next()

    def previous(self):
        app.player.previous()

    def seek(self, songpos, time_):
        """time_ in seconds"""

        app.player.seek(time_ * 1000)

    def seekid(self, songid, time_):
        """time_ in seconds"""

        app.player.seek(time_ * 1000)

    def seekcur(self, value, relative):
        if relative:
            pos = app.player.get_position()
            app.player.seek(pos + value)
        else:
            app.player.seek(value)

    def setvol(self, value):
        """value: 0..100"""

        app.player.volume = value / 100.0

    def repeat(self, value):
        app.window.repeat.set_active(value)

    def stats(self):
        stats = [
            ("artists", 1),
            ("albums", 1),
            ("songs", 1),
            ("uptime", 1),
            ("playtime", 1),
            ("db_playtime", 1),
            ("db_update", 1252868674),
        ]

        return stats

    def status(self):
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
            ("repeat", int(app.window.repeat.get_active())),
            ("random", 0),
            ("single", 0),
            ("consume", 0),
            ("playlist", 0),
            ("playlistlength", int(bool(app.player.info))),
            ("state", state),
            ("song", 0),
            ("songid", 0),
            ("nextsong", 0),
            ("nextsongid", 0),
            ("time", "%d:%d" % (
                int(app.player.get_position() / 1000),
                info and info("~#length") or 0)),
        ]

        return status

    def currentsong(self):
        song = app.player.info
        if song is None:
            return None

        parts = []
        parts.append(u"file: %s" % song("~uri"))
        parts.append(format_tags(song))
        parts.append(u"Pos: %d" % 0)
        parts.append(u"Id: %d" % 0)
        # TODO: modified time

        return u"\n".join(parts)

    def playlistinfo(self, start, end):
        song = app.player.info
        if song is None:
            return None

        if start > 1:
            return None

        parts = []
        parts.append(format_tags(song))
        parts.append(u"Pos: %d" % 0)
        parts.append(u"Id: %d" % 0)
        return u"\n".join(parts)

    def playlistid(self, songid=None):
        # XXX
        return

        if songid is None:
            return self.playlistinfo(0, 1)

        song = app.player.info
        if song is None:
            return None

        parts = []
        parts.append(format_tags(song))
        parts.append(u"Pos: %d" % 1)
        parts.append(u"Id: %d" % 1)
        return u"\n".join(parts)


class MPDServer(BaseTCPServer):

    def __init__(self, port):
        super(MPDServer, self).__init__(port, MPDConnection, const.DEBUG)
        self.service = MPDService()

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

    def _ok(self):
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

            self._ok()
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
            self._ok()
            return

        cmd, do_ack = self._commands[command]
        cmd(self, self.service, args)
        if do_ack:
            self._ok()

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
    if not len(args) < length:
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
    # TODO: register for events
    pass


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
