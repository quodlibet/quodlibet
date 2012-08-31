from tests import TestCase, add

from quodlibet.qltk.browser import LibraryBrowser
import quodlibet.config

class TLibraryBrowser(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def test_ctr(self):
        from quodlibet.library import SongLibrary
        from quodlibet.browsers.search import EmptyBar
        win = LibraryBrowser(EmptyBar, SongLibrary())
        win.browser.emit("songs-selected", [], False)
        win.songlist.get_selection().emit("changed")
        win.destroy()

    def tearDown(self):
        quodlibet.config.quit()

add(TLibraryBrowser)
