import gobject, gtk
from tests import TestCase, add

import widgets
import browsers.search
from browsers.search import EmptyBar, SearchBar
from formats._audio import AudioFile as AF

import __builtin__
__builtin__.__dict__['_'] = lambda a: a

from library import Library

SONGS = [AF({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
         AF({"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
         AF({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
         ]
SONGS.sort()

class TEmptyBar(TestCase):
    Bar = EmptyBar
    def setUp(self):
        widgets.library = browsers.search.library = Library()
        for af in SONGS:
            af.sanitize()
            browsers.search.library.add_song(af)
        self.bar = self.Bar(False)
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
        widgets.library = browsers.search.library = None
add(TEmptyBar)

class TSearchBar(TEmptyBar):
    Bar = SearchBar
    def setUp(self):
        import qltk
        from widgets import widgets
        widgets.watcher = qltk.SongWatcher()
        super(TSearchBar, self).setUp()

    def test_initial_limit(self):
        self.failUnlessEqual(0, self.bar._limit.get_value_as_int())

    def test_limit_two(self):
        class dummy:
            # equal anything with length two, since it'll be random.
            def __eq__(self, other): return len(other) == 2
        self.expected = dummy()
        self.bar._limit.show()
        self.bar._limit.set_value(2)
        self.bar.set_text("")
        self._do()

    def tearDown(self):
        super(TSearchBar, self).tearDown()
        from widgets import widgets
        widgets.watcher.destroy()
        del(widgets.watcher)
add(TSearchBar)
