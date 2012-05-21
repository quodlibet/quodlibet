import gtk

import os
import unittest

from tempfile import mkstemp

from quodlibet.library.songs import SongLibrary, SongFileLibrary, SongLibrarian

from tests import add
from tests.test_library__library import Fake, TLibrary, TLibrarian

import shutil
from quodlibet import config

class FakeSong(Fake):
    def list(self, tag):
        # Turn tag_values into a less-than query, for testing.
        if tag <= self: return []
        else: return [int(self)]

    def rename(self, newname):
        self.key = newname

def FSrange(*args):
    return map(FakeSong, range(*args))

class TSongLibrary(TLibrary):
    Fake = FakeSong
    Frange = staticmethod(FSrange)
    Library = SongLibrary

    def test_rename(self):
        song = FakeSong(10)
        self.library.add([song])
        self.library.rename(song, 20)
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnless(song in self.changed)
        self.failUnless(song in self.library)
        self.failUnless(song.key in self.library)
        self.failUnlessEqual(song.key, 20)

    def test_tag_values(self):
        self.library.add(self.Frange(30))
        del(self.added[:])
        self.failUnlessEqual(sorted(self.library.tag_values(10)), range(10))
        self.failUnlessEqual(sorted(self.library.tag_values(0)), [])
        self.failIf(self.changed or self.added or self.removed)
add(TSongLibrary)

class FakeSongFile(FakeSong):
    _valid = True
    _exists = True
    _mounted = True

    mountpoint = property(lambda self: int(self))

    def valid(self):
        return self._valid

    def exists(self):
        return self._exists

    def reload(self):
        if self._exists: self._valid = True
        else: raise IOError("doesn't exist")

    def mounted(self):
        return self._mounted

def FSFrange(*args):
    return map(FakeSongFile, range(*args))

class TSongFileLibrary(TSongLibrary):
    Fake = FakeSongFile
    Frange = staticmethod(FSFrange)
    Library = SongFileLibrary

    def test__load_exists_invalid(self):
        new = self.Fake(100)
        new._valid = False
        changed, removed = self.library._load(new)
        self.failIf(removed)
        self.failUnless(changed)
        self.failUnless(new._valid)
        self.failUnless(new in self.library)

    def test__load_not_exists(self):
        new = self.Fake(100)
        new._valid = False
        new._exists = False
        changed, removed = self.library._load(new)
        self.failIf(removed)
        self.failIf(changed)
        self.failIf(new._valid)
        self.failIf(new in self.library)

    def test__load_error_during_reload(self):
        try:
            from quodlibet import util
            print_exc = util.print_exc
            util.print_exc = lambda *args, **kwargs: None
            new = self.Fake(100)
            def error(): raise IOError
            new.reload = error
            new._valid = False
            changed, removed = self.library._load(new)
            self.failUnless(removed)
            self.failIf(changed)
            self.failIf(new._valid)
            self.failIf(new in self.library)
        finally:
            util.print_exc = print_exc

    def test__load_not_mounted(self):
        new = self.Fake(100)
        new._valid = False
        new._exists = False
        new._mounted = False
        changed, removed = self.library._load(new)
        self.failIf(removed)
        self.failIf(changed)
        self.failIf(new._valid)
        self.failIf(new in self.library)
        self.failUnlessEqual(new, self.library._masked[new][new])

    def __get_file(self):
        fd, filename = mkstemp(".flac")
        shutil.copy(os.path.join('tests', 'data', 'empty.flac'), filename)
        return filename

    def test_add_filename(self):
        config.init()
        try:
            filename = self.__get_file()
            ret = self.library.add_filename(filename)
            self.failUnless(ret)
            self.failUnlessEqual(1, len(self.library))
            self.failUnlessEqual(len(self.added), 1)
            ret = self.library.add_filename(filename)
            self.failUnless(ret)
            self.failUnlessEqual(len(self.added), 1)
            os.unlink(filename)

            filename = self.__get_file()
            ret = self.library.add_filename(filename, add=False)
            self.failUnless(ret)
            self.failIf(ret in self.library)
            self.failUnlessEqual(len(self.added), 1)
            self.library.add([ret])
            self.failUnless(ret in self.library)
            self.failUnlessEqual(len(self.added), 2)
            self.failUnlessEqual(2, len(self.library))
            os.unlink(filename)

            ret = self.library.add_filename("")
            self.failIf(ret)
            self.failUnlessEqual(len(self.added), 2)
            self.failUnlessEqual(2, len(self.library))

        finally:
            config.quit()

add(TSongFileLibrary)

class TSongLibrarian(TLibrarian):
    Fake = FakeSong
    Frange = staticmethod(FSrange)
    Library = SongFileLibrary
    Librarian = SongLibrarian

    def test_tag_values(self):
        self.lib1.add(self.Frange(0, 30, 2))
        self.lib2.add(self.Frange(1, 30, 2))
        del(self.added[:])
        self.failUnlessEqual(sorted(self.librarian.tag_values(20)), range(20))
        self.failUnlessEqual(sorted(self.librarian.tag_values(0)), [])
        self.failIf(self.changed or self.added or self.removed)

    def test_rename(self):
        new = self.Fake(10)
        new.key = 30
        self.lib1.add([new])
        self.lib2.add([new])
        self.librarian.rename(new, 20)
        while gtk.events_pending(): gtk.main_iteration()
        self.failUnlessEqual(new.key, 20)
        self.failUnless(new in self.lib1)
        self.failUnless(new in self.lib2)
        self.failUnless(new.key in self.lib1)
        self.failUnless(new.key in self.lib2)
        self.failUnlessEqual(self.changed_1, [new])
        self.failUnlessEqual(self.changed_2, [new])
        self.failUnless(new in self.changed)
add(TSongLibrarian)

if __name__ == "__main__":
    unittest.main()
