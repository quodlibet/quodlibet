from unittest import TestCase
from tests import registerCase, Mock
import os, gtk
import widgets
from widgets import DirectoryTree, EmptyBar, SearchBar, PlayList

import config

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

class TestEmptyBar(TestCase):
    def setUp(self):
        self._bar = EmptyBar(self._check_cb)

    def _check_cb(self, query, sort):
        self.failUnlessEqual(query, self._expected)
        del(self._expected)

    def test_initial(self):
        self._bar.set_text("a test")
        self._expected = "a test"
        self._bar.activate()

    def test_restore(self):
        self._bar.set_text("a test")
        self._bar.save()
        self._bar.set_text("not a test")
        self._bar.restore()
        self._expected = "a test"
        self._bar.activate()

    def test_can_filter(self):
        for key in ["artist", "album", "dummy", "~#track", "woo~bar~fake"]:
            self.failUnless(self._bar.can_filter(key))

    # not the best tests, but until we get a more structured way of
    # comparing queries they'll do...
    def test_filter_num(self):
        self._expected = "|(#(track = 3), #(track = 4))"
        self._bar.filter("~#track", [3, 4])

    def test_filter_text(self):
        self._expected = "artist = |('some guy'c)"
        self._bar.filter("artist", ["some guy"])

    def test_filter_text_multi(self):
        self._expected = "artist = |('A'c, 'B'c)"
        self._bar.filter("artist", ["A", "B"])

    def test_filter_text_escape(self):
        self._expected = "artist = |('A\\''c)"
        self._bar.filter("artist", ["A'"])

    def tearDown(self):
        self._bar.destroy()

# SearchBar shares most of its code with EmptyBar, except for its
# implementation of activate(). So all we need to test is set_text and
# save/restore.
class TestSearchBar(TestCase):
    def setUp(self):
        self._bar = SearchBar(self._check_cb)
    
    def _check_cb(self, query, sort):
        self.failUnlessEqual(query, self._expected)
        del(self._expected)

    def test_initial(self):
        self._bar.set_text("a test")
        self._expected = "a test"
        self._bar.activate()

    def test_savenosave(self):
        bar = SearchBar(self._check_cb, save=False)
        bar.set_text("a test")
        bar.save()
        bar.set_text("another test")
        self._expected = "another test"
        bar.activate()
        bar.restore()
        self._expected = "a test"
        bar.activate()
        bar.destroy()

    def test_restore(self):
        self._bar.set_text("a test")
        self._bar.save()
        self._bar.set_text("not a test")
        self._bar.restore()
        self._expected = "a test"
        self._bar.activate()

    def tearDown(self):
        self._bar.destroy()

class TestPlayList(TestCase):
    def test_normalize_safe(self):
        for string in ["", "foo", "bar", "a_title", "some_keys"]:
            self.failUnlessEqual(string, PlayList.normalize_name(string))

    def test_normalize_unsafe(self):
        for string in ["%%%", "bad_ string", "<woo>", "|%more%20&tests",
                       "% % % %", "   ", ":=)", "#!=", "mixed # strings",
                       "".join(PlayList.BAD)]:
            nstring = PlayList.normalize_name(string)
            self.failIfEqual(string, nstring)
            self.failUnlessEqual(string, PlayList.prettify_name(nstring))

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
        self.watcher = widgets.SongWatcher()

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

registerCase(TestDirTree)
registerCase(TestEmptyBar)
registerCase(TestSearchBar)
registerCase(TestPlayList)
registerCase(StopAfterTest)
registerCase(SongWatcher)

