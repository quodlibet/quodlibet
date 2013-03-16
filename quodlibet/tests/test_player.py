# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests import TestCase, add

from quodlibet import player
from quodlibet import library
from quodlibet import config
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.songmodel import PlaylistModel


FILES = [
    AudioFile({"~filename": "/foo/bar1", "title": "1"}),
    AudioFile({"~filename": "/foo/bar2", "title": "2"})
]
for file_ in FILES:
    file_.sanitize()


class TPlayer(TestCase):
    NAME = None

    def setUp(self):
        config.init()
        module = player.init(self.NAME)
        lib = library.init()
        self.player = module.init(lib.librarian)
        source = PlaylistModel()
        # FIXME: GIPORT, source.set segfaults here
        #source.set(FILES)
        for song in FILES:
            source.append(row=[song])
        self.player.setup(source, None, 0)

    def tearDown(self):
        import __builtin__
        pw = print_w
        __builtin__.__dict__["print_w"] = lambda *x: None
        # FIXME: idle_add should be removed on destroy, wait here instead
        while Gtk.events_pending():
            Gtk.main_iteration()
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

    def test_can_play_uri(self):
        self.player.can_play_uri("")
        self.player.can_play_uri("file://")
        self.assertFalse(self.player.can_play_uri("fake://"))

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

add(TNullPlayer)


class TXinePlayer(TPlayer):
    NAME = "xinebe"

if player.init(TXinePlayer.NAME):
    add(TXinePlayer)
else:
    print_w("couldn't load xinebe")


class TGstPlayer(TPlayer):
    NAME = "gstbe"

if player.init(TGstPlayer.NAME):
    add(TGstPlayer)
else:
    print_w("couldn't load gstbe")
