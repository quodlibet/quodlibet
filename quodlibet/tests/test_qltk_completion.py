from tests import TestCase, add

import gtk

from quodlibet import config
from quodlibet.library import SongLibrary
from quodlibet.qltk.completion import EntryWordCompletion, LibraryTagCompletion
from quodlibet.qltk.completion import LibraryValueCompletion

class TEntryWordCompletion(TestCase):
    def test_ctr(self):
        w = EntryWordCompletion()
        e = gtk.Entry()
        e.set_completion(w)
        self.failUnlessEqual(w.get_entry(), e)
        self.failUnlessEqual(e.get_completion(), w)
        e.destroy()
add(TEntryWordCompletion)

class TLibraryTagCompletion(TestCase):
    def test_ctr(self):
        w = LibraryTagCompletion(SongLibrary())
        e = gtk.Entry()
        e.set_completion(w)
        self.failUnlessEqual(w.get_entry(), e)
        self.failUnlessEqual(e.get_completion(), w)
        e.destroy()
add(TLibraryTagCompletion)

class TLibraryValueCompletion(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_ctr(self):
        w = LibraryValueCompletion("artist", SongLibrary())
        e = gtk.Entry()
        e.set_completion(w)
        self.failUnlessEqual(w.get_entry(), e)
        self.failUnlessEqual(e.get_completion(), w)
        e.destroy()
add(TLibraryValueCompletion)
