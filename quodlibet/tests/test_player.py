# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from senf import fsnative

from tests import TestCase, skipUnless

from quodlibet import player
from quodlibet import library
from quodlibet import config
from quodlibet.util import connect_obj
from quodlibet.player.nullbe import NullPlayer
from quodlibet.formats import AudioFile
from quodlibet.qltk.songmodel import PlaylistModel
from quodlibet.qltk.controls import Volume


FILES = [
    AudioFile({"~filename": fsnative(u"/foo/bar1"), "title": "1"}),
    AudioFile({"~filename": fsnative(u"/foo/bar2"), "title": "2"}),
    AudioFile({"~filename": fsnative(u"/foo/bar3"), "title": "3"}),
]
for file_ in FILES:
    file_.sanitize()

UNKNOWN_FILE = FILES.pop(-1)


class TPlayer(TestCase):
    NAME = None

    def setUp(self):
        config.init()
        config.set("player", "gst_pipeline", "fakesink")
        module = player.init_backend(self.NAME)
        lib = library.init()
        self.player = module.init(lib.librarian)
        source = PlaylistModel()
        source.set(FILES)

        self.events = []

        def start_end_handler(player, song, *args):
            self.events.append((args[-1], song))

        self.player.connect("song-started", start_end_handler, "started")
        self.player.connect("song-ended", start_end_handler, "ended")

        self.player.setup(source, None, 0)

        self.signals = []

        def handler(type_, *args):
            self.signals.append(type_)
        connect_obj(self.player, "unpaused", handler, "unpaused")
        connect_obj(self.player, "paused", handler, "paused")

    def _check_events(self):
        # make sure song-started and song-ended match up
        stack = []
        old = self.events[:]
        for type_, song in self.events:
            if type_ == "started":
                stack.append(song)
            elif type_ == "ended":
                self.assertTrue(stack.pop(-1) is song, msg=old)
        self.assertFalse(stack, msg=old)

    def tearDown(self):
        self.player.destroy()

        self._check_events()
        del self.events
        del self.signals
        config.quit()


class TPlayerMixin(object):

    def test_song_start(self):
        self.assertFalse(self.player.song)
        self.assertFalse(self.player.info)

    def test_paused(self):
        self.assertTrue(self.player.paused)
        self.player.paused = False
        self.assertFalse(self.player.paused)
        self.assertTrue(self.signals, ["unpaused"])

    def test_volume(self):
        self.assertEqual(self.player.volume, 1.0)
        self.player.volume = 1000
        self.assertEqual(self.player.volume, 1.0)
        self.player.volume = -1000
        self.assertEqual(self.player.volume, 0.0)
        self.player.volume = 0.5
        self.assertEqual(self.player.volume, 0.5)

    def test_remove(self):
        self.player.remove(None)
        self.player.go_to(FILES[0])
        self.assertEqual(self.player.song, FILES[0])
        self.player.remove(FILES[0])
        self.assertEqual(self.player.song, FILES[1])
        self.player.remove(None)
        self.assertEqual(self.player.song, FILES[1])

    def test_next(self):
        self.assertFalse(self.player.song)
        self.player.next()
        self.assertEqual(self.player.song, FILES[0])
        self.player.next()
        self.assertEqual(self.player.song, FILES[1])
        self.player.next()
        self.assertFalse(self.player.song)

    def test_previous(self):
        self.player.next()
        self.player.next()
        self.assertEqual(self.player.song, FILES[1])
        self.player.previous()
        self.assertEqual(self.player.song, FILES[0])

    def test_goto(self):
        self.assertTrue(self.player.paused)
        self.player.go_to(FILES[1])
        self.assertEqual(self.player.song, FILES[1])
        self.assertTrue(self.player.paused)
        self.player.go_to(FILES[0], explicit=True)
        self.assertEqual(self.player.song, FILES[0])

    def test_goto_unknown(self):
        self.assertTrue(self.player.paused)
        self.player.go_to(UNKNOWN_FILE, True)
        self.assertIs(self.player.song, UNKNOWN_FILE)
        self.assertTrue(self.player.paused)
        self.player.go_to(None)
        self.assertIs(self.player.song, None)

    def test_reset(self):
        self.player.go_to(None)
        self.player.reset()
        self.assertEqual(self.player.song, FILES[0])
        self.player.next()
        self.player.reset()
        self.assertEqual(self.player.song, FILES[0])

    def test_equalizer(self):
        self.player.eq_bands
        self.player.eq_values
        self.player.eq_values = [1, 2, 3, 4]
        self.player.next()

    def test_unpause_while_no_song(self):
        self.assertTrue(self.player.paused)
        self.player.go_to(None)
        self.player.paused = False
        self.player.next()
        self.assertTrue(self.signals, ["unpaused"])
        self.player.go_to(None)
        self.assertTrue(self.signals, ["unpaused", "paused"])

    def test_replaygain(self):
        self.player.replaygain_profiles[0] = "track"
        self.player.next()
        config.set("player", "replaygain", True)
        self.assertEqual(self.player.calc_replaygain_volume(1.0), 1.0)
        config.set("player", "fallback_gain", -5.0)
        self.assertAlmostEqual(
            self.player.calc_replaygain_volume(1.0), 0.562, 3)
        config.set("player", "pre_amp_gain", 10.0)
        self.assertEqual(self.player.calc_replaygain_volume(1.0), 1.0)

    def test_seekable(self):
        self.assertFalse(self.player.seekable)
        self.player.next()
        self.assertTrue(self.player.seekable)

        calls = []

        def on_change(*args):
            calls.append(args)

        self.player.connect("notify::seekable", on_change)
        self.player.go_to(None)
        self.assertTrue(calls)
        self.assertFalse(self.player.seekable)

    def test_mute(self):
        self.assertFalse(self.player.mute)
        self.player.next()
        self.assertFalse(self.player.mute)
        # backend don't have to support it, but shouldn't fail on set/get
        self.player.mute = not self.player.mute

    def test_preserve_volume(self):
        self.player.next()
        self.player.volume = 0.5
        self.player.next()
        self.assertEqual(self.player.volume, 0.5)


