from unittest import TestCase
from tests import registerCase, Mock
import os, gtk
import __builtin__
__builtin__.__dict__['_'] = lambda a: a
import widgets
from widgets import EmptyBar, SearchBar, PlayList
from properties import VALIDATERS
from efwidgets import DirectoryTree
import library; library.init("dummyfn")
import config
import qltk

class TestDirTree(TestCase):
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

class StopAfterTest(TestCase):
    def test_active(self):
        w = widgets.MainWindow.StopAfterMenu()
        self.failIf(w.active)
        for b in [True, False, True, False, False]:
            w.active = b
            if b: self.failUnless(w.active)
            else: self.failIf(w.active)
        w.destroy()

class SongWatcher(TestCase):
    def setUp(self):
        self.watcher = qltk.SongWatcher()

    def __changed(self, watcher, song, expected):
        self.failUnlessEqual(expected.pop(0), song)

    def __test_signal(self, sig):
        expected = range(5)
        self.watcher.connect(sig, self.__changed, expected)
        map(getattr(self.watcher, sig), range(5))
        while gtk.events_pending(): gtk.main_iteration()
        self.failIf(expected)

    def test_changed(self): self.__test_signal('changed')
    def test_removed(self): self.__test_signal('removed')
    def test_missing(self): self.__test_signal('missing')

    def __test_started_cb(self, watcher, song):
        self.failUnlessEqual(watcher.time[0], 0)
        self.failUnlessEqual(watcher.song, song)
        if song: self.failUnlessEqual(watcher.time[1], song["~#length"]*1000)
        else: self.failUnlessEqual(watcher.time[1], 1)
        self.__count += 1

    def test_started(self):
        self.__count = 0
        self.watcher.connect('song-started', self.__test_started_cb)
        self.watcher.song_started(None)
        while gtk.events_pending(): gtk.main_iteration()
        self.watcher.song_started({"~#length": 10})
        while gtk.events_pending(): gtk.main_iteration()
        self.watcher.song_started(None)
        while gtk.events_pending(): gtk.main_iteration()
        self.watcher.song_started({"~#length": 12})
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(4, self.__count)

    def __refresh_cb(self, watcher): self.__refreshed = True
    def test_refresh(self):
        self.__refreshed = False
        self.watcher.connect('refresh', self.__refresh_cb)
        self.watcher.refresh()
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnless(self.__refreshed)

    def __ended_cb(self, watcher, song, stopped):
        if song & 1: self.failIf(stopped)
        else: self.failUnless(stopped)
        watcher.song = song

    def test_ended(self):
        self.watcher.connect('song-ended', self.__ended_cb)
        self.watcher.song_ended(1, False)
        self.watcher.song_ended(2, True)
        self.watcher.song_ended(3, False)
        self.watcher.song_ended(4, True)
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(4, self.watcher.song)

    def __paused_cb(self, watcher): self.__paused += 1
    def __unpaused_cb(self, watcher): self.__unpaused += 1
    def test_paused(self):
        self.__paused = 0
        self.__unpaused = 0
        self.watcher.connect('paused', self.__paused_cb)
        self.watcher.connect('unpaused', self.__unpaused_cb)
        for i in range(4): self.watcher.set_paused(True)
        for i in range(6): self.watcher.set_paused(False)
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(4, self.__paused)
        self.failUnlessEqual(6, self.__unpaused)

    def tearDown(self):
        self.watcher.destroy()

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

registerCase(TestDirTree)
registerCase(StopAfterTest)
registerCase(SongWatcher)
registerCase(ValidaterTests)
