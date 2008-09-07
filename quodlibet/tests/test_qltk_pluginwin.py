from tests import TestCase, add

from quodlibet.qltk.pluginwin import PluginWindow
import quodlibet.config

class TPluginWindow(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.win = PluginWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        quodlibet.config.quit()
add(TPluginWindow)
