from tests import TestCase, add

import config
import widgets
import browsers.paned
from browsers.paned import PanedBrowser
from formats._audio import AudioFile as AF
from qltk.watcher import SongWatcher

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
        config.set("browsers", "panes", "artist")
        widgets.library = browsers.paned.library = Library()
        widgets.watcher = SongWatcher()
        for af in SONGS:
            af.sanitize()
            browsers.paned.library.add_song(af)
        self.bar = self.Bar(widgets.watcher, False)

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("artist"))

    def test_dynamic(self):
        self.failUnless(self.bar.dynamic(SONGS[0]))

    def test_filter_value(self):
        self.expected = [SONGS[0]]
        self.bar.filter("artist", ["boris"])

    def test_filter_notvalue(self):
        self.expected = SONGS[1:3]
        self.bar.filter("artist", ["notvalue", "mu", "piman"])

    def tearDown(self):
        self.bar.destroy()
        widgets.library = browsers.search.library = Library()
        widgets.watcher.destroy()
        del(widgets.watcher)
add(TPanedBrowser)
