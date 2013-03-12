from tests import TestCase, add

from quodlibet.qltk.prefs import PreferencesWindow
from quodlibet import config


class TPreferencesWindow(TestCase):

    def setUp(self):
        config.init()
        # Avoid warnings when running with empty config
        config.set_columns(["artist", "title"])
        self.win = PreferencesWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        config.quit()
add(TPreferencesWindow)
