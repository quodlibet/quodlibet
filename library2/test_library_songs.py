import os
import sys
import unittest

from tempfile import mkstemp

from library.songs import SongFileLibrary, SongLibrarian

from test_library import Fake, TLibrary, TLibrarian

class FakeSong(Fake):
    valid = True

    def list(self, tag):
        if tag > self: return []
        else: return [int(self)]

    def valid(self):
        return self.valid

    def exists(self):
        return True

    def reload(self):
        self.valid = True

    def mounted(self):
        return True

    def rename(self, newname):
        self.key = newname

def FSrange(*args):
    return map(FakeSong, range(*args))

class TSongFileLibrary(TLibrary):
    Fake = FakeSong
    Frange = staticmethod(FSrange)
    Library = SongFileLibrary

class TSongLibrarian(TLibrarian):
    Fake = FakeSong
    Frange = staticmethod(FSrange)
    Library = SongFileLibrary
    Librarian = SongLibrarian

if __name__ == "__main__":
    unittest.main()
