from tests import TestCase, add

from quodlibet.qltk.browser import LibraryBrowser

class TLibraryBrowser(TestCase):
    def test_ctr(self):
        from quodlibet.library import SongLibrary
        from quodlibet.browsers.search import EmptyBar
        LibraryBrowser(EmptyBar, SongLibrary()).destroy()
add(TLibraryBrowser)
