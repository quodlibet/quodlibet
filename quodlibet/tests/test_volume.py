from tests import TestCase, add

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.controls import Volume
import quodlibet.config

class TVolume(TestCase):
    def setUp(self):
        quodlibet.config.init()
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
        quodlibet.config.quit()
add(TVolume)
