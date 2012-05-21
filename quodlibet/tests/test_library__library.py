import gtk

import os

from tests import TestCase, add
from tempfile import mkstemp

from quodlibet.library._library import Library, Librarian

class Fake(int):
    def __init__(self, self2):
        self.key = int(self)

def Frange(*args):
    return map(Fake, range(*args))

class TLibrary(TestCase):
    Fake = Fake
    Frange = staticmethod(Frange)
    Library = Library

    def setUp(self):
        self.library = self.Library()
        self.added = []
        self.changed = []
        self.removed = []

        self.library.connect_object('added', list.extend, self.added)
        self.library.connect_object('changed', list.extend, self.changed)
        self.library.connect_object('removed', list.extend, self.removed)

    def test_add(self):
        self.library.add(self.Frange(12))
        self.failUnlessEqual(self.added, self.Frange(12))
        del(self.added[:])
        self.library.add(self.Frange(12, 24))
        self.failUnlessEqual(self.added, self.Frange(12, 24))

    def test_remove(self):
        self.library.add(self.Frange(10))
        self.library.remove(self.Frange(3, 6))
        self.failUnlessEqual(self.removed, self.Frange(3, 6))

        # Neither the objects nor their keys should be present.
        self.failIf(self.Fake(3) in self.library)
        self.failUnless(self.Fake(6) in self.library)
        self.failIf(3 in self.library)
        self.failUnless(6 in self.library)

    def test_remove_when_not_present(self):
        self.failUnlessRaises(KeyError, self.library.remove, [self.Fake(12)])

    def test_changed(self):
        self.library.add(self.Frange(10))
        self.library.changed(self.Frange(5))
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(self.changed, self.Frange(5))

    def test_changed_not_present(self):
        self.library.add(self.Frange(10))
        self.library.changed(self.Frange(2, 20, 3))
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(self.changed, [2, 5, 8])

    def test_changed_none_present(self):
        self.library.changed(self.Frange(5))
        while gtk.events_pending(): gtk.main_iteration()

    def test___iter__(self):
        self.library.add(self.Frange(10))
        self.failUnlessEqual(sorted(list(self.library)), self.Frange(10))

    def test___iter___empty(self):
        self.failIf(list(self.library))

    def test___len__(self):
        self.failUnlessEqual(len(self.library), 0)
        self.library.add(self.Frange(10))
        self.failUnlessEqual(len(self.library), 10)
        self.library.remove(self.Frange(3))
        self.failUnlessEqual(len(self.library), 7)

    def test___getitem__(self):
        self.library.add(self.Frange(10))
        self.failUnlessEqual(self.library[5], 5)
        new = self.Fake(12)
        new.key = 100
        self.library.add([new])
        self.failUnlessEqual(self.library[100], 12)
        self.failIf(12 in self.library)

    def test___getitem___not_present(self):
        self.library.add(self.Frange(10))
        self.failUnlessRaises(KeyError, self.library.__getitem__, 12)

    def test___contains__(self):
        self.library.add(self.Frange(10))
        new = self.Fake(12)
        new.key = 100
        self.library.add([new])
        for value in [0, 1, 2, 6, 9, 100, new]:
            # 0, 1, 2, 6, 9: all added by self.Frange
            # 100: key for new
            # new: is itself present
            self.failUnless(value in self.library, "didn't find %d" % value)

        for value in [-1, 10, 12, 101]:
            # -1, 10, 101: boundry values
            # 12: equal but non-key-equal to new
            self.failIf(value in self.library, "found %d" % value)

    def test_get(self):
        self.failUnless(self.library.get(12) is None)
        self.failUnless(self.library.get(12, "foo") == "foo")
        new = self.Fake(12)
        new.key = 100
        self.library.add([new])
        self.failUnless(self.library.get(12) is None)
        self.failUnless(self.library.get(100) is new)

    def test_keys(self):
        items = []
        for i in range(20):
            items.append(self.Fake(i))
            items[-1].key = i + 100
        self.library.add(items)
        self.failUnlessEqual(sorted(self.library.keys()), range(100, 120))
        self.failUnlessEqual(sorted(self.library.iterkeys()), range(100, 120))

    def test_values(self):
        items = []
        for i in range(20):
            items.append(self.Fake(i))
            items[-1].key = i + 100
        self.library.add(items)
        self.failUnlessEqual(sorted(self.library.values()), range(20))
        self.failUnlessEqual(sorted(self.library.itervalues()), range(20))

    def test_items(self):
        items = []
        for i in range(20):
            items.append(self.Fake(i))
            items[-1].key = i + 100
        self.library.add(items)
        expected = zip(range(100, 120), range(20))
        self.failUnlessEqual(sorted(self.library.items()), expected)
        self.failUnlessEqual(sorted(self.library.iteritems()), expected)

    def test_has_key(self):
        self.failIf(self.library.has_key(10))
        new = self.Fake(10)
        new.key = 20
        self.library.add([new])
        self.failIf(self.library.has_key(10))
        self.failUnless(self.library.has_key(20))

    def test_save_load(self):
        fd, filename = mkstemp()
        try:
            os.close(fd)
            self.library.add(self.Frange(30))
            self.library.save(filename)

            library = self.Library()
            library.load(filename)
            self.failUnlessEqual(
                sorted(self.library.items()), sorted(library.items()))
        finally:
            os.unlink(filename)

    def tearDown(self):
        self.library.destroy()
add(TLibrary)

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

        self.lib1.connect_object('added', list.extend, self.added_1)
        self.lib1.connect_object('changed', list.extend, self.changed_1)
        self.lib1.connect_object('removed', list.extend, self.removed_1)
        self.lib2.connect_object('added', list.extend, self.added_2)
        self.lib2.connect_object('changed', list.extend, self.changed_2)
        self.lib2.connect_object('removed', list.extend, self.removed_2)
        self.librarian.connect_object('added', list.extend, self.added)
        self.librarian.connect_object('changed', list.extend, self.changed)
        self.librarian.connect_object('removed', list.extend, self.removed)

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
        while gtk.events_pending(): gtk.main_iteration()
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
add(TLibrarian)
