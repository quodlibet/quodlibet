from tests import TestCase, add

import gtk

import quodlibet.browsers.search
import quodlibet.config

from quodlibet.browsers.search import EmptyBar, SearchBar
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary, SongLibrarian

# Don't sort yet, album_key makes it complicated...
SONGS = [AudioFile({
                "title": "one",
                "artist": "piman",
                "~filename": "/dev/null"}),
         AudioFile({
                "title": "two",
                "artist": "mu",
                "~filename": "/dev/zero"}),
         AudioFile({
                "title": "three",
                "artist": "boris",
                "~filename": "/bin/ls"}),
         AudioFile({
                "title": "four",
                "artist": "random",
                "album": "don't stop",
                "labelid": "65432-1",
                "~filename": "/dev/random"}),
         AudioFile({
                "title": "five",
                "artist": "shell",
                "album": "don't stop",
                "labelid": "12345-6",
                "~filename": "/dev/sh"})]

class TEmptyBar(TestCase):
    Bar = EmptyBar
    def setUp(self):
        quodlibet.config.init()
        quodlibet.browsers.search.library = SongLibrary()
        quodlibet.browsers.search.library.librarian = SongLibrarian()
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
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnless(self.expected is None)

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failUnless(self.bar.can_filter(key))

    def test_empty_is_all(self):
        self.bar.filter_text("")
        self.expected = list(sorted(SONGS))
        self._do()

    def test_dynamic(self):
        self.failUnless(self.bar.dynamic(SONGS[0]))
        self.bar.filter_text("this does not match any song")
        self.expected = []
        self.failIf(self.bar.dynamic(SONGS[0]))

    def test_filter(self):
        self.expected = [SONGS[1]]
        self.bar.filter("title", ["two"])

    def test_filter_again(self):
        self.expected = sorted(SONGS[3:5])
        self.bar.filter("album", ["don't stop"])

    def test_filter_notvalue(self):
        self.expected = sorted(SONGS[0:2])
        self.bar.filter("artist", ["notvalue", "mu", "piman"])

    def test_filter_none(self):
        self.expected = []
        self.bar.filter("title", ["not a value"])

    def test_filter_album_by_labelid(self):
        self.expected = [SONGS[3]]
        self.bar.filter("labelid", [("65432-1")])

    def test_filter_numeric(self):
        self.expected = list(sorted(SONGS))
        self.bar.filter("~#length", [0])

    def test_saverestore(self):
        self.bar.filter_text("title = %s" % SONGS[0]["title"])
        self.expected = [SONGS[0]]
        self._do()
        self.bar.save()
        self.bar.filter_text("")
        self.expected = list(sorted(SONGS))
        self._do()
        self.bar.restore()
        self.expected = [SONGS[0]]
        self._do()

    def tearDown(self):
        self.bar.destroy()
        quodlibet.browsers.search.library.destroy()
        quodlibet.config.quit()
add(TEmptyBar)

class TSearchBar(TEmptyBar):
    Bar = SearchBar
add(TSearchBar)
