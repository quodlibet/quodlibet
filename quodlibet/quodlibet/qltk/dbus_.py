# -*- coding: utf-8 -*-
# Copyright 2006 Federico Pelloni <federico.pelloni@gmail.com>
#           2013 Christoph Reiter
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import dbus
import dbus.service
from dbus import DBusException

from quodlibet.util import dbusutils
from quodlibet.query import Query
from quodlibet.qltk.songlist import SongList
from quodlibet.formats import decode_value
from quodlibet.compat import itervalues


class DBusHandler(dbus.service.Object):
    def __init__(self, player, library):
        try:
            self.library = library
            bus = dbus.SessionBus()
            name = dbus.service.BusName(
                'io.github.quodlibet.QuodLibet',
                bus=bus)
            path = '/io/github/quodlibet/QuodLibet'
            super(DBusHandler, self).__init__(name, path)
        except DBusException:
            pass
        else:
            player.connect('song-started', self.__song_started)
            player.connect('song-ended', self.__song_ended)
            player.connect('paused', lambda player: self.Paused())
            player.connect('unpaused', lambda player: self.Unpaused())
            self._player = player

    def __dict(self, song):
        dict = {}
        for key, value in (song or {}).items():
            value = decode_value(key, value)
            dict[key] = dbusutils.dbus_unicode_validate(value)
        if song:
            dict["~uri"] = song("~uri")
        return dict

    def __song_started(self, player, song):
        if song is not None:
            song = self.__dict(song)
            self.SongStarted(song)

    def __song_ended(self, player, song, skipped):
        if song is not None:
            song = self.__dict(song)
            self.SongEnded(song, skipped)

    @dbus.service.signal('io.github.quodlibet.QuodLibet')
    def SongStarted(self, song):
        pass

    @dbus.service.signal('io.github.quodlibet.QuodLibet')
    def SongEnded(self, song, skipped):
        pass

    @dbus.service.signal('io.github.quodlibet.QuodLibet')
    def Paused(self):
        pass

    @dbus.service.signal('io.github.quodlibet.QuodLibet')
    def Unpaused(self):
        pass

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def GetPosition(self):
        return self._player.get_position()

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def IsPlaying(self):
        return not self._player.paused

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def CurrentSong(self):
        return self.__dict(self._player.song)

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def Next(self):
        self._player.next()

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def Previous(self):
        self._player.previous()

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def Pause(self):
        self._player.paused = True

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def Play(self):
        self._player.play()

    @dbus.service.method('io.github.quodlibet.QuodLibet')
    def PlayPause(self):
        self._player.playpause()
        return self._player.paused

    @dbus.service.method('io.github.quodlibet.QuodLibet', in_signature='s')
    def Query(self, text):
        if text is not None:
            query = Query(text, star=SongList.star)
            if query.is_parsable:
                return [self.__dict(s) for s in itervalues(self.library)
                        if query.search(s)]
        return None
