from tests import TestCase, add
from quodlibet.qltk.views import AllTreeView
import quodlibet.config

class THintedTreeView(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.c = AllTreeView()

    def test_exists(self):
        self.failUnless(self.c)

    def tearDown(self):
        self.c.destroy()
add(THintedTreeView)
