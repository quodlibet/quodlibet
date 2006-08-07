from tests import TestCase, add

from qltk.browser import LibraryBrowser

class TLibraryBrowser(TestCase):
    def test_ctr(self):
        from library import SongLibrary
        from browsers.search import EmptyBar
        LibraryBrowser(EmptyBar, SongLibrary()).destroy()
add(TLibraryBrowser)
