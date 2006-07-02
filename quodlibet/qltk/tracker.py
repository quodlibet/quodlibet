# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import time

import config

class SongTracker(object):
    def __init__(self, watcher, player, pl):
        player.connect_object('song-ended', self.__end, watcher, pl)
        player.connect_object('song-started', self.__start, watcher)
        player.connect('error', self.__error)

    def __error(self, player, error, lock):
        config.set("memory", "song", "")

    def __start(self, watcher, song):
        if song is not None:
            if song.multisong:
                song["~#lastplayed"] = int(time.time())
                song["~#playcount"] = song.get("~#playcount", 0) + 1
            else:
                config.set("memory", "song", song["~filename"])
            song["~#laststarted"] = int(time.time())
            watcher.changed([song])

    def __end(self, watcher, song, ended, pl):
        config.set("memory", "song", "")
        if song is None or song.multisong:
            return
        elif not ended:
            song["~#lastplayed"] = int(time.time())
            song["~#playcount"] = song.get("~#playcount", 0) + 1
            watcher.changed([song])
        elif pl.current is not song:
            song["~#skipcount"] = song.get("~#skipcount", 0) + 1
            watcher.changed([song])
