from tests import TestCase, add

from quodlibet import config
from quodlibet import widgets

from quodlibet.browsers.paned import PanedBrowser
from quodlibet.formats._audio import AudioFile
from quodlibet.library import SongLibrary

SONGS = [
    AudioFile({"title": "one", "artist": "piman", "~filename": "/dev/null"}),
    AudioFile({"title": "two", "artist": "mu", "~filename": "/dev/zero"}),
    AudioFile({"title": "three", "artist": "boris", "~filename": "/bin/ls"})
    ]
SONGS.sort()

class TPanedBrowser(TestCase):
    Bar = PanedBrowser

    def setUp(self):
        config.init()
        config.set("browsers", "panes", "artist")
        library = SongLibrary()
        PanedBrowser.init(library)
        for af in SONGS:
            af.sanitize()
        library.add(SONGS)
        self.bar = self.Bar(library, False)

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
        config.quit()
add(TPanedBrowser)
