from tests import add, TestCase
from qltk.pluginwin import PluginWindow

class TPluginWindow(TestCase):
    def setUp(self):
        self.win = PluginWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
add(TPluginWindow)
