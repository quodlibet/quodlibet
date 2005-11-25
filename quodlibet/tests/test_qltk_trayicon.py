import gtk
from tests import add, TestCase
from qltk.trayicon import TrayIcon
from qltk.watcher import SongWatcher
from player import PlaylistPlayer

class TTrayIcon(TestCase):
    def setUp(self):
        self.icon = TrayIcon(
            SongWatcher(), gtk.Window(), PlaylistPlayer('fakesink'))

    def test_not_enabled(self):
        self.failIf(self.icon.enabled)

    def tearDown(self):
        self.icon.destroy()
add(TTrayIcon)
