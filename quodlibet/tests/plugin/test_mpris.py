# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import gtk
import dbus

from tests import TestCase, add
from tests.plugin import PluginTestCase

from quodlibet.formats._audio import AudioFile
from quodlibet import config
from quodlibet.qltk.quodlibetwindow import QuodLibetWindow
from quodlibet import library
from quodlibet import browsers
from quodlibet import player
from quodlibet import app
from quodlibet.player.nullbe import NullPlayer


A1 = AudioFile(
        {'album': u'greatness', 'title': 'excellent', 'artist': 'fooman\ngo',
         '~#lastplayed': 1234, '~#rating': 0.75, '~filename': '/foo a/b',
         "~#length": 123, "albumartist": "aa\nbb", "bpm": "123.5",
         "tracknumber": "6/7"})
A1.sanitize()

A2 = AudioFile(
        {'album': u'greatness2\ufffe', 'title': 'superlative',
         'artist': u'fooman\ufffe', '~#lastplayed': 1234, '~#rating': 1.0,
         '~filename': '/foo'})
A2.sanitize()

class TMPRIS(PluginTestCase):
    @classmethod
    def setUpClass(cls):
        config.init()
        browsers.init()
        library.init()
        player.init("nullbe")

        app.player = player.init_device(library.librarian)
        app.window = QuodLibetWindow(library.library, player.playlist)
        app.librarian = library.librarian
        app.player = player.playlist

        cls.plugin = cls.plugins["mpris"]

    def setUp(self):
        app.window.songlist.set_songs([A1, A2])
        app.player.go_to(None)
        self.m = self.plugin()
        self.m.enabled()
        self._replies = []

    def _main_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.mpris.quodlibet", "/org/mpris/MediaPlayer2")
        return dbus.Interface(obj,
                              dbus_interface="org.mpris.MediaPlayer2")

    def _prop(self):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.mpris.quodlibet", "/org/mpris/MediaPlayer2")
        return dbus.Interface(obj,
                              dbus_interface="org.freedesktop.DBus.Properties")

    def _player_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.mpris.quodlibet", "/org/mpris/MediaPlayer2")
        return dbus.Interface(obj,
                              dbus_interface="org.mpris.MediaPlayer2.Player")


    def _reply(self, *args):
        self._replies.append(args)

    def _error(self, *args):
        self.failIf(args)

    def _wait(self):
        while not self._replies:
            gtk.main_iteration(False)
        return self._replies.pop(0)

    def test_main(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2"

        app.window.hide()
        self.failIf(app.window.flags() & gtk.VISIBLE)
        self._main_iface().Raise(**args)
        self.failIf(self._wait())
        self.failUnless(app.window.flags() & gtk.VISIBLE)
        app.window.hide()

        props = {
            "CanQuit": dbus.Boolean(True),
            "CanRaise": dbus.Boolean(True),
            "CanSetFullscreen": dbus.Boolean(False),
            "HasTrackList": dbus.Boolean(False),
            "Identity": dbus.String("Quod Libet"),
            "DesktopEntry": dbus.String("quodlibet"),
            "SupportedUriSchemes": dbus.Array(),
        }

        for key, value in props.iteritems():
            self._prop().Get(piface, key, **args)
            resp = self._wait()[0]
            self.failUnlessEqual(resp, value)
            self.failUnless(isinstance(resp, type(value)))

        self._prop().Get(piface, "SupportedMimeTypes", **args)
        self.failUnless("audio/vorbis" in self._wait()[0])

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

        for key, value in props.iteritems():
            self._prop().Get(piface, key, **args)
            resp = self._wait()[0]
            self.failUnlessEqual(resp, value)
            self.failUnless(isinstance(resp, type(value)))

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

        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]

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

        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]
        self.failUnlessEqual(resp["xesam:album"], u'greatness2\ufffd')
        self.failUnlessEqual(resp["xesam:artist"], [u'fooman\ufffd'])

    def tearDown(self):
        self.m.disabled()
        del self.m

    @classmethod
    def tearDownClass(cls):
        app.window.destroy()
        config.quit()

add(TMPRIS)
