from tests import TestCase, add

from qltk.delete import DeleteDialog

class TDeleteDialog(TestCase):
    def setUp(self):
        self.win = DeleteDialog(None, ["/dev/null"])

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
add(TDeleteDialog)
