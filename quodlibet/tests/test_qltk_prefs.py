from tests import TestCase, add

from quodlibet.qltk.prefs import PreferencesWindow
import quodlibet.config

class TPreferencesWindow(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.win = PreferencesWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        quodlibet.config.quit()
add(TPreferencesWindow)
