# Copyright 2010 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import time

import gtk
import dbus
import dbus.glib

from quodlibet import util
from quodlibet.util.uri import URI
from quodlibet.player import playlist as player
from quodlibet.widgets import main as window
from quodlibet.library import librarian
from quodlibet.plugins.events import EventPlugin

# TODO: OpenUri, UriSchemes, Mimetypes, CanXYZ
# Date parsing (util?)

# python dbus bindings don't include annotations and properties
MPRIS2_INTROSPECTION = \
"""<node name="/org/mpris/MediaPlayer2">
  <interface name="org.freedesktop.DBus.Introspectable">
    <method name="Introspect">
      <arg direction="out" name="xml_data" type="s"/>
    </method>
  </interface>
  <interface name="org.freedesktop.DBus.Properties">
    <method name="Get">
      <arg direction="in" name="interface_name" type="s"/>
      <arg direction="in" name="property_name" type="s"/>
      <arg direction="out" name="value" type="v"/>
    </method>
    <method name="GetAll">
      <arg direction="in" name="interface_name" type="s"/>
      <arg direction="out" name="properties" type="a{sv}"/>
    </method>
    <method name="Set">
      <arg direction="in" name="interface_name" type="s"/>
      <arg direction="in" name="property_name" type="s"/>
      <arg direction="in" name="value" type="v"/>
    </method>
    <signal name="PropertiesChanged">
      <arg name="interface_name" type="s"/>
      <arg name="changed_properties" type="a{sv}"/>
      <arg name="invalidated_properties" type="as"/>
    </signal>
  </interface>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
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
    </signal>
    <property name="PlaybackStatus" type="s" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="LoopStatus" type="s" access="readwrite">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="Rate" type="d" access="readwrite">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="Shuffle" type="b" access="readwrite">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="Metadata" type="a{sv}" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="Volume" type="d" access="readwrite">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
    </property>
    <property name="Position" type="x" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
    </property>
    <property name="MinimumRate" type="d" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="MaximumRate" type="d" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="CanGoNext" type="b" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="CanGoPrevious" type="b" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="CanPlay" type="b" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="CanPause" type="b" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="CanSeek" type="b" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
    </property>
    <property name="CanControl" type="b" access="read">
      <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
    </property>
  </interface>
</node>"""

class MPRIS(EventPlugin):
    PLUGIN_ID = "mpris"
    PLUGIN_NAME = _("MPRIS D-Bus support")
    PLUGIN_DESC = _("Lets you control Quod Libet using the "
        "MPRIS 1.0/2.0 D-Bus Interface Specification.")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.2"

    def enabled(self):
        self.objects = [MPRIS1RootObject(), MPRIS1DummyTracklistObject(),
            MPRIS1PlayerObject(), MPRIS2Object()]

    def disabled(self):
        for obj in self.objects:
            obj.remove_from_connection()
        self.objects = []

    def plugin_on_paused(self):
        for obj in self.objects:
            obj.paused()

    def plugin_on_unpaused(self):
        for obj in self.objects:
            obj.unpaused()

    def plugin_on_song_started(self, song):
        for obj in self.objects:
            obj.song_started(song)

    def plugin_on_song_ended(self, song, skipped):
        for obj in self.objects:
            obj.song_ended(song, skipped)

class MPRISObject(dbus.service.Object):
    def paused(self): pass
    def unpaused(self): pass
    def song_started(self, song): pass
    def song_ended(self, song, skipped): pass

# http://xmms2.org/wiki/MPRIS
class MPRIS1RootObject(MPRISObject):
    __path = "/"

    __bus_name = "org.mpris.quodlibet"
    __interface = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.__bus_name, bus)
        super(MPRIS1RootObject, self).__init__(name, self.__path)

    @dbus.service.method(dbus_interface=__interface, out_signature="s")
    def Identity(self):
        return "Quod Libet"

    @dbus.service.method(dbus_interface=__interface)
    def Quit(self):
        window.destroy()

    @dbus.service.method(dbus_interface=__interface, out_signature="(qq)")
    def MprisVersion(self):
        return (1, 0)

