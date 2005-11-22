from tests import TestCase, add
from player import PlaylistPlayer
from qltk.volume import Volume

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

class SliderVolume(TestCase):
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

add(SliderVolume)

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
