from tests import TestCase, add
from player import PlaylistPlayer
from qltk.controls import Volume

class PlayerVolume(TestCase):
    def setUp(self):
        self.p = PlaylistPlayer('fakesink')

    def test_setget(self):
        for i in [0.0, 1.2, 0.24, 1.0, 0.9]:
            self.p.volume = i
            self.failUnlessAlmostEqual(self.p.volume, i)

    def tearDown(self):
        self.p.quit()
add(PlayerVolume)

class CombinedVolume(TestCase):
    def setUp(self):
        self.p = PlaylistPlayer('fakesink')
        self.v = Volume(self.p)

    def test_setget(self):
        for i in [0.0, 1.2, 0.24, 1.0, 0.9]:
            self.v.set_value(i)
            self.failUnlessAlmostEqual(self.p.volume, self.v.get_value())

    def tearDown(self):
        self.p.quit()
        self.v.destroy()
add(CombinedVolume)
