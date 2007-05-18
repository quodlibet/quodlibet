from tests import TestCase, add

import gtk

from quodlibet import widgets
import quodlibet.browsers.search

from quodlibet.browsers.search import EmptyBar, SearchBar
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary

SONGS = [AudioFile(
    {"title": "one", "artist": "piman", "~filename": "/dev/null"}),
         AudioFile(
    {"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
         AudioFile(
    {"title": "three", "artist": "boris", "~filename": "/bin/ls"})
         ]
SONGS.sort()

class TEmptyBar(TestCase):
    Bar = EmptyBar
    def setUp(self):
        quodlibet.browsers.search.library = SongLibrary()
        for af in SONGS:
            af.sanitize()
        quodlibet.browsers.search.library.add(SONGS)
        self.bar = self.Bar(quodlibet.browsers.search.library, False)
        self.bar.connect('songs-selected', self._expected)

    def _expected(self, bar, songs, sort):
        songs.sort()
        self.failUnlessEqual(self.expected, songs)
        self.expected = None

    def _do(self):
        self.bar.activate()
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnless(self.expected is None)

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failUnless(self.bar.can_filter(key))

    def test_default_none(self):
        self.expected = None
        self._do()

    def test_empty_is_all(self):
        self.bar.set_text("")
        self.expected = list(SONGS)
        self._do()

    def test_dynamic(self):
        self.failUnless(self.bar.dynamic(SONGS[0]))
        self.bar.set_text("this does not match any song")
        self.expected = []
        self.bar.activate()
        self.failIf(self.bar.dynamic(SONGS[0]))

    def test_filter(self):
        self.expected = [SONGS[1]]
        self.bar.filter("title", ["two"])

    def test_filter_notvalue(self):
        self.expected = SONGS[1:3]
        self.bar.filter("artist", ["notvalue", "mu", "piman"])

    def test_filter_none(self):
        self.expected = []
        self.bar.filter("title", ["not a value"])

    def test_filter_numeric(self):
        self.expected = list(SONGS)
        self.bar.filter("~#length", [0])

    def test_saverestore(self):
        self.bar.set_text("title = %s" % SONGS[0]["title"])
        self.expected = [SONGS[0]]
        self._do()
        self.bar.save()
        self.bar.set_text("")
        self.expected = list(SONGS)
        self._do()
        self.bar.restore()
        self.expected = [SONGS[0]]
        self._do()

    def tearDown(self):
        self.bar.destroy()
        quodlibet.browsers.search.library.destroy()
add(TEmptyBar)

class TSearchBar(TEmptyBar):
    Bar = SearchBar
    def setUp(self):
        super(TSearchBar, self).setUp()

    def test_ctr(self): pass

    def tearDown(self):
        super(TSearchBar, self).tearDown()
add(TSearchBar)