class MPRIS1DummyTracklistObject(MPRISObject):
    __path = "/TrackList"

    __bus_name = "org.mpris.quodlibet"
    __interface = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.__bus_name, bus)
        super(MPRIS1DummyTracklistObject, self).__init__(name, self.__path)

    @dbus.service.method(dbus_interface=__interface, in_signature="i",
        out_signature="a{sv}")
    def GetMetadata(self, position):
        song = player.info
        if position != 0:
            song = None
        return MPRIS1PlayerObject._get_metadata(song)

    @dbus.service.method(dbus_interface=__interface, out_signature="i")
    def GetCurrentTrack(self):
        return 0

    @dbus.service.method(dbus_interface=__interface, out_signature="i")
    def GetLength(self):
        return 0

    @dbus.service.method(dbus_interface=__interface, in_signature="sb",
        out_signature="i")
    def AddTrack(self, uri, play):
        return -1

    @dbus.service.method(dbus_interface=__interface, in_signature="b")
    def SetLoop(self, loop):
        window.repeat.set_active(loop)

    @dbus.service.method(dbus_interface=__interface, in_signature="b")
    def SetRandom(self, shuffle):
        shuffle_on = window.order.get_active_name() == "shuffle"
        if shuffle_on and not shuffle:
            window.order.set_active("inorder")
        elif not shuffle_on and shuffle:
            window.order.set_active("shuffle")

class MPRIS1PlayerObject(MPRISObject):
    __path = "/Player"

    __bus_name = "org.mpris.quodlibet"
    __interface = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.__bus_name, bus)
        super(MPRIS1PlayerObject, self).__init__(name, self.__path)

        self.__rsig = window.repeat.connect("toggled", self.__update_status)
        self.__ssig = window.order.connect("changed", self.__update_status)
        self.__lsig = librarian.connect("changed", self.__update_track_changed)

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS1PlayerObject, self).remove_from_connection(*arg, **kwargs)

        window.repeat.disconnect(self.__rsig)
        window.order.disconnect(self.__ssig)
        librarian.disconnect(self.__lsig)

    def paused(self):
        self.StatusChange(self.__get_status())
    unpaused = paused

    def song_started(self, song):
        self.TrackChanged(self._get_metadata(song))

    def __update_track_changed(self, library, songs):
        if player.info in songs:
             self.TrackChanged(self._get_metadata(player.info))

    def __update_status(self, *args):
        self.StatusChange(self.__get_status())

    @staticmethod
    def _get_metadata(song):
        #http://xmms2.org/wiki/MPRIS_Metadata#MPRIS_v1.0_Metadata_guidelines
        metadata = dbus.Dictionary(signature="sv")
        if not song: return metadata

        # Missing: "audio-samplerate", "video-bitrate"

        strings = {"location": "~uri", "title": "title", "artist": "artist",
            "album": "album", "tracknumber": "tracknumber", "genre": "genre",
            "comment": "comment", "asin": "asin",
            "puid fingerprint": "musicip_puid",
            "mb track id": "musicbrainz_trackid",
            "mb artist id": "musicbrainz_artistid",
            "mb artist sort name": "artistsort",
            "mb album id": "musicbrainz_albumid", "mb release date": "date",
            "mb album artist": "albumartist",
            "mb album artist id": "musicbrainz_albumartistid",
            "mb album artist sort name": "albumartistsort",
            }

        for key, tag in strings.iteritems():
            val = song.comma(tag)
            if val:
                metadata[key] = val

        metadata["audio-bitrate"] = song("~#bitrate", 0) * 1024
        metadata["rating"] = int(round(song("~#rating") * 5))
        metadata["year"] = song("~#year", 0)
        metadata["time"] = song("~#length", 0)
        metadata["mtime"] = song("~#length", 0) * 1000

        year = song("~year")
        if year:
            try: tuple_time = time.strptime(year, "%Y")
            except ValueError: pass
            else:
                try: metadata["date"] = int(time.mktime(tuple_time))
                except ValueError: pass

        return metadata

    def __get_status(self):
        play = (not player.info and 2) or int(player.paused)
        shuffle = (window.order.get_active_name() != "inorder")
        repeat_one = (window.order.get_active_name() == "onesong" and \
            window.repeat.get_active())
        repeat_all = int(window.repeat.get_active())

        return (play, shuffle, repeat_one, repeat_all)

    @dbus.service.method(dbus_interface=__interface)
    def Next(self):
        player.next()

    @dbus.service.method(dbus_interface=__interface)
    def Prev(self):
        player.previous()

    @dbus.service.method(dbus_interface=__interface)
    def Pause(self):
        if player.song is None:
            player.reset()
        else:
            player.paused ^= True

    @dbus.service.method(dbus_interface=__interface)
    def Stop(self):
        player.stop()

    @dbus.service.method(dbus_interface=__interface)
    def Play(self):
        if player.song is None:
            player.reset()
        else:
            if player.paused:
                player.paused = False
            else:
                player.seek(0)

    @dbus.service.method(dbus_interface=__interface)
    def Repeat(self):
        pass

    @dbus.service.method(dbus_interface=__interface, out_signature="(iiii)")
    def GetStatus(self):
        return self.__get_status()

    @dbus.service.method(dbus_interface=__interface, out_signature="a{sv}")
    def GetMetadata(self):
        return self._get_metadata(player.info)

    @dbus.service.method(dbus_interface=__interface, out_signature="i")
    def GetCaps(self):
        # everything except Tracklist
        return (1 | 1 << 1 | 1 << 2 | 1 << 3 | 1 << 4 | 1 << 5)

    @dbus.service.method(dbus_interface=__interface, in_signature="i")
    def VolumeSet(self, volume):
        player.volume = volume / 100.0

    @dbus.service.method(dbus_interface=__interface, out_signature="i")
    def VolumeGet(self):
        return int(round(player.volume * 100))

    @dbus.service.method(dbus_interface=__interface, in_signature="i")
    def PositionSet(self, position):
        player.seek(position)

    @dbus.service.method(dbus_interface=__interface, out_signature="i")
    def PositionGet(self):
        return int(player.get_position())

    @dbus.service.signal(__interface, signature="a{sv}")
    def TrackChanged(self, metadata):
        pass

    @dbus.service.signal(__interface, signature="(iiii)")
    def StatusChange(self, status):
        pass

    @dbus.service.signal(__interface, signature="i")
    def CapsChange(self, status):
        pass

