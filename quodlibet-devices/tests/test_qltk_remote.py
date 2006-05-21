from tests import add, TestCase

import os
import gtk

import const

from formats._audio import AudioFile
from qltk.remote import FSInterface
from player import PlaylistPlayer

class TFSInterface(TestCase):
    def setUp(self):
        self.p = PlaylistPlayer("fakesink")
        self.fs = FSInterface(self.p)

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_init(self):
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def test_start(self):
        self.p.emit('song_started', AudioFile({"woo": "bar", "~#length": 10}))
        self.do()
        self.failUnless("woo=bar\n" in file(const.CURRENT).read())

    def test_song_ended(self):
        self.p.emit('song-started', AudioFile({"woo": "bar", "~#length": 10}))
        self.do()
        self.p.emit('song-ended', {}, False)
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def tearDown(self):
        self.p.destroy()
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass
add(TFSInterface)
