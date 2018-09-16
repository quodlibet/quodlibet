# -*- coding: utf-8 -*-
# Copyright 2010,2012 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

import dbus
import dbus.service

from quodlibet import app
from quodlibet.util.dbusutils import dbus_unicode_validate as unival

from .util import MPRISObject


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
        return app.name

    @dbus.service.method(IFACE)
    def Quit(self):
        app.quit()

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
        song = app.player.info
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
    def SetLoop(self, value):
        app.player_options.repeat = value

    @dbus.service.method(IFACE, in_signature="b")
    def SetRandom(self, value):
        app.player_options.shuffle = value


class MPRIS1Player(MPRISObject):
    PATH = "/Player"
    BUS_NAME = "org.mpris.quodlibet"
    IFACE = "org.freedesktop.MediaPlayer"

    def __init__(self):
        bus = dbus.SessionBus()
        name = dbus.service.BusName(self.BUS_NAME, bus)
        super(MPRIS1Player, self).__init__(name, self.PATH)

        player_options = app.player_options
        self.__sigs = [
            player_options.connect("notify::repeat", self.__update_status),
            player_options.connect("notify::single", self.__update_status),
            player_options.connect("notify::shuffle", self.__update_status),
        ]

        self.__lsig = app.librarian.connect(
            "changed", self.__update_track_changed)

    def remove_from_connection(self, *arg, **kwargs):
        super(MPRIS1Player, self).remove_from_connection(*arg, **kwargs)

        for id_ in self.__sigs:
            app.player_options.disconnect(id_)

        app.librarian.disconnect(self.__lsig)

    def paused(self):
        self.StatusChange(self.__get_status())
    unpaused = paused

    def song_started(self, song):
        self.TrackChange(self._get_metadata(song))

    def __update_track_changed(self, library, songs):
        if app.player.info in songs:
            self.TrackChange(self._get_metadata(app.player.info))

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

        for key, tag in strings.items():
            val = song.comma(tag)
            if val:
                metadata[key] = unival(val)

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
            # checking maxint, also we need uint (dbus always tries int)
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
        if app.player.info is not None:
            play = 0 if not app.player.paused else 1
        else:
            play = 2
        shuffle = app.player_options.shuffle
        repeat_one = app.player_options.single
        repeat_all = app.player_options.repeat

        return (play, shuffle, repeat_one, repeat_all)

    @dbus.service.method(IFACE)
    def Next(self):
        app.player.next()

    @dbus.service.method(IFACE)
    def Prev(self):
        app.player.previous()

    @dbus.service.method(IFACE)
    def Pause(self):
        app.player.paused = True

    @dbus.service.method(IFACE)
    def Stop(self):
        app.player.stop()

    @dbus.service.method(IFACE)
    def Play(self):
        app.player.play()

    @dbus.service.method(IFACE, in_signature="b")
    def Repeat(self, value):
        app.player_options.single = value

    @dbus.service.method(IFACE, out_signature="(iiii)")
    def GetStatus(self):
        return self.__get_status()

    @dbus.service.method(IFACE, out_signature="a{sv}")
    def GetMetadata(self):
        return self._get_metadata(app.player.info)

    @dbus.service.method(IFACE, out_signature="i")
    def GetCaps(self):
        # everything except Tracklist
        return (1 | 1 << 1 | 1 << 2 | 1 << 3 | 1 << 4 | 1 << 5)

    @dbus.service.method(IFACE, in_signature="i")
    def VolumeSet(self, volume):
        app.player.volume = volume / 100.0

    @dbus.service.method(IFACE, out_signature="i")
    def VolumeGet(self):
        return int(round(app.player.volume * 100))

    @dbus.service.method(IFACE, in_signature="i")
    def PositionSet(self, position):
        app.player.seek(position)

    @dbus.service.method(IFACE, out_signature="i")
    def PositionGet(self):
        return int(app.player.get_position())

    @dbus.service.signal(IFACE, signature="a{sv}")
    def TrackChange(self, metadata):
        pass

    @dbus.service.signal(IFACE, signature="(iiii)")
    def StatusChange(self, status):
        pass

    @dbus.service.signal(IFACE, signature="i")
    def CapsChange(self, status):
        pass
