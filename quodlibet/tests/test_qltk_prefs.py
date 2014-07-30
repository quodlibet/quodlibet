from tests import TestCase

from quodlibet.qltk.prefs import PreferencesWindow
from quodlibet.qltk.songlist import set_columns
from quodlibet import config


class TPreferencesWindow(TestCase):

    def setUp(self):
        config.init()
        # Avoid warnings when running with empty config
        set_columns(["artist", "title"])
        self.win = PreferencesWindow(None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        config.quit()
