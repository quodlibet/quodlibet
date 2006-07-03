import os
import sys
import unittest

from tempfile import mkstemp

from library.songs import SongLibrary, SongFileLibrary, SongLibrarian

from test_library import Fake, TLibrary, TLibrarian

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

class FakeSongFile(FakeSong):
    _valid = True
    _exists = True
    _mounted = True

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

class TSongLibrarian(TLibrarian):
    Fake = FakeSong
    Frange = staticmethod(FSrange)
    Library = SongFileLibrary
    Librarian = SongLibrarian

if __name__ == "__main__":
    unittest.main()
