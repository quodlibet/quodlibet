from tests import add, TestCase
from qltk.views import HintedTreeView

class THintedTreeView(TestCase):
    def setUp(self): self.c = HintedTreeView()
    def tearDown(self): self.c.destroy()
add(THintedTreeView)
