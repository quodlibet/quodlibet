from tests import TestCase, add

from qltk.getstring import GetStringDialog

class TGetStringDialog(TestCase):
    def setUp(self):
        self.gsd1 = GetStringDialog(None, "title", "enter a string")
        self.gsd2 = GetStringDialog(None, "title", "enter a string",
                                    options=["1", "2"])
    def test_ctr(self): pass
    def tearDown(self):
        self.gsd1.destroy()
        self.gsd2.destroy()
add(TGetStringDialog)
