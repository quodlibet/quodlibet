from tests import TestCase, add

from quodlibet.qltk.pluginwin import PluginWindow
import quodlibet.config
import quodlibet.plugins

class TPluginWindow(TestCase):
    def setUp(self):
        quodlibet.plugins.init()
        quodlibet.config.init()
        self.win = PluginWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        quodlibet.plugins.quit()
        quodlibet.config.quit()
add(TPluginWindow)
