from unittest import TestCase
from tests import registerCase
import os, gtk, const
from browsers.search import EmptyBar, SearchBar
from properties import VALIDATERS
from efwidgets import DirectoryTree

from widgets import PlayList, FileChooser, CountManager, FSInterface, PluginWindow, PreferencesWindow
import qltk

class TFSInterface(TestCase):
    from formats.audio import AudioFile as AF
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

registerCase(TFSInterface)

class TFileChooser(TestCase):
    def test_init_nodir(self):
        f = FileChooser(None, "A file chooser")
        self.assertEqual(f.get_current_folder(), os.path.realpath("."))
        f.destroy()

    def test_init_dir(self):
        f = FileChooser(None, "A file chooser", "/home")
        self.assertEqual(f.get_current_folder(), "/home")
        f.destroy()

registerCase(TFileChooser)

class TCountManager(TestCase):
    def setUp(self):
        self.w = qltk.SongWatcher()
        self.s1 = {"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10}
        self.s2 = {"~#playcount": 0, "~#skipcount": 0, "~#lastplayed": 10}
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

registerCase(TCountManager)

class TPluginWindow(TestCase):
    def test_create(self):
        from plugins import PluginManager
        from widgets import SongList
        SongList.pm = PluginManager(qltk.SongWatcher(), [])
        w = PluginWindow(None)
        w.destroy()
        del(SongList.pm)

registerCase(TPluginWindow)

class TPreferencesWindow(TestCase):
    def test_create(self):
        w = PreferencesWindow(None)
        w.destroy()

registerCase(TPreferencesWindow)

class TDirectoryTree(TestCase):
    def test_initial(self):
        for path in ["/", "/home", os.environ["HOME"], "/usr/bin"]:
            dirlist = DirectoryTree(path)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

    def test_bad_initial(self):
        for path in ["/", os.environ["HOME"]]:
            newpath = os.path.join(path, "bin/file/does/not/exist")
            dirlist = DirectoryTree(newpath)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

    def test_bad_go_to(self):
         newpath = "/woooooo/bar/fun/broken"
         dirlist = DirectoryTree("/")
         dirlist.go_to(newpath)
         dirlist.destroy()

class ValidaterTests(TestCase):
    def validate(self, key, values):
        for val in values: self.failUnless(VALIDATERS[key][0](val))
    def invalidate(self, key, values):
        for val in values: self.failIf(VALIDATERS[key][0](val))

    def test_date_valid(self):
        self.validate("date", ["2002-10-12", "2000", "1200-10", "0000-00-00"])
    def test_date_invalid(self):
        self.invalidate(
            "date", ["200", "date-or-no", "", "2000-00-00-00"])

    def test_gain_valid(self):
        gains = ["2.12 dB", "99. dB", "-1.11 dB", "-0.99 dB", "0 dB"]
        self.validate('replaygain_track_gain', gains)
        self.validate('replaygain_album_gain', gains)
    def test_gain_invalid(self):
        gains = ["12.12", "hooray", "", "dB dB"]
        self.invalidate('replaygain_track_gain', gains)
        self.invalidate('replaygain_album_gain', gains)

    def test_peak_valid(self):
        peaks = ["12.12", "100", "0.999", "123.145"]
        self.validate('replaygain_track_peak', peaks)
        self.validate('replaygain_album_peak', peaks)
    def test_peak_invalid(self):
        peaks = ["", "100 dB", "woooo", "12.12.12"]
        self.invalidate('replaygain_track_peak', peaks)
        self.invalidate('replaygain_album_peak', peaks)

registerCase(TDirectoryTree)
registerCase(ValidaterTests)
