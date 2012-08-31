from tests import TestCase, add

from quodlibet.qltk.sortdialog import SortDialog

class TSortDialog(TestCase):
    def test(self):
        SortDialog(None).destroy()

add(TSortDialog)
