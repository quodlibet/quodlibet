from tests import add, TestCase
from qltk.prefs import PreferencesWindow

class TPreferencesWindow(TestCase):
    def setUp(self):
        self.win = PreferencesWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
add(TPreferencesWindow)
