# Copyright 2014-2024 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import socket
import time
from urllib.parse import quote, unquote

from quodlibet import _
from quodlibet import app
from quodlibet.util.dprint import print_w, print_d, print_


class SqueezeboxError(Exception):
    """Errors communicating with the Squeezebox"""


class SqueezeboxServerSettings(dict):
    """Encapsulates Server settings"""

    def __str__(self):
        try:
            return _("Squeezebox server at {hostname}:{port}").format(**self)
        except KeyError:
            return _("unidentified Squeezebox server")


class SqueezeboxPlayerSettings(dict):
    """Encapsulates player settings"""

    def __str__(self):
        try:
            return "{name} [{playerid}]".format(**self)
        except KeyError:
            return _("unidentified Squeezebox player: %r") % self


class SqueezeboxServer:
    """Encapsulates access to a Squeezebox player via a squeezecenter server"""

    _TIMEOUT = 10
    _MAX_FAILURES = 3
    telnet = None
    is_connected = False
    current_player = 0
    players: list[SqueezeboxPlayerSettings] = []
    config = SqueezeboxServerSettings()
    _debug = False

    def __init__(
        self,
        hostname="localhost",
        port=9090,
        user="",
        password="",
        library_dir="",
        current_player=0,
        debug=False,
    ):
        self._debug = debug
        self.failures = 0
        self.delta = 600  # Default in ms
        self.config = SqueezeboxServerSettings(locals())
        if hostname:
            del self.config["self"]
            del self.config["current_player"]
            self.current_player = int(current_player) or 0
            try:
                if self._debug:
                    print_d(f"Trying {self.config}...")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(self._TIMEOUT)
                self.socket.connect((socket.gethostbyname(hostname), port))
            except OSError as e:
                print_d(f"Couldn't talk to {self.config} ({e})")
            else:
                result = self.__request(f"login {user} {password}")
                if result != (6 * "*"):
                    raise SqueezeboxError(
                        f"Couldn't log in to squeezebox: response was '{result}'"
                    )
                self.is_connected = True
                self.failures = 0
                print_d(f"Connected to Squeezebox Server! {self}")
                # Reset players (forces reload)
                self.players = []
                self.get_players()

    def get_library_dir(self):
        return self.config["library_dir"]

    def __request(self, line, raw=False, want_reply=True):
        """
        Send a request to the server, if connected, and return its response
        """
        line = line.strip()

        if not (self.is_connected or line.split()[0] == "login"):
            print_d(f"Can't do '{line.split()[0]}' - not connected", self)
            return None

        if self._debug:
            print_(f'>>>> "{line}"')
        try:
            self.socket.send((line + "\n").encode("utf-8"))
            if not want_reply:
                return None
            raw_response = b""
            while not raw_response.endswith(b"\n"):
                raw_response += self.socket.recv(1)
            raw_response = raw_response.decode("utf-8")
        except (TimeoutError, OSError) as e:
            print_w(f"Couldn't communicate with squeezebox ({e})")
            self.failures += 1
            if self.failures >= self._MAX_FAILURES:
                print_w("Too many Squeezebox failures. Disconnecting")
                self.is_connected = False
            return None
        response = (raw_response if raw else unquote(raw_response)).strip()
        if self._debug:
            print_(f'<<<< "{response}"')
        return (
            response[len(line) - 1 :]
            if line.endswith("?")
            else response[len(line) + 1 :]
        )

    def get_players(self):
        """Returns (and caches) a list of the Squeezebox players available"""
        if self.players:
            return self.players
        pairs = self.__request("players 0 99", True).split(" ")

        def demunge(string):
            s = unquote(string)
            cpos = s.index(":")
            return s[0:cpos], s[cpos + 1 :]

        # Do a meaningful URL-unescaping and tuplification for all values
        pairs = [demunge(p) for p in pairs]

        # First element is always count
        count = int(pairs.pop(0)[1])
        self.players = []
        for pair in pairs:
            if pair[0] == "playerindex":
                playerindex = int(pair[1])
                self.players.append(SqueezeboxPlayerSettings())
            else:
                # Don't worry playerindex is always the first entry...
                self.players[playerindex][pair[0]] = pair[1]
        if self._debug:
            print_d("Found %d player(s): %s" % (len(self.players), self.players))
        assert count == len(self.players)
        return self.players

    def player_request(self, line, want_reply=True):
        if not self.is_connected:
            return None
        try:
            return self.__request(
                f"{self.players[self.current_player]['playerid']} {line}",
                want_reply=want_reply,
            )
        except IndexError:
            return None

    def get_version(self):
        if self.is_connected:
            return self.__request("version ?")
        return "(not connected)"

    def play(self):
        """Plays the current song"""
        self.player_request("play")

    def is_stopped(self):
        """Returns whether the player is in any sort of non-playing mode"""
        response = self.player_request("mode ?")
        return "play" != response

    def playlist_play(self, path):
        """Play song immediately"""
        self.player_request(f"playlist play {quote(path)}")

    def playlist_add(self, path):
        self.player_request(f"playlist add {quote(path)}", False)

    def playlist_save(self, name):
        self.player_request(f"playlist save {quote(name)}", False)

    def playlist_clear(self):
        self.player_request("playlist clear", False)

    def playlist_resume(self, name, resume, wipe=False):
        cmd = "playlist resume %s noplay:%d wipePlaylist:%d" % (
            quote(name),
            int(not resume),
            int(wipe),
        )
        self.player_request(cmd, want_reply=False)

    def change_song(self, path):
        """Queue up a song"""
        self.player_request("playlist clear")
        self.player_request(f"playlist insert {quote(path)}")

    def seek_to(self, ms):
        """Seeks the current song to `ms` milliseconds from start"""
        if not self.is_connected:
            return
        if self._debug:
            print_d(
                "Requested %0.2f s, adding drift of %d ms..."
                % (ms / 1000.0, self.delta)
            )
        ms += self.delta
        start = time.time()
        self.player_request("time %d" % round(int(ms) / 1000))
        end = time.time()
        took = (end - start) * 1000
        reported_time = self.get_milliseconds()
        ql_pos = app.player.get_position()
        # Assume 50% of the time taken to complete is response.
        # TODO: Better predictive modelling
        new_delta = ql_pos - reported_time
        self.delta = (self.delta + new_delta) / 2
        if self._debug:
            print_d(
                f"Player at {reported_time / 1000.0:0.0f} "
                f"but QL at {ql_pos / 1000.0:0.2f}."
                f"(Took {took:0.0f} ms). Drift was {new_delta:+0.0f} ms"
            )

    def get_milliseconds(self):
        secs = self.player_request("time ?") or 0
        return float(secs) * 1000.0

    def pause(self):
        self.player_request("pause 1")

    def unpause(self):
        if self.is_stopped():
            self.play()
        ms = app.player.get_position()
        self.seek_to(ms)

    def stop(self):
        self.player_request("stop")

    def __str__(self):
        return str(self.config)
