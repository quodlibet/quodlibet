from tests import TestCase, add

import gtk

from library import SongLibrary
from qltk.completion import EntryWordCompletion, LibraryTagCompletion

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
