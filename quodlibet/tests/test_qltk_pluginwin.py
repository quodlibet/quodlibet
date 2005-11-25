from tests import add, TestCase
from qltk.pluginwin import PluginWindow
from plugins import PluginManager
from qltk.watcher import SongWatcher

class TPluginWindow(TestCase):
    def setUp(self):
        self.win = PluginWindow(None, PluginManager(SongWatcher(), []))

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
add(TPluginWindow)
