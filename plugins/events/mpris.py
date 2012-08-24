# Copyright 2010,2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import time
import tempfile

import gtk
import dbus
import dbus.service
import dbus.glib

from quodlibet import util
from quodlibet.util.uri import URI
from quodlibet.util.dbusutils import DBusIntrospectable, DBusProperty
from quodlibet.player import playlist as player
from quodlibet.widgets import main as window
from quodlibet.library import librarian
from quodlibet.plugins.events import EventPlugin


# TODO: OpenUri, CanXYZ
# Date parsing (util?)

class MPRIS(EventPlugin):
    PLUGIN_ID = "mpris"
    PLUGIN_NAME = _("MPRIS D-Bus support")
    PLUGIN_DESC = _("Lets you control Quod Libet using the "
        "MPRIS 1.0/2.0 D-Bus Interface Specification.")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.2"

    def enabled(self):
        self.objects = [MPRIS1Root(), MPRIS1DummyTracklist(),
                        MPRIS1Player(), MPRIS2()]

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
    def paused(self):
        pass

    def unpaused(self):
        pass

    def song_started(self, song):
        pass

    def song_ended(self, song, skipped):
        pass


# http://xmms2.org/wiki/MPRIS
class MPRIS1Root(MPRISObject):
    PATH = "/"
    BUS_NAME = "org.mpris.quodlibet"
    IFACE = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        super(MPRIS1Root, self).__init__(name, self.PATH)

    @dbus.service.method(IFACE, out_signature="s")
    def Identity(self):
        return "Quod Libet"

    @dbus.service.method(IFACE)
    def Quit(self):
        window.destroy()

    @dbus.service.method(IFACE, out_signature="(qq)")
    def MprisVersion(self):
        return (1, 0)


class MPRIS1DummyTracklist(MPRISObject):
    PATH = "/TrackList"
    BUS_NAME = "org.mpris.quodlibet"
    IFACE = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        super(MPRIS1DummyTracklist, self).__init__(name, self.PATH)

    @dbus.service.method(IFACE, in_signature="i", out_signature="a{sv}")
    def GetMetadata(self, position):
        song = player.info
        if position != 0:
            song = None
        return MPRIS1Player._get_metadata(song)

    @dbus.service.method(IFACE, out_signature="i")
    def GetCurrentTrack(self):
        return 0

    @dbus.service.method(IFACE, out_signature="i")
    def GetLength(self):
        return 0

    @dbus.service.method(IFACE, in_signature="sb",
        out_signature="i")
    def AddTrack(self, uri, play):
        return -1

    @dbus.service.method(IFACE, in_signature="b")
    def SetLoop(self, loop):
        window.repeat.set_active(loop)

    @dbus.service.method(IFACE, in_signature="b")
    def SetRandom(self, shuffle):
        shuffle_on = window.order.get_active_name() == "shuffle"
        if shuffle_on and not shuffle:
            window.order.set_active("inorder")
        elif not shuffle_on and shuffle:
            window.order.set_active("shuffle")


