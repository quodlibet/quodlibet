# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests import TestCase, skipUnless, AbstractTestCase

from quodlibet import player
from quodlibet import library
from quodlibet import config
from quodlibet.player.nullbe import NullPlayer
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.songmodel import PlaylistModel
from quodlibet.qltk.controls import Volume


FILES = [
    AudioFile({"~filename": "/foo/bar1", "title": "1"}),
    AudioFile({"~filename": "/foo/bar2", "title": "2"})
]
for file_ in FILES:
    file_.sanitize()


class TPlayer(AbstractTestCase):
    NAME = None

    def setUp(self):
        config.init()
        config.set("player", "gst_pipeline", "fakesink")
        module = player.init(self.NAME)
        lib = library.init()
        self.player = module.init(lib.librarian)
        source = PlaylistModel()
        source.set(FILES)
        self.player.setup(source, None, 0)

    def tearDown(self):
        import __builtin__
        pw = print_w
        __builtin__.__dict__["print_w"] = lambda *x: None
        self.player.destroy()
        while Gtk.events_pending():
            Gtk.main_iteration()
        __builtin__.__dict__["print_w"] = pw
        config.quit()

    def test_song_start(self):
        self.assertFalse(self.player.song)
        self.assertFalse(self.player.info)

    def test_paused(self):
        self.assertTrue(self.player.paused)
        self.player.paused = False
        self.assertFalse(self.player.paused)

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


class TNullPlayer(TPlayer):
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

    def test_can_play_uri_xine(self):
        self.assertFalse(self.player.can_play_uri(""))
        self.assertFalse(self.player.can_play_uri("file://"))
        self.assertFalse(self.player.can_play_uri("fake://"))


has_xine = True
try:
    player.init("xinebe")
except player.PlayerError:
    has_xine = False


@skipUnless(has_xine, "couldn't load/test xinebe")
class TXinePlayer(TPlayer):
    NAME = "xinebe"

    def test_can_play_uri_xine(self):
        self.assertFalse(self.player.can_play_uri(""))
        self.assertTrue(self.player.can_play_uri("file://"))
        self.assertFalse(self.player.can_play_uri("fake://"))


has_gstbe = True
try:
    player.init("gstbe")
except player.PlayerError:
    has_gstbe = False


@skipUnless(has_gstbe, "couldn't load/test gstbe")
class TGstPlayer(TPlayer):
    NAME = "gstbe"

    def test_can_play_uri_gst(self):
        self.assertFalse(self.player.can_play_uri(""))
        self.assertTrue(self.player.can_play_uri("file://"))
        self.assertFalse(self.player.can_play_uri("fake://"))


class TVolume(TestCase):
    def setUp(self):
        config.init()
        self.p = NullPlayer()
        self.v = Volume(self.p)

    def test_setget(self):
        for i in [0.0, 1.2, 0.24, 1.0, 0.9]:
            self.v.set_value(i)
            self.failUnlessAlmostEqual(self.p.volume, self.v.get_value())

    def test_add(self):
        self.v.set_value(0.5)
        self.v += 0.1
        self.failUnlessAlmostEqual(self.p.volume, 0.6)

    def test_sub(self):
        self.v.set_value(0.5)
        self.v -= 0.1
        self.failUnlessAlmostEqual(self.p.volume, 0.4)

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
        config.quit()
