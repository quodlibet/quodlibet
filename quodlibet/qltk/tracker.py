# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#                2013 Christoph Reiter
#           2020-2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import time
from typing import Collection

from gi.repository import GObject, GLib

from quodlibet import config, print_d
from quodlibet.formats import AudioFile
from quodlibet.library.base import Library


class TimeTracker(GObject.GObject):
    """Emits tick every second (with up to one second jitter) as long
    as the player is actively playing.

    Uses timeout_add_seconds, so multiple instances of this should
    sync and not produce more wakeups.
    """

    __gsignals__ = {
        'tick': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, player):
        super().__init__()

        self.__interval = 1000
        self.__player = player
        self.__id = None
        self.__stop = False
        self.__reset = False
        self.__sigs = [
            player.connect("paused", self.__paused, True),
            player.connect("unpaused", self.__paused, False),
        ]
        self.__paused(player, player.paused)

    def set_interval(self, interval):
        """Update the resolution in milliseconds"""

        self.__interval = interval
        self.__reset = True

    def tick(self):
        """Emit a tick event"""

        self.emit("tick")

    def destroy(self):
        for signal_id in self.__sigs:
            self.__player.disconnect(signal_id)
        self.__source_remove()

    def __source_remove(self):
        if self.__id is not None:
            GLib.source_remove(self.__id)
            self.__id = None

    def __update(self):
        if self.__stop:
            self.__source_remove()
            return False

        if self.__reset:
            self.__reset = False
            self.__source_remove()
            self.__paused(self.__player, self.__player.paused)

        self.tick()
        return True

    def __paused(self, player, paused):
        if paused:
            # By removing the timeout only in the callback we are safe from
            # huge deviation caused by lots of pause/unpause actions.
            self.__stop = True
        else:
            self.__stop = False
            if self.__id is None:
                # The application is already woke up every seconds
                # so synchronize to it by calling timeout_add_seconds(...)
                # if the requested tracker interval is exactly 1 second.
                self.__id = GLib.timeout_add_seconds(1, self.__update) \
                    if self.__interval == 1000 \
                    else GLib.timeout_add(self.__interval, self.__update)


class SongTracker:

    def __init__(self, librarian, player, pl):
        self.__player_ids = [
            player.connect('song-ended', self.__end, librarian, pl),
            player.connect('song-started', self.__start, librarian),
        ]
        self.__player = player
        timer = TimeTracker(player)
        timer.connect("tick", self.__timer)
        self.elapsed = 0
        self.__to_change = set()
        self.__change_id = None

    def destroy(self):
        for id_ in self.__player_ids:
            self.__player.disconnect(id_)
        self.__player = None

        if self.__change_id:
            GLib.source_remove(self.__change_id)
            self.__change_id = None

    def __changed(self, librarian, song):
        # try to combine changed events and process them if QL is idle
        self.__to_change.add(song)

        if self.__change_id is not None:
            GLib.source_remove(self.__change_id)
            self.__change_id = None

        def idle_change():
            librarian.changed(list(self.__to_change))
            self.__to_change.clear()
            self.__change_id = None

        self.__change_id = GLib.idle_add(idle_change,
                                         priority=GLib.PRIORITY_LOW)

    def __start(self, player, song, librarian):
        self.elapsed = 0
        if song is not None:
            if song.multisong:
                song["~#lastplayed"] = int(time.time())
                song["~#playcount"] = song.get("~#playcount", 0) + 1
            else:
                config.set("memory", "song", song["~filename"])
            song["~#laststarted"] = int(time.time())
            self.__changed(librarian, song)
        else:
            config.set("memory", "song", "")

    def __end(self, player, song, ended, librarian, pl):
        if song is not None and not song.multisong:
            if ended:
                config.set("memory", "seek", player.get_position())
            else:
                config.set("memory", "seek", 0)

            if self.elapsed + 1 >= config.getint(
                "player", "consider_played_percent", 50) * song.get(
                "~#length", 1) / 100:
                song["~#lastplayed"] = int(time.time())
                song["~#playcount"] = song.get("~#playcount", 0) + 1
                self.__changed(librarian, song)
            elif pl.current is not song:
                if not player.error:
                    song["~#skipcount"] = song.get("~#skipcount", 0) + 1
                    self.__changed(librarian, song)
        else:
            config.set("memory", "seek", 0)

    def __timer(self, timer):
        self.elapsed += 1


class FSInterface:
    """Provides a file in ~/.quodlibet to indicate what song is playing."""

    def __init__(self, path, player, library: Library):
        self.path = path
        self._player = player
        self._pids = [
            player.connect('song-started', self.__started),
            player.connect('song-ended', self.__ended),
        ]
        self._lids = [library.connect('changed', self.__changed)]
        self._library = library

    def destroy(self):
        for id_ in self._pids:
            self._player.disconnect(id_)
        for id_ in self._lids:
            print_d(f"Disconnecting signal {id_} from {self._library}")
            self._library.disconnect(id_)
        try:
            os.unlink(self.path)
        except EnvironmentError:
            pass

    def __started(self, player, song):
        if song:
            song = player.with_elapsed_info(song)
            try:
                with open(self.path, "wb") as f:
                    f.write(song.to_dump())
            except EnvironmentError:
                pass

    def __ended(self, player, song, stopped):
        try:
            os.unlink(self.path)
        except EnvironmentError:
            pass

    def __changed(self, _lib: Library, songs: Collection[AudioFile]):
        current = self._player.song
        if current and current in songs:
            print_d("Current song changed, updating current file")
            self.__started(self._player, current)
