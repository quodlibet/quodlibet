from unittest import TestCase, makeSuite
from tests import registerCase

import sre
from match import Union, Inter, Neg, Tag

TAG = { "artist": "piman\nmu",
        "title": "Quod Libet",
        "album": "Python & PyGTK",
        "version": "0.3"
        }

class MatchTest(TestCase):
    def test_Union(self):
        m = Union([sre.compile("piman"), sre.compile("empty")])
        self.failUnless(m.search(TAG["artist"]))
        m = Union([sre.compile("undef"), sre.compile("empty")])
        self.failIf(m.search(TAG["artist"]))

    def test_Inter(self):
        m = Inter([sre.compile("mu"), sre.compile("piman")])
        self.failUnless(m.search(TAG["artist"]))
        m = Inter([sre.compile("mu"), sre.compile("empty")])
        self.failIf(m.search(TAG["artist"]))

    def test_Neg(self):
        m = Neg(sre.compile("foobar"))
        self.failUnless(m.search(TAG["title"]))
        m = Neg(sre.compile("Quod"))
        self.failIf(m.search(TAG["title"]))

    def test_Tag(self):
        m = Tag("title", sre.compile("Quod"))
        self.failUnless(m.search(TAG))
        m = Tag("album", sre.compile("PythGTK"))
        self.failIf(m.search(TAG))
        
registerCase(MatchTest)
