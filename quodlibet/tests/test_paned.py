import gobject, gtk
from tests import TestCase, add

import config
import widgets
import browsers.paned
from browsers.paned import PanedBrowser
from formats._audio import AudioFile as AF

import __builtin__
__builtin__.__dict__['_'] = lambda a: a

from library import Library

SONGS = [AF({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
         AF({"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
         AF({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
         ]
SONGS.sort()

class TPanedBrowser(TestCase):
    Bar = PanedBrowser
    def setUp(self):
        import qltk
        config.set("browsers", "panes", "artist")
        widgets.library = browsers.paned.library = Library()
        from widgets import widgets as ws
        ws.watcher = qltk.SongWatcher()
        for af in SONGS:
            af.sanitize()
            browsers.paned.library.add_song(af)
        self.bar = self.Bar(ws.watcher, False)
        self.bar.connect('songs-selected', self._expected)
        while gtk.events_pending(): gtk.main_iteration()

    def _expected(self, bar, songs, sort):
        songs.sort()
        self.failUnlessEqual(self.expected, songs)
        self.expected = None

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("artist"))

    def test_dynamic(self):
        self.failUnless(self.bar.dynamic(SONGS[0]))

    def test_filter_value(self):
        self.expected = [SONGS[0]]
        self.bar.filter("artist", ["boris"])
        self.failUnless(self.expected is None)

    def test_filter_notvalue(self):
        self.expected = SONGS[1:3]
        self.bar.filter("artist", ["notvalue", "mu", "piman"])
        self.failUnless(self.expected is None)

    def test_saverestore(self):
        self.expected = [SONGS[0]]
        self.bar.filter("artist", ["boris"])
        self.failUnless(self.expected is None)
        self.bar.save()
        self.expected = list(SONGS)
        self.bar.filter("artist", ["boris", "piman", "mu"])
        self.failUnless(self.expected is None)
        self.expected = [SONGS[0]]
        self.bar.restore()
        self.failUnless(self.expected is None)

    def tearDown(self):
        self.bar.destroy()
        widgets.library = browsers.search.library = None
        from widgets import widgets as ws
        ws.watcher.destroy()
        del(ws.watcher)
add(TPanedBrowser)
