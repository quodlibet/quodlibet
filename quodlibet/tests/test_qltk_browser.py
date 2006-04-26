from tests import TestCase, add

from qltk.browser import LibraryBrowser

class TLibraryBrowser(TestCase):
    def test_ctr(self):
        from qltk.watcher import SongWatcher
        from browsers.search import EmptyBar
        LibraryBrowser(EmptyBar, SongWatcher()).destroy()
add(TLibraryBrowser)
