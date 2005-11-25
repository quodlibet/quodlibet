import gtk
from tests import add, TestCase
from qltk.watcher import SongWatcher

class TSongWatcher(TestCase):
    def setUp(self):
        self.watcher = SongWatcher()

    def __changed(self, watcher, song, expected):
        self.failUnlessEqual(expected.pop(0), song)

    def __test_signal(self, sig):
        expected = [[0], [1], [2], [3], [4], [5]]
        self.watcher.connect(sig, self.__changed, expected)
        map(getattr(self.watcher, sig), list(expected))
        while gtk.events_pending(): gtk.main_iteration()
        self.failIf(expected)

    def test_changed(self): self.__test_signal('changed')
    def test_removed(self): self.__test_signal('removed')

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

add(TSongWatcher)

