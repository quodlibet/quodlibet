from tests import add, TestCase

import os
import gtk

import const

from formats._audio import AudioFile
from qltk.remote import FSInterface
from qltk.watcher import SongWatcher

class TFSInterface(TestCase):
    def setUp(self):
        self.w = SongWatcher()
        self.fs = FSInterface(self.w)

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_init(self):
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def test_start(self):
        self.w.song_started(AudioFile({"woo": "bar", "~#length": 10}))
        self.do()
        self.failUnless("woo=bar\n" in file(const.CURRENT).read())

    def test_song_ended(self):
        self.w.song_started(AudioFile({"woo": "bar", "~#length": 10}))
        self.do()
        self.w.song_ended({}, False)
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def tearDown(self):
        self.w.destroy()
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass
add(TFSInterface)
