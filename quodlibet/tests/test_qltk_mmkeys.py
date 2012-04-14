from tests import TestCase, add

import gtk
from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.mmkeys_ import init

class TMmKeys(TestCase):
    def setUp(self):
        self.win = gtk.Window()
        self.keys = init(self.win, NullPlayer())
    def test_ctr(self): pass
    def tearDown(self):
        self.win.destroy()
add(TMmKeys)
