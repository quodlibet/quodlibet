from tests import TestCase

from quodlibet.qltk.sortdialog import SortDialog


class TSortDialog(TestCase):
    def test(self):
        SortDialog(None).destroy()
