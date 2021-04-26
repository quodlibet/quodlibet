# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from tests import TestCase, run_gtk_loop
from quodlibet.util import connect_obj
from quodlibet.library import SongLibrarian, SongFileLibrary
from quodlibet.library.base import Library
from quodlibet.library.librarians import Librarian
from tests.test_library_libraries import Fake, Frange, FakeSongFile, FSrange


class TLibrarian(TestCase):
    Fake = Fake
    Frange = staticmethod(Frange)
    Librarian = Librarian
    Library = Library

    def setUp(self):
        self.librarian = self.Librarian()
        self.Library.librarian = self.librarian
        self.lib1 = self.Library("One")
        self.lib2 = self.Library("Two")

        self.added_1 = []
        self.changed_1 = []
        self.removed_1 = []
        self.added_2 = []
        self.changed_2 = []
        self.removed_2 = []
        self.added = []
        self.changed = []
        self.removed = []

        connect_obj(self.lib1, 'added', list.extend, self.added_1)
        connect_obj(self.lib1, 'changed', list.extend, self.changed_1)
        connect_obj(self.lib1, 'removed', list.extend, self.removed_1)
        connect_obj(self.lib2, 'added', list.extend, self.added_2)
        connect_obj(self.lib2, 'changed', list.extend, self.changed_2)
        connect_obj(self.lib2, 'removed', list.extend, self.removed_2)
        connect_obj(self.librarian, 'added', list.extend, self.added)
        connect_obj(self.librarian, 'changed', list.extend, self.changed)
        connect_obj(self.librarian, 'removed', list.extend, self.removed)

    def test_libraries(self):
        self.failUnlessEqual(len(self.librarian.libraries), 2)
        self.failUnless(self.lib1 in self.librarian.libraries.values())
        self.failUnless(self.lib2 in self.librarian.libraries.values())

    def test_register_at_instantiation(self):
        try:
            lib = self.Library("Three")
            self.failUnlessEqual(len(self.librarian.libraries), 3)
        finally:
            lib.destroy()

    def test_register_later(self):
        try:
            lib = self.Library()
            self.failUnlessEqual(len(self.librarian.libraries), 2)
            self.librarian.register(lib, "Three")
            self.failUnlessEqual(len(self.librarian.libraries), 3)
        finally:
            lib.destroy()

    def test_register_exists(self):
        self.failUnlessRaises(ValueError, self.Library, "Two")

    def test_unregister(self):
        self.lib2.destroy()
        self.failUnlessEqual(len(self.librarian.libraries), 1)
        self.failUnless(self.lib1 in self.librarian.libraries.values())
        self.failIf(self.lib2 in self.librarian.libraries.values())
        self.lib1.destroy()
        self.failUnlessEqual(len(self.librarian.libraries), 0)

    def test_added(self):
        self.lib1.add(self.Frange(12))
        self.lib2.add(self.Frange(12, 24))
        self.failUnlessEqual(sorted(self.added), self.Frange(24))

    def test_removed(self):
        self.lib1.add(self.Frange(12))
        self.lib2.add(self.Frange(12, 24))
        self.lib1.remove([self.Fake(9)])
        self.lib2.remove([self.Fake(16)])
        self.failUnlessEqual(self.removed, [self.Fake(9), self.Fake(16)])

    def test_changed(self):
        self.lib1.add(self.Frange(12))
        self.lib2.add(self.Frange(12, 24))
        self.librarian.changed(self.Frange(6, 18))
        run_gtk_loop()
        self.failUnlessEqual(sorted(self.changed), self.Frange(6, 18))
        self.failUnlessEqual(self.changed_1, self.Frange(6, 12))
        self.failUnlessEqual(self.changed_2, self.Frange(12, 18))

    def test___getitem__(self):
        self.lib1.add(self.Frange(12))
        self.lib2.add(self.Frange(12, 24))
        self.failUnlessEqual(self.librarian[10], 10)
        new = self.Fake(100)
        new.key = 200
        self.lib2.add([new])
        self.failUnlessEqual(self.librarian[200], new)

    def test___getitem___not_present(self):
        self.lib1.add(self.Frange(12))
        self.lib2.add(self.Frange(12, 24))
        self.lib2.remove([self.Fake(16)])
        self.failUnlessRaises(KeyError, self.librarian.__getitem__, 16)
        self.failUnlessRaises(KeyError, self.librarian.__getitem__, 99)

    def test___contains__(self):
        self.lib1.add(self.Frange(12))
        self.lib2.add(self.Frange(12, 24))
        new = self.Fake(100)
        new.key = 200
        self.lib1.add([new])
        for value in [1, 2, 15, 22, 200, new]:
            self.failUnless(value in self.librarian, "didn't find %d" % value)
        for value in [-1, 25, 50, 100]:
            self.failIf(value in self.librarian, "found %d" % value)

    def tearDown(self):
        self.Library.librarian = None
        self.lib1.destroy()
        self.lib2.destroy()
        self.librarian.destroy()


class TSongLibrarian(TLibrarian):
    Fake = FakeSongFile
    Frange = staticmethod(FSrange)
    Library = SongFileLibrary
    Librarian = SongLibrarian

    def test_tag_values(self):
        self.lib1.add(self.Frange(0, 30, 2))
        self.lib2.add(self.Frange(1, 30, 2))
        del(self.added[:])
        self.failUnlessEqual(
            sorted(self.librarian.tag_values(20)), list(range(20)))
        self.failUnlessEqual(sorted(self.librarian.tag_values(0)), [])
        self.failIf(self.changed or self.added or self.removed)

    def test_rename(self):
        new = self.Fake(10)
        new.key = 30
        self.lib1.add([new])
        self.lib2.add([new])
        self.librarian.rename(new, 20)
        run_gtk_loop()
        self.failUnlessEqual(new.key, 20)
        self.failUnless(new in self.lib1)
        self.failUnless(new in self.lib2)
        self.failUnless(new.key in self.lib1)
        self.failUnless(new.key in self.lib2)
        self.failUnlessEqual(self.changed_1, [new])
        self.failUnlessEqual(self.changed_2, [new])
        self.failUnless(new in self.changed)

    def test_rename_changed(self):
        new = self.Fake(10)
        self.lib1.add([new])
        changed = set()
        self.librarian.rename(new, 20, changed=changed)
        self.assertEqual(len(changed), 1)
        self.assertTrue(new in changed)

    def test_reload(self):
        new = self.Fake(10)
        self.lib1.add([new])
        changed = set()
        removed = set()

        self.librarian.reload(new, changed=changed, removed=removed)
        self.assertTrue(new in changed)
        self.assertFalse(removed)
