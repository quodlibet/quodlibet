from tests import TestCase, add

from quodlibet import config

from quodlibet.browsers.paned import PanedBrowser, PanePattern
from quodlibet.formats._audio import AudioFile
from quodlibet.util.collection import Collection
from quodlibet.library import SongLibrary, SongLibrarian

SONGS = [
    AudioFile({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
    AudioFile({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
    ]
SONGS.sort()

ALBUM = Collection()
ALBUM.songs = SONGS


class TPanedBrowser(TestCase):
    Bar = PanedBrowser

    def setUp(self):
        config.init()
        config.set("browsers", "panes", "artist")
        library = SongLibrary()
        library.librarian = SongLibrarian()
        PanedBrowser.init(library)
        for af in SONGS:
            af.sanitize()
        library.add(SONGS)
        self.bar = self.Bar(library, False)

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter_tag(key))
        self.failUnless(self.bar.can_filter("artist"))

    def test_filter_value(self):
        self.expected = [SONGS[0]]
        self.bar.filter("artist", ["boris"])

    def test_filter_notvalue(self):
        self.expected = SONGS[1:3]
        self.bar.filter("artist", ["notvalue", "mu", "piman"])

    def tearDown(self):
        self.bar.destroy()
        config.quit()
add(TPanedBrowser)


class TPanePattern(TestCase):
    def test_tag(self):
        p = PanePattern("title")
        self.failUnlessEqual(p.title, "Title")
        self.failUnlessEqual(p.tags, set(["title"]))

        self.failUnlessEqual(p.format(SONGS[0]), ["three"])
        self.failUnless("3" in p.format_display(ALBUM))
        self.failIf(p.has_markup)

    def test_numeric(self):
        p = PanePattern("~#lastplayed")
        self.failUnlessEqual(p.title, "Last Played")
        self.failUnlessEqual(p.tags, set(["~#lastplayed"]))

        self.failUnlessEqual(p.format(SONGS[0]), ["0"])
        self.failIf(p.has_markup)

    def test_tied(self):
        p = PanePattern("~title~artist")
        self.failUnlessEqual(p.title, "Title / Artist")
        self.failUnlessEqual(p.tags, set(["title", "artist"]))

        self.failUnlessEqual(p.format(SONGS[0]), ["three - boris"])
        self.failIf(p.has_markup)

    def test_pattern(self):
        p = PanePattern("<foo>")
        self.failUnlessEqual(p.title, "Foo")
        self.failUnlessEqual(p.tags, set(["foo"]))
        self.failUnless(p.has_markup)

    def test_condition(self):
        p = PanePattern("<foo|a <bar>|quux>")
        self.failUnlessEqual(p.title, "a Bar")
        self.failUnlessEqual(p.tags, set(["bar"]))
        self.failUnless(p.has_markup)

    def test_group(self):
        p = PanePattern("a\:b:<title>")
        self.failUnlessEqual(p.title, "A:B")
        self.failUnlessEqual(set(p.format_display(ALBUM).split(", ")),
                             set(["one", "two", "three"]))

        p = PanePattern("foo:~#lastplayed")
        self.failUnlessEqual(p.format_display(ALBUM), "0")

        p = PanePattern("foo:title")
        self.failUnlessEqual(set(p.format_display(ALBUM).split(", ")),
                             set(["one", "two", "three"]))

add(TPanePattern)