class MPRIS1Player(MPRISObject):
    PATH = "/Player"
    BUS_NAME = "org.mpris.quodlibet"
    IFACE = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        super(MPRIS1Player, self).__init__(name, self.PATH)

        self.__rsig = window.repeat.connect("toggled", self.__update_status)
        self.__ssig = window.order.connect("changed", self.__update_status)
        self.__lsig = librarian.connect("changed", self.__update_track_changed)

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS1Player, self).remove_from_connection(*arg, **kwargs)

        window.repeat.disconnect(self.__rsig)
        window.order.disconnect(self.__ssig)
        librarian.disconnect(self.__lsig)

    def paused(self):
        self.StatusChange(self.__get_status())
    unpaused = paused

    def song_started(self, song):
        self.TrackChange(self._get_metadata(song))

    def __update_track_changed(self, library, songs):
        if player.info in songs:
            self.TrackChange(self._get_metadata(player.info))

    def __update_status(self, *args):
        self.StatusChange(self.__get_status())

    @staticmethod
    def _get_metadata(song):
        #http://xmms2.org/wiki/MPRIS_Metadata#MPRIS_v1.0_Metadata_guidelines
        metadata = dbus.Dictionary(signature="sv")
        if not song:
            return metadata

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

        nums = [("audio-bitrate", 1024, "~#bitrate"),
                ("rating", 5, "~#rating"),
                ("year", 1, "~#year"),
                ("time", 1, "~#length"),
                ("mtime", 1000, "~#length")]

        for target, mul, key in nums:
            value = song(key, None)
            if value is None:
                continue
            value = int(value * mul)
            # dbus uses python types to guess the dbus type without
            # checking maxint, also we need uint (dbus always trys int)
            try:
                value = dbus.UInt32(value)
            except OverflowError:
                continue
            metadata[target] = value

        year = song("~year")
        if year:
            try:
                tuple_time = time.strptime(year, "%Y")
            except ValueError:
                pass
            else:
                try:
                    date = int(time.mktime(tuple_time))
                    date = dbus.UInt32(date)
                except (ValueError, OverflowError):
                    pass
                else:
                    metadata["date"] = date

        return metadata

    def __get_status(self):
        play = (not player.info and 2) or int(player.paused)
        shuffle = (window.order.get_active_name() != "inorder")
        repeat_one = (window.order.get_active_name() == "onesong" and
            window.repeat.get_active())
        repeat_all = int(window.repeat.get_active())

        return (play, shuffle, repeat_one, repeat_all)

    @dbus.service.method(IFACE)
    def Next(self):
        player.next()

    @dbus.service.method(IFACE)
    def Prev(self):
        player.previous()

    @dbus.service.method(IFACE)
    def Pause(self):
        if player.song is None:
            player.reset()
        else:
            player.paused ^= True

    @dbus.service.method(IFACE)
    def Stop(self):
        player.stop()

    @dbus.service.method(IFACE)
    def Play(self):
        if player.song is None:
            player.reset()
        else:
            if player.paused:
                player.paused = False
            else:
                player.seek(0)

    @dbus.service.method(IFACE)
    def Repeat(self):
        pass

    @dbus.service.method(IFACE, out_signature="(iiii)")
    def GetStatus(self):
        return self.__get_status()

    @dbus.service.method(IFACE, out_signature="a{sv}")
    def GetMetadata(self):
        return self._get_metadata(player.info)

    @dbus.service.method(IFACE, out_signature="i")
    def GetCaps(self):
        # everything except Tracklist
        return (1 | 1 << 1 | 1 << 2 | 1 << 3 | 1 << 4 | 1 << 5)

    @dbus.service.method(IFACE, in_signature="i")
    def VolumeSet(self, volume):
        player.volume = volume / 100.0

    @dbus.service.method(IFACE, out_signature="i")
    def VolumeGet(self):
        return int(round(player.volume * 100))

    @dbus.service.method(IFACE, in_signature="i")
    def PositionSet(self, position):
        player.seek(position)

    @dbus.service.method(IFACE, out_signature="i")
    def PositionGet(self):
        return int(player.get_position())

    @dbus.service.signal(IFACE, signature="a{sv}")
    def TrackChange(self, metadata):
        pass

    @dbus.service.signal(IFACE, signature="(iiii)")
    def StatusChange(self, status):
        pass

    @dbus.service.signal(IFACE, signature="i")
    def CapsChange(self, status):
        pass


