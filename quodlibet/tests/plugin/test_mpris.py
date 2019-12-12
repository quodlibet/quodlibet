# Copyright 2012,2013 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

try:
    import dbus
except ImportError:
    dbus = None

from gi.repository import Gtk
from senf import fsnative

from tests import skipUnless
from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app

from quodlibet.formats import AudioFile
from quodlibet import config
from quodlibet import app


A1 = AudioFile(
        {'album': u'greatness', 'title': 'excellent', 'artist': 'fooman\ngo',
         '~#lastplayed': 1234, '~#rating': 0.75,
         '~filename': fsnative(u'/foo a/b'),
         "~#length": 123, "albumartist": "aa\nbb", "bpm": "123.5",
         "tracknumber": "6/7"})
A1.sanitize()

A2 = AudioFile(
        {'album': u'greatness2\ufffe', 'title': 'superlative',
         'artist': u'fooman\ufffe', '~#lastplayed': 1234, '~#rating': 1.0,
         '~filename': fsnative(u'/foo'), 'discnumber': '4294967296'})
A2.sanitize()

MAX_TIME = 3


@skipUnless(dbus, "no dbus")
class TMPRIS(PluginTestCase):

    BUS_NAME = "org.mpris.MediaPlayer2.quodlibet"

    def setUp(self):
        self.plugin = self.plugins["mpris"].cls

        config.init()
        init_fake_app()

        while Gtk.events_pending():
            Gtk.main_iteration()

        app.window.songlist.set_songs([A1, A2])
        app.player.go_to(None)
        self.m = self.plugin()
        self.m.enabled()
        self._replies = []

    def tearDown(self):
        bus = dbus.SessionBus()
        self.failUnless(
            bus.name_has_owner(self.BUS_NAME))
        self.m.disabled()
        self.failIf(bus.name_has_owner(self.BUS_NAME))

        destroy_fake_app()
        config.quit()
        del self.m

    def test_name_owner(self):
        bus = dbus.SessionBus()
        self.failUnless(bus.name_has_owner(self.BUS_NAME))

    def _main_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object(self.BUS_NAME, "/org/mpris/MediaPlayer2")
        return dbus.Interface(obj,
                              dbus_interface="org.mpris.MediaPlayer2")

    def _prop(self):
        bus = dbus.SessionBus()
        obj = bus.get_object(self.BUS_NAME, "/org/mpris/MediaPlayer2")
        return dbus.Interface(obj,
                              dbus_interface="org.freedesktop.DBus.Properties")

    def _player_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object(self.BUS_NAME, "/org/mpris/MediaPlayer2")
        return dbus.Interface(obj,
                              dbus_interface="org.mpris.MediaPlayer2.Player")

    def _introspect_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object(self.BUS_NAME, "/org/mpris/MediaPlayer2")
        return dbus.Interface(
            obj, dbus_interface="org.freedesktop.DBus.Introspectable")

    def _reply(self, *args):
        self._replies.append(args)

    def _error(self, *args):
        self.failIf(args)

    def _wait(self, msg=""):
        start = time.time()
        while not self._replies:
            Gtk.main_iteration_do(False)
            if time.time() - start > MAX_TIME:
                self.fail("Timed out waiting for replies (%s)" % msg)
        return self._replies.pop(0)

    def test_main(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2"

        app.window.hide()
        self.failIf(app.window.get_visible())
        self._main_iface().Raise(**args)
        self.failIf(self._wait())
        self.failUnless(app.window.get_visible())
        app.window.hide()

        props = {
            "CanQuit": dbus.Boolean(True),
            "CanRaise": dbus.Boolean(True),
            "CanSetFullscreen": dbus.Boolean(False),
            "HasTrackList": dbus.Boolean(False),
            "Identity": dbus.String("Quod Libet"),
            "DesktopEntry": dbus.String("io.github.quodlibet.QuodLibet"),
            "SupportedUriSchemes": dbus.Array(),
        }

        for key, value in props.items():
            self._prop().Get(piface, key, **args)
            resp = self._wait()[0]
            self.failUnlessEqual(resp, value)
            self.failUnless(isinstance(resp, type(value)))

        self._prop().Get(piface, "SupportedMimeTypes", **args)
        self.failUnless("audio/vorbis" in self._wait()[0])

        self._introspect_iface().Introspect(**args)
        assert self._wait()

    def test_player(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2.Player"

        props = {
            "PlaybackStatus": dbus.String("Stopped"),
            "LoopStatus": dbus.String("None"),
            "Rate": dbus.Double(1.0),
            "Shuffle": dbus.Boolean(False),
            "Volume": dbus.Double(1.0),
            "Position": dbus.Int64(0),
            "MinimumRate": dbus.Double(1.0),
            "MaximumRate": dbus.Double(1.0),
            "CanGoNext": dbus.Boolean(True),
            "CanGoPrevious": dbus.Boolean(True),
            "CanPlay": dbus.Boolean(True),
            "CanPause": dbus.Boolean(True),
            "CanSeek": dbus.Boolean(True),
            "CanControl": dbus.Boolean(True),
        }

        for key, value in props.items():
            self._prop().Get(piface, key, **args)
            resp = self._wait(msg="for key '%s'" % key)[0]
            self.failUnlessEqual(resp, value)
            self.failUnless(isinstance(resp, type(value)))

    def test_volume_property(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2.Player"

        def get_volume():
            self._prop().Get(piface, "Volume", **args)
            return float(self._wait()[0])

        assert get_volume() == 1.0
        app.player.volume = 0.5
        assert get_volume() == 0.5
        self._prop().Set(piface, "Volume", 0.25, **args)
        self._wait()
        assert app.player.volume == 0.25

    def test_metadata(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2.Player"

        # No song case
        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]
        self.failUnlessEqual(resp["mpris:trackid"],
                             "/net/sacredchao/QuodLibet/NoTrack")
        self.failUnless(isinstance(resp["mpris:trackid"], dbus.ObjectPath))

        # go to next song
        self._player_iface().Next(**args)
        self._wait()
        self.m.plugin_on_song_started(app.player.info)

        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]
        self.failIfEqual(resp["mpris:trackid"],
                         "/net/sacredchao/QuodLibet/NoTrack")

        # mpris stuff
        self.failIf(resp["mpris:trackid"].startswith("/org/mpris/"))
        self.failUnless(isinstance(resp["mpris:trackid"], dbus.ObjectPath))

        self.failUnlessEqual(resp["mpris:length"], 123 * 10 ** 6)
        self.failUnless(isinstance(resp["mpris:length"], dbus.Int64))

        # list text values
        self.failUnlessEqual(resp["xesam:artist"], ["fooman", "go"])
        self.failUnlessEqual(resp["xesam:albumArtist"], ["aa", "bb"])

        # single text values
        self.failUnlessEqual(resp["xesam:album"], "greatness")
        self.failUnlessEqual(resp["xesam:title"], "excellent")
        self.failUnlessEqual(resp["xesam:url"], "file:///foo%20a/b")

        # integers
        self.failUnlessEqual(resp["xesam:audioBPM"], 123)
        self.failUnless(isinstance(resp["xesam:audioBPM"], dbus.Int32))

        self.failUnlessEqual(resp["xesam:trackNumber"], 6)
        self.failUnless(isinstance(resp["xesam:trackNumber"], dbus.Int32))

        # rating
        self.failUnlessAlmostEqual(resp["xesam:userRating"], 0.75)
        self.failUnless(isinstance(resp["xesam:userRating"], dbus.Double))

        # time
        from time import strptime
        from calendar import timegm
        seconds = timegm(strptime(resp["xesam:lastUsed"], "%Y-%m-%dT%H:%M:%S"))
        self.failUnlessEqual(seconds, 1234)

        # go to next song with invalid utf-8
        self._player_iface().Next(**args)
        self._wait()
        self.m.plugin_on_song_started(app.player.info)

        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]
        self.failUnlessEqual(resp["xesam:album"], u'greatness2\ufffd')
        self.failUnlessEqual(resp["xesam:artist"], [u'fooman\ufffd'])
        # overflow
        assert resp["xesam:discNumber"] == 0
