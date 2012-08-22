# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import gtk
import dbus

from tests import TestCase, add
from tests.plugin import PluginTestCase, import_plugin

from quodlibet.formats._audio import AudioFile
from quodlibet import config
from quodlibet import widgets
from quodlibet.qltk.quodlibetwindow import QuodLibetWindow
from quodlibet import library
from quodlibet import browsers
from quodlibet import player
from quodlibet.player.nullbe import NullPlayer


A1 = AudioFile(
        {'album': 'greatness', 'title': 'excellent', 'artist': 'fooman',
         '~#lastplayed': 1234, '~#rating': 0.75, '~filename': '/foo',
         "~#length": 123})
A1.sanitize()
A2 = AudioFile(
        {'album': 'greatness2', 'title': 'superlative', 'artist': 'fooman',
         '~#lastplayed': 1234, '~#rating': 1.0, '~filename': '/foo'})
A2.sanitize()


class TMPRIS(PluginTestCase):
    @classmethod
    def setUpClass(cls):
        config.init()
        browsers.init()
        library.init()
        player.init("nullbe")
        player.init_device(library.librarian)
        widgets.main = QuodLibetWindow(library.library, player.playlist)
        cls.plugin = import_plugin("events", "mpris").MPRIS

    def setUp(self):
        widgets.main.songlist.set_songs([A1, A2])
        player.playlist.go_to(None)
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

        widgets.main.hide()
        self.failIf(widgets.main.get_visible())
        self._main_iface().Raise(**args)
        self.failIf(self._wait())
        self.failUnless(widgets.main.get_visible())
        widgets.main.hide()

        self._prop().Get(piface, "CanQuit", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "CanRaise", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "HasTrackList", **args)
        self.failUnlessEqual(self._wait()[0], False)

        self._prop().Get(piface, "Identity", **args)
        self.failUnlessEqual(self._wait()[0], "Quod Libet")

        self._prop().Get(piface, "DesktopEntry", **args)
        self.failUnlessEqual(self._wait()[0], "quodlibet")

        self._prop().Get(piface, "SupportedUriSchemes", **args)
        self.failUnlessEqual(self._wait()[0], [])

        self._prop().Get(piface, "SupportedMimeTypes", **args)
        self.failUnlessEqual(self._wait()[0], [])

    def test_player(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2.Player"

        self._prop().Get(piface, "PlaybackStatus", **args)
        self.failUnlessEqual(self._wait()[0], "Stopped")

        self._prop().Get(piface, "LoopStatus", **args)
        self.failUnlessEqual(self._wait()[0], "None")

        self._prop().Get(piface, "Rate", **args)
        self.failUnlessEqual(self._wait()[0], 1.0)

        self._prop().Get(piface, "Shuffle", **args)
        self.failUnlessEqual(self._wait()[0], False)

        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]
        self.failUnlessEqual(resp["mpris:trackid"], "/org/mpris/MediaPlayer2/")

        self._prop().Get(piface, "Volume", **args)
        self.failUnlessEqual(self._wait()[0], 1.0)

        self._prop().Get(piface, "Position", **args)
        self.failUnlessEqual(self._wait()[0], 0)

        self._prop().Get(piface, "MinimumRate", **args)
        self.failUnlessEqual(self._wait()[0], 1.0)

        self._prop().Get(piface, "MaximumRate", **args)
        self.failUnlessEqual(self._wait()[0], 1.0)

        self._prop().Get(piface, "CanGoNext", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "CanGoPrevious", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "CanPlay", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "CanPause", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "CanSeek", **args)
        self.failUnlessEqual(self._wait()[0], True)

        self._prop().Get(piface, "CanControl", **args)
        self.failUnlessEqual(self._wait()[0], True)

    def test_metadata(self):
        args = {"reply_handler": self._reply, "error_handler": self._error}
        piface = "org.mpris.MediaPlayer2.Player"

        self._player_iface().Next(**args)
        self._wait()

        self._prop().Get(piface, "Metadata", **args)
        resp = self._wait()[0]
        self.failIfEqual(resp["mpris:trackid"], "/org/mpris/MediaPlayer2/")

        self.failUnlessEqual(resp["xesam:album"], "greatness")
        self.failUnlessEqual(resp["xesam:artist"], ["fooman"])
        self.failUnlessAlmostEqual(resp["xesam:userRating"], 0.75)

        self.failUnlessEqual(resp["mpris:length"], 123 * 10**6)
        from time import strptime
        from calendar import timegm
        seconds = timegm(strptime(resp["xesam:lastUsed"], "%Y-%m-%dT%H:%M:%S"))
        self.failUnlessEqual(seconds, 1234)

    def tearDown(self):
        self.m.disabled()
        del self.m

    @classmethod
    def tearDownClass(cls):
        widgets.main.destroy()
        config.quit()

add(TMPRIS)
