# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil

from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary
from quodlibet.library.file import FileLibrary
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.tracker import SongTracker, FSInterface
from tests import TestCase, mkdtemp, run_gtk_loop

A_PATH = "/dev/null"


class TSongTracker(TestCase):
    def setUp(self):
        config.init()
        self.p = NullPlayer()
        self.w = SongLibrary()
        self.s1 = AudioFile(
            {"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10,
             "~filename": "foo", "~#length": 1.5})
        self.s2 = AudioFile(
            {"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10,
             "~filename": "foo", "~#length": 1.5})
        self.cm = SongTracker(self.w, self.p, self)
        self.current = None

    def test_destroy(self):
        self.cm.destroy()

    def test_play(self):
        import time
        # Allow at least 2 second to elapse to simulate playing
        self.p.song = self.s1
        self.p.paused = False
        time.sleep(2)
        run_gtk_loop()
        self.p.emit('song-ended', self.s1, False)
        run_gtk_loop()
        t = time.time()
        self.assertEquals(self.s1["~#playcount"], 1)
        self.assertEquals(self.s1["~#skipcount"], 0)
        self.failUnless(t - self.s1["~#lastplayed"] <= 1)

    def test_skip(self):
        self.p.emit('song-ended', self.s1, True)
        run_gtk_loop()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 1)
        self.failUnless(self.s1["~#lastplayed"], 10)

    def test_error(self):
        self.current = self.p.song = self.s1
        self.p._error('Test error')
        run_gtk_loop()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 0)
        self.failUnless(self.s1["~#lastplayed"], 10)

    def test_restart(self):
        self.current = self.s1
        self.p.emit('song-ended', self.s1, True)
        run_gtk_loop()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 0)

    def tearDown(self):
        self.w.destroy()
        config.quit()


class TFSInterface(TestCase):
    def setUp(self):
        self.p = NullPlayer()
        self.dir = mkdtemp()
        self.lib = FileLibrary()
        self.song = AudioFile({"~filename": A_PATH, "title": "bar", "~#length": 10})
        self.lib.add([self.song])
        self.filename = os.path.join(self.dir, "foo")
        self.fs = FSInterface(self.filename, self.p, self.lib)

    def tearDown(self):
        self.p.destroy()
        self.lib.destroy()
        shutil.rmtree(self.dir)

    def test_init(self):
        run_gtk_loop()
        self.failIf(os.path.exists(self.filename))

    def test_start(self):
        self.p.emit('song_started', self.song)
        run_gtk_loop()
        with open(self.filename, "rb") as h:
            self.failUnless(b"title=bar\n" in h.read())

    def test_song_ended(self):
        self.p.emit('song-started', self.song)
        run_gtk_loop()
        self.p.emit('song-ended', {}, False)
        run_gtk_loop()
        self.failIf(os.path.exists(self.filename))

    def test_elapsed(self):
        self.p.seek(123456)
        self.p.emit('song-started', AudioFile({"~#length": 10}))
        run_gtk_loop()
        with open(self.filename, "rb") as h:
            contents = h.read()
        assert b"~#elapsed=123.456" in contents
        assert b"~elapsed=2:03\n" in contents

    def test_current_song_changed(self):
        self.p.song = self.song
        self.song["title"] = "new!"
        self.lib.changed([self.song])
        run_gtk_loop()
        with open(self.filename, "rb") as h:
            contents = h.read()
        assert b"title=new!\n" in contents
