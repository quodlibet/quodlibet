from tests import TestCase, add

import gtk

from quodlibet.library import SongLibrary
from quodlibet.qltk.completion import EntryWordCompletion, LibraryTagCompletion

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
