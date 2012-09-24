from tests import TestCase, add

import gtk

from quodlibet.formats._audio import AudioFile
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.tracker import SongTracker
from quodlibet.library import SongLibrary

class TSongTracker(TestCase):
    def setUp(self):
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

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_play(self):
        import time
        # Allow at least 2 second to elapse to simulate playing
        self.p.song = self.s1
        self.p.paused = False
        time.sleep(2)
        self.do()
        self.p.emit('song-ended', self.s1, False)
        self.do()
        t = time.time()
        self.assertEquals(self.s1["~#playcount"], 1)
        self.assertEquals(self.s1["~#skipcount"], 0)
        self.failUnless(t - self.s1["~#lastplayed"] <= 1)

    def test_skip(self):
        self.p.emit('song-ended', self.s1, True)
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 1)
        self.failUnless(self.s1["~#lastplayed"], 10)

    def test_error(self):
        self.current = self.p.song = self.s1
        self.p.error('Test error')
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 0)
        self.assertEquals(self.s1["~errors"].endswith('Test error\n\n'), True)
        self.failUnless(self.s1["~#lastplayed"], 10)

    def test_restart(self):
        self.current = self.s1
        self.p.emit('song-ended', self.s1, True)
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 0)

    def tearDown(self):
        self.w.destroy()

add(TSongTracker)

