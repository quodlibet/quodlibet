from tests import TestCase, add
from quodlibet.qltk.views import AllTreeView

class THintedTreeView(TestCase):
    def setUp(self): self.c = AllTreeView()
    def tearDown(self): self.c.destroy()
add(THintedTreeView)
