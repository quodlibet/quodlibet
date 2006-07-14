from tests import TestCase, add

from player import PlaylistPlayer
from qltk.controls import PlayControls, Volume
from library import SongLibrary

class TPlayControls(TestCase):
    def test_ctr(self):
        PlayControls(PlaylistPlayer('fakesink'), SongLibrary()).destroy()
add(TPlayControls)

class TVolume(TestCase):
    def setUp(self):
        self.volume = 0.5

    def test_set(self):
        Volume(self).set_value(0.1)
        self.failUnlessAlmostEqual(self.volume, 0.1)

    def test_add(self):
        v = Volume(self)
        v.set_value(0.5)
        v += 0.1
        self.failUnlessAlmostEqual(self.volume, 0.6)

    def test_sub(self):
        v = Volume(self)
        v.set_value(0.5)
        v -= 0.1
        self.failUnlessAlmostEqual(self.volume, 0.4)

    def test_add_boundry(self):
        v = Volume(self)
        v.set_value(0.95)
        v += 0.1
        self.failUnlessAlmostEqual(self.volume, 1.0)

    def test_sub_boundry(self):
        v = Volume(self)
        v.set_value(0.05)
        v -= 0.1
        self.failUnlessAlmostEqual(self.volume, 0.0)
add(TVolume)
