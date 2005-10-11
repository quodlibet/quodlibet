from tests import TestCase, add
import os, gtk, const
from formats._audio import AudioFile as AF

from widgets import PlayList, FolderChooser, CountManager, FSInterface, PluginWindow, PreferencesWindow, TrayIcon
import qltk

class TFSInterface(TestCase):
    from formats._audio import AudioFile as AF
    def setUp(self):
        self.w = qltk.SongWatcher()
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

class TFolderChooser(TestCase):
    def test_init_nodir(self):
        f = FolderChooser(None, "A file chooser")
        self.assertEqual(f.get_current_folder(), os.path.realpath("."))
        f.destroy()

    def test_init_dir(self):
        f = FolderChooser(None, "A file chooser", "/home")
        self.assertEqual(f.get_current_folder(), "/home")
        f.destroy()

add(TFolderChooser)

class TCountManager(TestCase):
    def setUp(self):
        self.w = qltk.SongWatcher()
        self.s1 = AF({"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10})
        self.s2 = AF({"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10})
        self.cm = CountManager(self.w, self)
        self.current = None

    def do(self):
        while gtk.events_pending(): gtk.main_iteration()

    def test_play(self):
        self.w.song_ended(self.s1, False)
        self.do()
        import time; t = time.time()
        self.assertEquals(self.s1["~#playcount"], 1)
        self.assertEquals(self.s1["~#skipcount"], 0)
        self.failUnless(t - self.s1["~#lastplayed"] <= 1)

    def test_skip(self):
        self.w.song_ended(self.s1, True)
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 1)
        self.failUnless(self.s1["~#lastplayed"], 10)

    def test_restart(self):
        self.current = self.s1
        self.w.song_ended(self.s1, True)
        self.do()
        self.assertEquals(self.s1["~#playcount"], 0)
        self.assertEquals(self.s1["~#skipcount"], 0)

    def tearDown(self):
        self.w.destroy()

add(TCountManager)

class TPluginWindow(TestCase):
    def test_create(self):
        from plugins import PluginManager
        from widgets import SongList
        SongList.pm = PluginManager(qltk.SongWatcher(), [])
        w = PluginWindow(None)
        w.destroy()
        del(SongList.pm)

add(TPluginWindow)

class TPreferencesWindow(TestCase):
    def test_create(self):
        w = PreferencesWindow(None)
        w.destroy()
add(TPreferencesWindow)

class TTrayIcon(TestCase):
    def setUp(self):
        self.ti = TrayIcon(None, {})

    def test_enabled(self):
        self.failIf(self.ti.enabled)
add(TTrayIcon)

