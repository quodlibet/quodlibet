# -*- coding: utf-8 -*-
# Copyright 2006 Federico Pelloni <federico.pelloni@gmail.com>
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

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
            name = dbus.service.BusName('net.sacredchao.QuodLibet', bus=bus)
            path = '/net/sacredchao/QuodLibet'
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

    @dbus.service.signal('net.sacredchao.QuodLibet')
    def SongStarted(self, song):
        pass

    @dbus.service.signal('net.sacredchao.QuodLibet')
    def SongEnded(self, song, skipped):
        pass

    @dbus.service.signal('net.sacredchao.QuodLibet')
    def Paused(self):
        pass

    @dbus.service.signal('net.sacredchao.QuodLibet')
    def Unpaused(self):
        pass

    @dbus.service.method('net.sacredchao.QuodLibet')
    def GetPosition(self):
        return self._player.get_position()

    @dbus.service.method('net.sacredchao.QuodLibet')
    def IsPlaying(self):
        return not self._player.paused

    @dbus.service.method('net.sacredchao.QuodLibet')
    def CurrentSong(self):
        return self.__dict(self._player.song)

    @dbus.service.method('net.sacredchao.QuodLibet')
    def Next(self):
        self._player.next()

    @dbus.service.method('net.sacredchao.QuodLibet')
    def Previous(self):
        self._player.previous()

    @dbus.service.method('net.sacredchao.QuodLibet')
    def Pause(self):
        self._player.paused = True

    @dbus.service.method('net.sacredchao.QuodLibet')
    def Play(self):
        self._player.play()

    @dbus.service.method('net.sacredchao.QuodLibet')
    def PlayPause(self):
        self._player.playpause()
        return self._player.paused

    @dbus.service.method('net.sacredchao.QuodLibet', in_signature='s')
    def Query(self, query):
        if query is not None:
            try:
                results = Query(query, star=SongList.star).search
            except Query.error:
                pass
            else:
                return [self.__dict(s) for s in itervalues(self.library)
                        if results(s)]
        return None
