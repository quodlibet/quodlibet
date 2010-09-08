# Copyright 2010 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import time

import gtk
import dbus
import dbus.glib

from quodlibet.util.uri import URI
from quodlibet.player import playlist as player
from quodlibet.widgets import main as window
from quodlibet.library import librarian
from plugins.events import EventPlugin

# TODO: OpenUri, UriSchemes, Mimetypes, CanXYZ

class MPRIS(EventPlugin):
    PLUGIN_ID = "mpris"
    PLUGIN_NAME = _("MPRIS D-Bus support")
    PLUGIN_DESC = _("Lets you control Quod Libet using the "
        "MPRIS 2.0 D-Bus Interface Specification.")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.1"

    def enabled(self):
        self.m2 = MPRIS2Object()

    def disabled(self):
        if self.m2:
            self.m2.remove_from_connection()
            self.m2 = None

    def destroy(self):
        self.disabled()

# http://www.mpris.org/2.0/spec/
class MPRIS2Object(dbus.service.Object):

    __path = "/org/mpris/MediaPlayer2"
    __bus_name = "org.mpris.MediaPlayer2.quodlibet"

    __prop_interface = "org.freedesktop.DBus.Properties"

    def __get_playback_status():
        return ("Playing", "Paused")[int(player.paused)]

    def __get_loop_status():
        return ("None", "Playlist")[int(window.repeat.get_active())]

    def __set_loop_status(value):
        window.repeat.set_active(value == "Playlist")

    def __get_shuffle():
        return (window.order.get_active_name() == "shuffle")

    def __set_shuffle(value):
        shuffle_on = window.order.get_active_name() == "shuffle"
        if shuffle_on and not value:
            window.order.set_active("inorder")
        elif not shuffle_on and value:
            window.order.set_active("shuffle")

    def __get_metadata():
        """http://xmms2.org/wiki/MPRIS_Metadata"""
        song = player.info

        metadata = dbus.Dictionary(signature="sv")
        if not song: return metadata

        track_id = MPRIS2Object.__path + "/" + str(id(song))

        metadata["mpris:trackid"] = track_id
        metadata["mpris:length"] = long(player.info.get("~#length", 0) * 1000)
        cover = song.find_cover()
        if cover:
            # This doesn't work for embedded images.. the file gets unlinked
            # after loosing the file handle
            metadata["mpris:artUrl"] = str(URI.frompath(cover.name))

        # All list values
        list_val = {"artist": "artist", "albumArtist": "albumartist",
            "comment": "comment", "composer": "composer", "genre": "genre",
            "lyricist": "lyricist"}
        for xesam, tag in list_val.iteritems():
            vals = song.list(tag)
            if vals:
                metadata["xesam:" + xesam] = vals

        # All single values
        sing_val = {"album": "album"}
        for xesam, tag in sing_val.iteritems():
            vals = song.comma(tag)
            if vals:
                metadata["xesam:" + xesam] = vals

        # URI
        metadata["xesam:url"] = song("~uri")

        # Numbers
        num_val = {"audioBPM ": "bpm", "discNumber": "disc",
            "trackNumber": "track", "useCount": "playcount",
            "userRating": "rating"}

        for xesam, tag in num_val.iteritems():
            val = song("~#" + tag, None)
            if val is not None:
                metadata["xesam:" +  xesam] = val

        # Dates
        ISO_8601_format = "%Y-%m-%dT%H:%M:%S"
        tuple_time = time.gmtime(song("~#lastplayed"))
        iso_time = time.strftime(ISO_8601_format, tuple_time)
        metadata["xesam:lastUsed"] = iso_time

        year = song("~year")
        if year:
            try: tuple_time = time.strptime(year, "%Y")
            except ValueError: pass
            else:
                iso_time = time.strftime(ISO_8601_format, tuple_time)
                metadata["xesam:contentCreated"] = iso_time

        return metadata

    def __get_volume():
        return float(player.volume)

    def __set_volume(value):
        player.volume = max(0, value)

    def __get_position():
        return long(player.get_position()*1000)

    __root_interface = "org.mpris.MediaPlayer2"
    __root_props = {
        "CanQuit": (True, None),
        "CanRaise": (True, None),
        "HasTrackList": (False, None),
        "Identity": ("Quod Libet", None),
        "DesktopEntry": ("quodlibet", None),
        "SupportedUriSchemes": (dbus.Array(signature="s"), None),
        "SupportedMimeTypes": (dbus.Array(signature="s"), None)
    }

    __player_interface = "org.mpris.MediaPlayer2.Player"
    __player_props = {
        "PlaybackStatus": (__get_playback_status, None),
        "LoopStatus": (__get_loop_status, __set_loop_status),
        "Rate": (1.0, None),
        "Shuffle": (__get_shuffle, __set_shuffle),
        "Metadata": (__get_metadata, None),
        "Volume": (__get_volume, __set_volume),
        "Position": (__get_position, None),
        "MinimumRate": (1.0, None),
        "MaximumRate": (1.0, None),
        "CanGoNext": (True, None), # Pretend we can do everything for now
        "CanGoPrevious": (True, None),
        "CanPlay": (True, None),
        "CanPause": (True, None),
        "CanSeek": (True, None),
        "CanControl": (True, None),
    }

    __prop_mapping = {
        __player_interface: __player_props,
        __root_interface: __root_props}

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.__bus_name, bus)
        super(MPRIS2Object, self).__init__(name, self.__path)

        self.__psigs = [
            player.connect("seek", self.__seeked),
            player.connect_object("paused", self.__update_property,
                self.__player_interface, "PlaybackStatus"),
            player.connect_object("unpaused", self.__update_property,
                self.__player_interface, "PlaybackStatus"),
            player.connect_object("song-ended", self.__update_song_ended,
                self.__player_interface, "Metadata"),
            player.connect_object("song-started", self.__update_song_started,
                self.__player_interface, "Metadata"),
            ]

        self.__rsigs = [
            window.repeat.connect_object("toggled", self.__update_property,
                self.__player_interface, "LoopStatus"),
            ]

        self.__ssigs = [
            window.order.connect_object("changed", self.__update_property,
                self.__player_interface, "Shuffle"),
            ]

        self.__lsigs = [
            librarian.connect_object("changed", self.__update_metadata_changed,
                self.__player_interface, "Metadata"),
            ]

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS2Object, self).remove_from_connection(*arg, **kwargs)
        for sig in self.__psigs:
            player.disconnect(sig)
        for sig in self.__rsigs:
            window.repeat.disconnect(sig)
        for sig in self.__ssigs:
            window.order.disconnect(sig)
        for sig in self.__lsigs:
            librarian.disconnect(sig)

    def __update_song_started(self, interface, song, prop):
        self.__update_property(interface, prop, invalid=True)

    def __update_song_ended(self, interface, song, stopped, prop):
        self.__update_property(interface, prop, invalid=True)

    def __update_metadata_changed(self, interface, song, prop):
        if song is player.info:
            self.__update_property(interface, prop, invalid=True)

    def __update_property(self, interface, prop, invalid=False):
        if invalid:
            self.PropertiesChanged(interface, {}, [prop])
        else:
            getter, setter = self.__prop_mapping[interface][prop]
            if callable(getter): val = getter()
            else: val = getter
            self.PropertiesChanged(interface, {prop: val}, [])

    def __seeked(self, player, song, ms):
        self.Seeked(long(ms * 1000))

    @dbus.service.method(__root_interface)
    def Raise(self):
        from quodlibet.widgets import main as window
        window.show()
        window.present()

    @dbus.service.method(__root_interface)
    def Quit(self):
        from quodlibet.widgets import main as window
        window.destroy()

    @dbus.service.method(__player_interface)
    def Next(self):
        paused = player.paused
        player.next()
        player.paused = paused

    @dbus.service.method(__player_interface)
    def Previous(self):
        paused = player.paused
        player.previous()
        player.paused = paused

    @dbus.service.method(__player_interface)
    def Pause(self):
        player.paused = True

    @dbus.service.method(__player_interface)
    def Play(self):
        if player.song is None:
            player.reset()
        else:
            player.paused = False

    @dbus.service.method(__player_interface)
    def PlayPause(self):
        if player.song is None:
            player.reset()
        else:
            player.paused ^= True

    @dbus.service.method(__player_interface)
    def Stop(self):
        player.stop()

    @dbus.service.method(__player_interface, in_signature="x")
    def Seek(self, offset):
        new_pos = player.get_position() + offset/1000
        player.seek(new_pos)

    @dbus.service.method(__player_interface, in_signature="ox")
    def SetPosition(self, track_id, position):
        current_track_id = self.__path + "/" + str(id(player.info))
        if track_id != current_track_id: return
        player.seek(position/1000)

    @dbus.service.method(__player_interface, in_signature="s")
    def OpenUri(self, uri):
        pass

    @dbus.service.method(dbus_interface=__prop_interface,
        in_signature="ss", out_signature="v")
    def Get(self, interface, prop):
        getter, setter = self.__prop_mapping[interface][prop]
        if callable(getter):
            return getter()
        return getter

    @dbus.service.method(dbus_interface=__prop_interface,
        in_signature="ssv", out_signature="")
    def Set(self, interface, prop, value):
        getter, setter = self.__prop_mapping[interface][prop]
        if setter is not None:
            setter(value)

    @dbus.service.method(dbus_interface=__prop_interface,
        in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        read_props = {}
        props = self.__prop_mapping[interface]
        for key, (getter, setter) in props.iteritems():
            read_props[key] = (callable(getter) and getter()) or getter
        return read_props

    @dbus.service.signal(__player_interface, signature="x")
    def Seeked(self, position):
        pass

    @dbus.service.signal(__prop_interface, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed_properties,
        invalidated_properties):
        pass
