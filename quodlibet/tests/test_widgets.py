from tests import TestCase, add
import os, gtk, const
from formats._audio import AudioFile as AF

from qltk.remote import FSInterface
from qltk.pluginwin import PluginWindow
from qltk.prefs import PreferencesWindow
import qltk
from qltk.watcher import SongWatcher

class TFSInterface(TestCase):
    from formats._audio import AudioFile as AF
    def setUp(self):
        self.w = SongWatcher()
        self.fs = FSInterface(self.w)

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_init(self):
        self.do()
        self.failUnless(os.path.exists(const.PAUSED))
        self.failIf(os.path.exists(const.CURRENT))

    def test_start(self):
        self.w.song_started(self.AF({"woo": "bar", "~#length": 10}))
        self.do()
        self.failUnless("woo=bar\n" in file(const.CURRENT).read())

    def test_pause(self):
        for b in [True, False, True, True, False, True]:
            self.w.set_paused(b); self.do()
            self.failUnlessEqual(os.path.exists(const.PAUSED), b)

    def test_song_ended(self):
        self.w.song_started(self.AF({"woo": "bar", "~#length": 10}))
        self.do()
        self.w.song_ended({}, False)
        self.do()
        self.failIf(os.path.exists(const.CURRENT))

    def tearDown(self):
        self.w.destroy()
        try: os.unlink(const.PAUSED)
        except EnvironmentError: pass
        try: os.unlink(const.CURRENT)
        except EnvironmentError: pass

add(TFSInterface)

class TPluginWindow(TestCase):
    def test_create(self):
        from plugins import PluginManager
        from widgets import SongList
        w = PluginWindow(None, PluginManager(SongWatcher(), []))
        w.destroy()

add(TPluginWindow)

class TPreferencesWindow(TestCase):
    def test_create(self):
        w = PreferencesWindow(None)
        w.destroy()
add(TPreferencesWindow)