class TNullPlayer(TPlayer, TPlayerMixin):
    NAME = "nullbe"

    def test_previous_seek(self):
        self.player.next()
        self.player.next()
        self.assertEqual(self.player.song, FILES[1])
        self.player.seek(10000)
        self.assertEqual(self.player.get_position(), 10000)
        self.player.previous()
        self.assertEqual(self.player.get_position(), 0)
        self.assertEqual(self.player.song, FILES[1])

    def test_previous_force(self):
        self.player.next()
        self.player.next()
        self.assertEqual(self.player.song, FILES[1])
        self.player.seek(10000)
        self.assertEqual(self.player.get_position(), 10000)
        self.player.previous(force=True)
        self.assertEqual(self.player.get_position(), 0)
        self.assertEqual(self.player.song, FILES[0])

    def test_previous_skip(self):
        self.player.next()
        self.player.next()
        self.assertEqual(self.player.song, FILES[1])
        self.player.seek(10)
        self.assertEqual(self.player.get_position(), 10)
        self.player.previous()
        self.assertEqual(self.player.get_position(), 0)
        self.assertEqual(self.player.song, FILES[0])

    def test_stop(self):
        self.player.next()
        self.player.seek(10000)
        self.assertEqual(self.player.get_position(), 10000)
        self.player.stop()
        self.assertEqual(self.player.get_position(), 0)

    def test_can_play_uri_null(self):
        self.assertTrue(self.player.can_play_uri(""))
        self.assertTrue(self.player.can_play_uri("file://"))
        self.assertTrue(self.player.can_play_uri("fake://"))


has_xine = True
try:
    player.init_backend("xinebe")
except player.PlayerError:
    has_xine = False


@skipUnless(has_xine, "couldn't load/test xinebe")
class TXinePlayer(TPlayer, TPlayerMixin):
    NAME = "xinebe"

    def test_can_play_uri_xine(self):
        self.assertFalse(self.player.can_play_uri(""))
        self.assertTrue(self.player.can_play_uri("file://"))
        self.assertFalse(self.player.can_play_uri("fake://"))


has_gstbe = True
try:
    player.init_backend("gstbe")
except player.PlayerError:
    has_gstbe = False


@skipUnless(has_gstbe, "couldn't load/test gstbe")
class TGstPlayer(TPlayer, TPlayerMixin):
    NAME = "gstbe"

    def test_can_play_uri_gst(self):
        self.assertFalse(self.player.can_play_uri(""))
        self.assertTrue(self.player.can_play_uri("file://"))
        self.assertFalse(self.player.can_play_uri("fake://"))


class TVolume(TestCase):
    def setUp(self):
        self.p = NullPlayer()
        self.v = Volume(self.p)

    def test_setget(self):
        for i in [0.0, 1.2, 0.24, 1.0, 0.9]:
            self.v.set_value(i)
            self.failUnlessAlmostEqual(self.p.volume, self.v.get_value() ** 3)

    def test_add(self):
        self.v.set_value(0.5)
        self.v += 0.1
        self.failUnlessAlmostEqual(self.p.volume, 0.6 ** 3)

    def test_sub(self):
        self.v.set_value(0.5)
        self.v -= 0.1
        self.failUnlessAlmostEqual(self.p.volume, 0.4 ** 3)

    def test_add_boundry(self):
        self.v.set_value(0.95)
        self.v += 0.1
        self.failUnlessAlmostEqual(self.p.volume, 1.0)

    def test_sub_boundry(self):
        self.v.set_value(0.05)
        self.v -= 0.1
        self.failUnlessAlmostEqual(self.p.volume, 0.0)

    def tearDown(self):
        self.p.destroy()
        self.v.destroy()
