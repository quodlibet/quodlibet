from tests import TestCase, add

from qltk.downloader import DownloadWindow

class TDownloadWindow(TestCase):
    def setUp(self):
        self.win = DownloadWindow()

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
add(TDownloadWindow)
