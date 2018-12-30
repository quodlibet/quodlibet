# Copyright 2006 Federico Pelloni <federico.pelloni@gmail.com>
#           2013 Christoph Reiter
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GLib
from gi.repository import Gio

from quodlibet.util import dbusutils
from quodlibet.query import Query
from quodlibet.qltk.songlist import SongList
from quodlibet.formats import decode_value


class DBusHandler:
    """
    <!DOCTYPE node PUBLIC
      "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
      "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
    <node name="/net/sacredchao/QuodLibet">
      <interface name="org.freedesktop.DBus.Introspectable">
        <method name="Introspect">
          <arg direction="out" type="s" />
        </method>
      </interface>
      <interface name="net.sacredchao.QuodLibet">
        <signal name="SongStarted">
          <arg type="v" name="song" />
        </signal>
        <signal name="SongEnded">
          <arg type="v" name="song" />
          <arg type="v" name="skipped" />
        </signal>
        <signal name="Paused"></signal>
        <signal name="Unpaused"></signal>
        <method name="GetPosition">
          <arg direction="out" type="u" />
        </method>
        <method name="IsPlaying">
          <arg direction="out" type="b" />
        </method>
        <method name="CurrentSong">
          <arg direction="out" type="a{ss}" />
        </method>
        <method name="Next"></method>
        <method name="Previous"></method>
        <method name="Pause"></method>
        <method name="Play"></method>
        <method name="PlayPause">
          <arg direction="out" type="b" />
        </method>
        <method name="Query">
          <arg direction="in"  type="s" name="text" />
          <arg direction="out" type="aa{ss}" />
        </method>
      </interface>
    </node>
    """

    BUS_NAME = 'net.sacredchao.QuodLibet'
    PATH = '/net/sacredchao/QuodLibet'

    def __init__(self, player, library):
        try:
            self._registered_ids = []
            self._method_outargs = {}
            self.library = library
            self.conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            Gio.bus_own_name_on_connection(self.conn, self.BUS_NAME,
                                           Gio.BusNameOwnerFlags.NONE,
                                           None, self.__on_name_lost)
            self.__register_ifaces()
        except GLib.Error:
            pass
        else:
            player.connect('song-started', self.__song_started)
            player.connect('song-ended', self.__song_ended)
            player.connect('paused', lambda player: self.Paused())
            player.connect('unpaused', lambda player: self.Unpaused())
            self._player = player

    def __on_name_lost(self, connection, name):
        for _id in self._registered_ids:
            connection.unregister_object(_id)

    def __register_ifaces(self):
        info = Gio.DBusNodeInfo.new_for_xml(self.__doc__)
        for interface in info.interfaces:
            for method in interface.methods:
                self._method_outargs[method.name] = '({})'.format(
                    ''.join([arg.signature for arg in method.out_args]))

            _id = self.conn.register_object(
                object_path=self.PATH,
                interface_info=interface,
                method_call_closure=self.__on_method_call)
            self._registered_ids.append(_id)

    def __on_method_call(self, connection, sender, object_path, interface_name,
                         method_name, parameters, invocation):
        args = list(parameters.unpack())
        result = getattr(self, method_name)(*args)
        if not isinstance(result, tuple):
            result = (result,)

        out_args = self._method_outargs[method_name]
        if out_args != '()':
            variant = GLib.Variant(out_args, result)
            invocation.return_value(variant)
        else:
            invocation.return_value(None)

    @staticmethod
    def __dict(song):
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

    def Introspect(self):
        return self.__doc__

    def SongStarted(self, song):
        self.conn.emit_signal(None, self.PATH, 'net.sacredchao.QuodLibet',
                              'SongStarted', GLib.Variant('(a{ss})', (song,)))

    def SongEnded(self, song, skipped):
        self.conn.emit_signal(None, self.PATH, 'net.sacredchao.QuodLibet',
                              'SongEnded', GLib.Variant('(a{ss}b)',
                                                        (song, skipped)))

    def Paused(self):
        self.conn.emit_signal(None, self.PATH, 'net.sacredchao.QuodLibet',
                              'Paused', None)

    def Unpaused(self):
        self.conn.emit_signal(None, self.PATH, 'net.sacredchao.QuodLibet',
                              'Unpaused', None)

    def GetPosition(self):
        return self._player.get_position()

    def IsPlaying(self):
        return not self._player.paused

    def CurrentSong(self):
        return self.__dict(self._player.song)

    def Next(self):
        self._player.next()

    def Previous(self):
        self._player.previous()

    def Pause(self):
        self._player.paused = True

    def Play(self):
        self._player.play()

    def PlayPause(self):
        self._player.playpause()
        return self._player.paused

    def Query(self, text):
        if text is not None:
            query = Query(text, star=SongList.star)
            if query.is_parsable:
                return [self.__dict(s) for s in self.library.values()
                        if query.search(s)]
        return None
