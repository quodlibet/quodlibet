from unittest import TestCase
from tests import registerCase

from player import PlaylistPlayer

class Volume(TestCase):
    def setUp(self):
        self.p = PlaylistPlayer('fakesink')

    def test_setget(self):
        for i in [0.0, 1.2, 0.24, 1.0, 0.9]:
            self.p.volume = i
            self.failUnlessAlmostEqual(self.p.volume, i)

    def tearDown(self):
        self.p.quit()

registerCase(Volume)
