# -*- coding: utf-8 -*-
# Copyright 2010,2012 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import tempfile

import dbus
import dbus.service
from senf import fsn2uri

from quodlibet import app
from quodlibet.util.dbusutils import DBusIntrospectable, DBusProperty
from quodlibet.util.dbusutils import dbus_unicode_validate as unival
from quodlibet.compat import iteritems, listmap

from .util import MPRISObject

# TODO: OpenUri, CanXYZ
# Date parsing (util?)


# http://www.mpris.org/2.0/spec/
class MPRIS2(DBusProperty, DBusIntrospectable, MPRISObject):

    BUS_NAME = "org.mpris.MediaPlayer2.quodlibet"
    PATH = "/org/mpris/MediaPlayer2"

    ROOT_IFACE = "org.mpris.MediaPlayer2"

    ROOT_ISPEC = """
<method name="Raise"/>
<method name="Quit"/>"""

    ROOT_PROPS = """
<property name="CanQuit" type="b" access="read"/>
<property name="CanRaise" type="b" access="read"/>
<property name="CanSetFullscreen" type="b" access="read"/>
<property name="HasTrackList" type="b" access="read"/>
<property name="Identity" type="s" access="read"/>
<property name="DesktopEntry" type="s" access="read"/>
<property name="SupportedUriSchemes" type="as" access="read"/>
<property name="SupportedMimeTypes" type="as" access="read"/>"""

    PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"

    PLAYER_ISPEC = """
<method name="Next"/>
<method name="Previous"/>
<method name="Pause"/>
<method name="PlayPause"/>
<method name="Stop"/>
<method name="Play"/>
<method name="Seek">
  <arg direction="in" name="Offset" type="x"/>
</method>
<method name="SetPosition">
  <arg direction="in" name="TrackId" type="o"/>
  <arg direction="in" name="Position" type="x"/>
</method>
<method name="OpenUri">
  <arg direction="in" name="Uri" type="s"/>
</method>
<signal name="Seeked">
  <arg name="Position" type="x"/>
</signal>"""

    PLAYER_PROPS = """
<property name="PlaybackStatus" type="s" access="read"/>
<property name="LoopStatus" type="s" access="readwrite"/>
<property name="Rate" type="d" access="readwrite"/>
<property name="Shuffle" type="b" access="readwrite"/>
<property name="Metadata" type="a{sv}" access="read"/>
<property name="Volume" type="d" access="readwrite"/>
<property name="Position" type="x" access="read">
  <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" \
value="false"/>
</property>
<property name="MinimumRate" type="d" access="read"/>
<property name="MaximumRate" type="d" access="read"/>
<property name="CanGoNext" type="b" access="read"/>
<property name="CanGoPrevious" type="b" access="read"/>
<property name="CanPlay" type="b" access="read"/>
<property name="CanPause" type="b" access="read"/>
<property name="CanSeek" type="b" access="read"/>
<property name="CanControl" type="b" access="read">
  <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" \
value="false"/>
</property>"""

    def __init__(self):
        DBusIntrospectable.__init__(self)
        DBusProperty.__init__(self)

        self.set_introspection(MPRIS2.ROOT_IFACE, MPRIS2.ROOT_ISPEC)
        self.set_properties(MPRIS2.ROOT_IFACE, MPRIS2.ROOT_PROPS)

        self.set_introspection(MPRIS2.PLAYER_IFACE, MPRIS2.PLAYER_ISPEC)
        self.set_properties(MPRIS2.PLAYER_IFACE, MPRIS2.PLAYER_PROPS)

        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        MPRISObject.__init__(self, bus, self.PATH, name)

        self.__metadata = None
        self.__cover = None
        player_options = app.player_options
        self.__repeat_id = player_options.connect(
            "notify::repeat", self.__repeat_changed)
        self.__random_id = player_options.connect(
            "notify::shuffle", self.__shuffle_changed)
        self.__single_id = player_options.connect(
            "notify::single", self.__single_changed)

        self.__lsig = app.librarian.connect("changed", self.__library_changed)
        self.__vsig = app.player.connect("notify::volume",
                                         self.__volume_changed)
        self.__seek_sig = app.player.connect("seek", self.__seeked)

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS2, self).remove_from_connection(*arg, **kwargs)

        player_options = app.player_options
        player_options.disconnect(self.__repeat_id)
        player_options.disconnect(self.__random_id)
        player_options.disconnect(self.__single_id)
        app.librarian.disconnect(self.__lsig)
        app.player.disconnect(self.__vsig)
        app.player.disconnect(self.__seek_sig)

        if self.__cover is not None:
            self.__cover.close()
            self.__cover = None
        self.__invalidate_metadata()

    def __volume_changed(self, *args):
        self.emit_properties_changed(self.PLAYER_IFACE, ["Volume"])

    def __repeat_changed(self, *args):
        self.emit_properties_changed(self.PLAYER_IFACE, ["LoopStatus"])

    def __shuffle_changed(self, *args):
        self.emit_properties_changed(self.PLAYER_IFACE, ["Shuffle"])

    def __single_changed(self, *args):
        self.emit_properties_changed(self.PLAYER_IFACE, ["LoopStatus"])

    def __seeked(self, player, song, ms):
        self.Seeked(ms * 1000)

    def __library_changed(self, library, songs):
        self.__invalidate_metadata()
        if not songs or app.player.info not in songs:
            return
        self.emit_properties_changed(self.PLAYER_IFACE, ["Metadata"])

    @dbus.service.method(ROOT_IFACE)
    def Raise(self):
        app.present()

    @dbus.service.method(ROOT_IFACE)
    def Quit(self):
        app.quit()

    @dbus.service.signal(PLAYER_IFACE, signature="x")
    def Seeked(self, position):
        pass

    @dbus.service.method(PLAYER_IFACE)
    def Next(self):
        player = app.player
        paused = player.paused
        player.next()
        player.paused = paused

    @dbus.service.method(PLAYER_IFACE)
    def Previous(self):
        player = app.player
        paused = player.paused
        player.previous()
        player.paused = paused

    @dbus.service.method(PLAYER_IFACE)
    def Pause(self):
        app.player.paused = True

    @dbus.service.method(PLAYER_IFACE)
    def Play(self):
        app.player.play()

    @dbus.service.method(PLAYER_IFACE)
    def PlayPause(self):
        app.player.playpause()

    @dbus.service.method(PLAYER_IFACE)
    def Stop(self):
        app.player.stop()

    @dbus.service.method(PLAYER_IFACE, in_signature="x")
    def Seek(self, offset):
        new_pos = app.player.get_position() + offset / 1000
        app.player.seek(new_pos)

    @dbus.service.method(PLAYER_IFACE, in_signature="ox")
    def SetPosition(self, track_id, position):
        if track_id == self.__get_current_track_id():
            app.player.seek(position / 1000)

    def paused(self):
        self.emit_properties_changed(self.PLAYER_IFACE, ["PlaybackStatus"])
    unpaused = paused

    def song_started(self, song):
        self.__invalidate_metadata()

        # so the position in clients gets updated faster
        self.Seeked(0)

        self.emit_properties_changed(self.PLAYER_IFACE,
                                    ["PlaybackStatus", "Metadata"])

    def __get_current_track_id(self):
        path = "/net/sacredchao/QuodLibet"
        if not app.player.info:
            return dbus.ObjectPath(path + "/" + "NoTrack")
        return dbus.ObjectPath(path + "/" + str(id(app.player.info)))

    def __invalidate_metadata(self):
        self.__metadata = None

    def __get_metadata(self):
        if self.__metadata is None:
            self.__metadata = self.__get_metadata_real()
            assert self.__metadata is not None
        return self.__metadata

    def __get_metadata_real(self):
        """
        https://www.freedesktop.org/wiki/Specifications/mpris-spec/metadata/
        """

        metadata = {}
        metadata["mpris:trackid"] = self.__get_current_track_id()

        def ignore_overflow(dbus_type, value):
            try:
                return dbus_type(value)
            except OverflowError:
                return 0

        song = app.player.info
        if not song:
            return metadata

        metadata["mpris:length"] = ignore_overflow(
            dbus.Int64, song("~#length") * 10 ** 6)

        if self.__cover is not None:
            self.__cover.close()
            self.__cover = None

        cover = app.cover_manager.get_cover(song)
        if cover:
            is_temp = cover.name.startswith(tempfile.gettempdir())
            if is_temp:
                self.__cover = cover
            metadata["mpris:artUrl"] = fsn2uri(cover.name)

        # All list values
        list_val = {"artist": "artist", "albumArtist": "albumartist",
            "comment": "comment", "composer": "composer", "genre": "genre",
            "lyricist": "lyricist"}
        for xesam, tag in iteritems(list_val):
            vals = song.list(tag)
            if vals:
                metadata["xesam:" + xesam] = listmap(unival, vals)

        # All single values
        sing_val = {"album": "album", "title": "title", "asText": "~lyrics"}
        for xesam, tag in iteritems(sing_val):
            vals = song.comma(tag)
            if vals:
                metadata["xesam:" + xesam] = unival(vals)

        # URI
        metadata["xesam:url"] = song("~uri")

        # Integers
        num_val = {"audioBPM": "bpm", "discNumber": "disc",
                   "trackNumber": "track", "useCount": "playcount"}

        for xesam, tag in iteritems(num_val):
            val = song("~#" + tag, None)
            if val is not None:
                metadata["xesam:" + xesam] = ignore_overflow(dbus.Int32, val)

        # Rating
        metadata["xesam:userRating"] = ignore_overflow(
            dbus.Double, song("~#rating"))

        # Dates
        ISO_8601_format = "%Y-%m-%dT%H:%M:%S"
        tuple_time = time.gmtime(song("~#lastplayed"))
        iso_time = time.strftime(ISO_8601_format, tuple_time)
        metadata["xesam:lastUsed"] = iso_time

        year = song("~year")
        if year:
            try:
                tuple_time = time.strptime(year, "%Y")
                iso_time = time.strftime(ISO_8601_format, tuple_time)
            except ValueError:
                pass
            else:
                metadata["xesam:contentCreated"] = iso_time

        return metadata

    def set_property(self, interface, name, value):
        player = app.player
        player_options = app.player_options

        if interface == self.PLAYER_IFACE:
            if name == "LoopStatus":
                if value == "Playlist":
                    player_options.repeat = True
                    player_options.single = False
                elif value == "Track":
                    player_options.repeat = True
                    player_options.single = True
                elif value == "None":
                    player_options.repeat = False
                    player_options.single = False
            elif name == "Rate":
                pass
            elif name == "Shuffle":
                player_options.shuffle = value
            elif name == "Volume":
                player.volume = value

    def get_property(self, interface, name):
        player = app.player
        player_options = app.player_options

        if interface == self.ROOT_IFACE:
            if name == "CanQuit":
                return True
            elif name == "CanRaise":
                return True
            elif name == "CanSetFullscreen":
                return False
            elif name == "HasTrackList":
                return False
            elif name == "Identity":
                return app.name
            elif name == "DesktopEntry":
                return "io.github.quodlibet.QuodLibet"
            elif name == "SupportedUriSchemes":
                # TODO: enable once OpenUri is done
                can = lambda s: False
                #can = lambda s: app.player.can_play_uri("%s://fake" % s)
                schemes = ["http", "https", "ftp", "file", "mms"]
                return filter(can, schemes)
            elif name == "SupportedMimeTypes":
                from quodlibet import formats
                return formats.mimes
        elif interface == self.PLAYER_IFACE:
            if name == "PlaybackStatus":
                if not player.song:
                    return "Stopped"
                return ("Playing", "Paused")[int(player.paused)]
            elif name == "LoopStatus":
                if not player_options.repeat:
                    return "None"
                else:
                    if player_options.single:
                        return "Track"
                    return "Playlist"
            elif name == "Rate":
                return 1.0
            elif name == "Shuffle":
                return player_options.shuffle
            elif name == "Metadata":
                return self.__get_metadata()
            elif name == "Volume":
                return player.volume
            elif name == "Position":
                return player.get_position() * 1000
            elif name == "MinimumRate":
                return 1.0
            elif name == "MaximumRate":
                return 1.0
            elif name == "CanGoNext":
                return True
            elif name == "CanGoPrevious":
                return True
            elif name == "CanPlay":
                return True
            elif name == "CanPause":
                return True
            elif name == "CanSeek":
                return True
            elif name == "CanControl":
                return True
