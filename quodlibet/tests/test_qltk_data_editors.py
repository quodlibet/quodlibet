from quodlibet import config
from tests import TestCase, add
from quodlibet.qltk.data_editors import MultiStringEditor


class TMultiStringEditor(TestCase):

    def setUp(self):
        config.init()

    def test_no_strings(self):
        mse = MultiStringEditor("title")
        self.failUnlessEqual(mse.get_strings(), [])
        self.failUnlessEqual(mse.get_title(), "title")
        mse.destroy()

    def test_defaulting(self):
        defaults = ["one", "two three"]
        mse = MultiStringEditor("title", defaults)
        self.failUnlessEqual(mse.get_strings(), defaults)
        mse.destroy()

    def tearDown(self):
        config.quit()

add(TMultiStringEditor)