# http://www.mpris.org/2.0/spec/
class MPRIS2Object(MPRISObject):

    __path = "/org/mpris/MediaPlayer2"
    __bus_name = "org.mpris.MediaPlayer2.quodlibet"

    __prop_interface = "org.freedesktop.DBus.Properties"
    __introspect_interface = "org.freedesktop.DBus.Introspectable"

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
        metadata["mpris:trackid"] = MPRIS2Object.__path + "/"
        if not song: return metadata

        metadata["mpris:trackid"] += str(id(song))
        metadata["mpris:length"] = long(player.info.get("~#length", 0) * 1000)
        cover = song.find_cover()
        if cover:
            name = cover.name
            if isinstance(name, str):
                name = util.fsdecode(name)
            # This doesn't work for embedded images.. the file gets unlinked
            # after loosing the file handle
            metadata["mpris:artUrl"] = str(URI.frompath(name))

        # All list values
        list_val = {"artist": "artist", "albumArtist": "albumartist",
            "comment": "comment", "composer": "composer", "genre": "genre",
            "lyricist": "lyricist"}
        for xesam, tag in list_val.iteritems():
            vals = song.list(tag)
            if vals:
                metadata["xesam:" + xesam] = vals

        # All single values
        sing_val = {"album": "album", "title": "title", "asText": "~lyrics"}
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
                try: iso_time = time.strftime(ISO_8601_format, tuple_time)
                except ValueError: pass
                else:
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

        self.__rsig = window.repeat.connect_object(
            "toggled", self.__update_property,
            self.__player_interface, "LoopStatus")

        self.__ssig = window.order.connect_object(
            "changed", self.__update_property,
            self.__player_interface, "Shuffle")

        self.__lsig = librarian.connect_object(
            "changed", self.__update_metadata_changed,
            self.__player_interface, "Metadata")

    def paused(self):
        self.__update_property(self.__player_interface, "PlaybackStatus")
    unpaused = paused

    def song_started(self, song):
        self.__update_property(
            self.__player_interface, "Metadata")

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS2Object, self).remove_from_connection(*arg, **kwargs)

        window.repeat.disconnect(self.__rsig)
        window.order.disconnect(self.__ssig)
        librarian.disconnect(self.__lsig)

    def __update_metadata_changed(self, interface, song, prop):
        if song is player.info:
            self.__update_property(interface, prop)

    def __update_property(self, interface, prop):
        getter, setter = self.__prop_mapping[interface][prop]
        if callable(getter): val = getter()
        else: val = getter
        self.PropertiesChanged(interface, {prop: val}, [])

    def __seeked(self, player, song, ms):
        self.Seeked(long(ms * 1000))

    @dbus.service.method(__introspect_interface)
    def Introspect(self):
        return MPRIS2_INTROSPECTION

    @dbus.service.method(__root_interface)
    def Raise(self):
        window.show()
        window.present()

    @dbus.service.method(__root_interface)
    def Quit(self):
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
            if callable(getter): getter = getter()
            read_props[key] = getter
        return read_props

    @dbus.service.signal(__player_interface, signature="x")
    def Seeked(self, position):
        pass

    @dbus.service.signal(__prop_interface, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed_properties,
        invalidated_properties):
        pass