# http://www.mpris.org/2.0/spec/
class MPRIS2(DBusProperty, DBusIntrospectable, MPRISObject):

    BUS_NAME = "org.mpris.MediaPlayer2.quodlibet"
    PATH = "/org/mpris/MediaPlayer2"

    ROOT_IFACE = "org.mpris.MediaPlayer2"

    ROOT_ISPEC = """
<method name="Raise"/>
<method name="Quit"/>"""

    ROOT_PROPS = """
<annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
<property name="CanQuit" type="b" access="read"/>
<property name="CanRaise" type="b" access="read"/>
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
<property name="Volume" type="d" access="readwrite">
  <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
</property>
<property name="Position" type="x" access="read">
  <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
</property>
<property name="MinimumRate" type="d" access="read"/>
<property name="MaximumRate" type="d" access="read"/>
<property name="CanGoNext" type="b" access="read"/>
<property name="CanGoPrevious" type="b" access="read"/>
<property name="CanPlay" type="b" access="read"/>
<property name="CanPause" type="b" access="read"/>
<property name="CanSeek" type="b" access="read"/>
<property name="CanControl" type="b" access="read">
  <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="false"/>
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

        self.__rsig = window.repeat.connect_object(
            "toggled", self.emit_properties_changed,
            self.PLAYER_IFACE, ["LoopStatus"])

        self.__ssig = window.order.connect_object(
            "changed", self.emit_properties_changed,
            self.PLAYER_IFACE, ["Shuffle"])

        self.__lsig = librarian.connect("changed", self.__library_changed)

        self.__seek_sig = player.connect("seek", self.__seeked)

        self.emit_properties_changed(self.PLAYER_IFACE, ["Metadata"])

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS2, self).remove_from_connection(*arg, **kwargs)

        self.__cover = None
        window.repeat.disconnect(self.__rsig)
        window.order.disconnect(self.__ssig)
        librarian.disconnect(self.__lsig)
        player.disconnect(self.__seek_sig)

    @dbus.service.method(ROOT_IFACE)
    def Raise(self):
        window.show()
        window.present()

    @dbus.service.method(ROOT_IFACE)
    def Quit(self):
        window.destroy()

    @dbus.service.signal(PLAYER_IFACE, signature="x")
    def Seeked(self, position):
        pass

    @dbus.service.method(PLAYER_IFACE)
    def Next(self):
        paused = player.paused
        player.next()
        player.paused = paused

    @dbus.service.method(PLAYER_IFACE)
    def Previous(self):
        paused = player.paused
        player.previous()
        player.paused = paused

    @dbus.service.method(PLAYER_IFACE)
    def Pause(self):
        player.paused = True

    @dbus.service.method(PLAYER_IFACE)
    def Play(self):
        if player.song is None:
            player.reset()
        else:
            player.paused = False

    @dbus.service.method(PLAYER_IFACE)
    def PlayPause(self):
        if player.song is None:
            player.reset()
        else:
            player.paused ^= True

    @dbus.service.method(PLAYER_IFACE)
    def Stop(self):
        player.stop()

    @dbus.service.method(PLAYER_IFACE, in_signature="x")
    def Seek(self, offset):
        new_pos = player.get_position() + offset / 1000
        player.seek(new_pos)

    @dbus.service.method(PLAYER_IFACE, in_signature="ox")
    def SetPosition(self, track_id, position):
        current_track_id = self.PATH + "/" + str(id(player.info))
        if track_id == current_track_id:
            player.seek(position / 1000)

    def paused(self):
        self.emit_properties_changed(self.PLAYER_IFACE, ["PlaybackStatus"])
    unpaused = paused

    def song_started(self, song):
        self.emit_properties_changed(self.PLAYER_IFACE, ["Metadata"])

    def __seeked(self, player, song, ms):
        self.Seeked(ms * 1000)

    def __library_changed(self, library, song):
        if song and song is not player.info:
            return
        self.emit_properties_changed(self.PLAYER_IFACE, ["Metadata"])

    def __get_metadata(self):
        """http://xmms2.org/wiki/MPRIS_Metadata"""

        song = player.info

        metadata = dbus.Dictionary(signature="sv")
        metadata["mpris:trackid"] = self.PATH + "/"
        if not song:
            return metadata

        metadata["mpris:trackid"] += str(id(song))
        metadata["mpris:length"] = \
            long(player.info.get("~#length", 0) * 1000000)

        self.__cover = cover = song.find_cover()
        is_temp = False
        if cover:
            name = cover.name
            is_temp = name.startswith(tempfile.gettempdir())
            if isinstance(name, str):
                name = util.fsdecode(name)
            # This doesn't work for embedded images.. the file gets unlinked
            # after loosing the file handle
            metadata["mpris:artUrl"] = str(URI.frompath(name))

        if not is_temp:
            self.__cover = None

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
                metadata["xesam:" + xesam] = val

        # Dates
        ISO_8601_format = "%Y-%m-%dT%H:%M:%S"
        tuple_time = time.gmtime(song("~#lastplayed"))
        iso_time = time.strftime(ISO_8601_format, tuple_time)
        metadata["xesam:lastUsed"] = iso_time

        year = song("~year")
        if year:
            try:
                tuple_time = time.strptime(year, "%Y")
            except ValueError:
                pass
            else:
                try:
                    iso_time = time.strftime(ISO_8601_format, tuple_time)
                except ValueError:
                    pass
                else:
                    metadata["xesam:contentCreated"] = iso_time

        return metadata

    def set_property(self, interface, name, value):
        if interface == self.PLAYER_IFACE:
            if name == "LoopStatus":
                window.repeat.set_active(value == "Playlist")
            elif name == "Rate":
                pass
            elif name == "Shuffle":
                shuffle_on = window.order.get_active_name() == "shuffle"
                if shuffle_on and not value:
                    window.order.set_active("inorder")
                elif not shuffle_on and value:
                    window.order.set_active("shuffle")
            elif name == "Volume":
                player.volume = max(0, value)

    def get_property(self, interface, name):
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
                return "Quod Libet"
            elif name == "DesktopEntry":
                return "quodlibet"
            elif name == "SupportedUriSchemes":
                # TODO: enable once OpenUri is done
                can = lambda s: False
                # from quodlibet.player import backend
                #can = lambda s: backend.can_play_uri("%s://fake" % s)
                array = dbus.Array(signature="s")
                schemes = ["http", "https", "ftp", "file", "mms"]
                array.extend(filter(can, schemes))
                return array
            elif name == "SupportedMimeTypes":
                from quodlibet import formats
                array = dbus.Array(signature="s")
                array.extend(formats.mimes)
                return array
        elif interface == self.PLAYER_IFACE:
            if name == "PlaybackStatus":
                paused = player.paused
                if not player.song or (paused and not player.get_position()):
                    return "Stopped"
                return ("Playing", "Paused")[int(paused)]
            elif name == "LoopStatus":
                # TODO: track status
                return ("None", "Playlist")[int(window.repeat.get_active())]
            elif name == "Rate":
                return 1.0
            elif name == "Shuffle":
                return (window.order.get_active_name() == "shuffle")
            elif name == "Metadata":
                return self.__get_metadata()
            elif name == "Volume":
                return float(player.volume)
            elif name == "Position":
                return long(player.get_position() * 1000)
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
