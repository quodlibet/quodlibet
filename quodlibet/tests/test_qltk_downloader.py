from tests import TestCase, add

from quodlibet.qltk.downloader import DownloadWindow
import quodlibet.config

class TDownloadWindow(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.win = DownloadWindow()

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        quodlibet.config.quit()
add(TDownloadWindow)
