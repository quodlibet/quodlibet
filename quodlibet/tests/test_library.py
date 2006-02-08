from tests import TestCase, add
from formats._audio import AudioFile as AF

import library

CORPUS = [
    AF({"~filename": "/tmp/foo", "title": "A", "random": "A"}),
    AF({"~filename": "/tmp/foo2", "title": "B", "artist": "woo"}),
    AF({"~filename": "/tmp/foo3", "title": "C", "random": "B"}),
    AF({"~filename": "/tmp/foo4", "title": "D", "random": "C"}),
    AF({"~filename": "/tmp/foo5", "title": "E"}),
    AF({"~filename": "/tmp/foo6", "title": "F", "random": "A"}),
    ]

class TLibrary(TestCase):
    def setUp(self):
        self.lib = library.Library()
        for song in CORPUS[1:]:
            self.failUnless(self.lib.add_song(song))

    def test_add(self):
        self.failUnless(self.lib.add_song(CORPUS[0]))

    def test_add_in_lib(self):
        self.failIf(self.lib.add_song(CORPUS[1]))

    def test_add_fn(self):
        song = self.lib.add("tests/data/silence-44-s.ogg")
        self.failUnless(song)
        self.failUnless(song["~filename"] in self.lib)
        self.failUnless(song in self.lib.values())
        self.failIf(self.lib.add_song(song))

    def test_add_fn_in_lib(self):
        self.failUnless(self.lib.add("/tmp/foo2"))

    def test_add_fn_invalid(self):
        self.failIf(self.lib.add("/does/not/exist"))

    def test_random(self):
        self.failUnless(self.lib.random('title') in "ABCDEF")
        self.failUnlessEqual(self.lib.random('artist'), "woo")
        self.failUnlessEqual(self.lib.random('album'), None)

    def test_random_go_away_501(self):
        results = {}
        for i in range(1000):
            val = self.lib.random('random')
            results[val] = results.get(val, 0) + 1
        for v in results.values():
            self.failUnless(250 < v < 400, "statistically unlikely outcome")

    def test_remove(self):
        song = CORPUS[1]
        self.failUnless(song["~filename"] in self.lib)
        self.failUnless(song in self.lib.values())
        self.lib.remove(song)
        self.failIf(song["~filename"] in self.lib)
        self.failIf(song in self.lib.values())

    def test_saveload(self):
        import os, tempfile
        fd, name = tempfile.mkstemp()
        os.close(fd)
        self.lib.save(name)
        newlib = library.Library()
        changed, removed = newlib.load(name)
        self.failUnlessEqual(len(self.lib), removed)
        os.unlink(name)

    def test_reload(self):
        song = CORPUS[1]
        changed, removed = [], []
        self.lib.reload(song, changed, removed)
        self.failUnlessEqual(removed, [song])
        self.failIf(changed)
        self.failIf(song["~filename"] in self.lib)
        self.failIf(song in self.lib.values())

    def test_scan(self):
        changed = removed = []
        for changed, removed in self.lib.scan([]): pass
        self.failIf(changed)
        self.failIf(removed)

    def test_rebuild(self):
        for changed, removed in self.lib.rebuild(): pass
        self.failIf(changed)
        self.failUnlessEqual(len(removed), len(CORPUS) - 1)

    def test_query(self):
        songs = self.lib.query("artist = /./")
        self.failUnlessEqual(songs, [CORPUS[1]])
        songs = self.lib.query("title = !/./")
    def test_query_sorted(self):
        songs = self.lib.query("title = /./", "title")
        self.failUnlessEqual(songs, CORPUS[1:])
    def test_query_simple(self):
        songs = self.lib.query("C")
        self.failUnlessEqual(songs, [CORPUS[2]])

add(TLibrary)
