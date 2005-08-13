from unittest import TestCase, makeSuite
from tests import registerCase
from songlist import PlaylistModel

class Playlist(TestCase):
    def setUp(self):
        self.pl = PlaylistModel()
        self.pl.set(range(10))

    def test_isempty(self):
        self.pl.set([])
        self.failUnless(self.pl.is_empty())

    def test_get(self):
        self.assertEqual(self.pl.get(), range(10))
        self.pl.set(range(12))
        self.assertEqual(self.pl.get(), range(12))

    def test_next(self):
        self.failUnless(self.pl.current is None)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 0)
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 1)
        self.pl.go_to(9)
        self.failUnlessEqual(self.pl.current, 9)
        self.pl.next()
        self.failUnless(self.pl.current is None)

    def test_previous(self):
        self.pl.go_to(2)
        self.failUnlessEqual(self.pl.current, 2)
        self.pl.previous()
        self.failUnlessEqual(self.pl.current, 1)
        self.pl.previous()
        self.failUnlessEqual(self.pl.current, 0)
        self.pl.previous()
        self.failUnlessEqual(self.pl.current, 0)


    def test_saveplace(self):
        self.pl.go_to(5)
        self.failUnlessEqual(self.pl.current, 5)
        self.pl.set([5, 10, 15, 20])
        self.pl.next()
        self.failUnlessEqual(self.pl.current, 10)

    def shutDown(self):
        self.pl.destroy()

registerCase(Playlist)
