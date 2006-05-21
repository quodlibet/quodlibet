from tests import TestCase, add

from qltk.renamefiles import SpacesToUnderscores, StripWindowsIncompat
from qltk.renamefiles import StripDiacriticals, StripNonASCII

class TFilter(TestCase):
    def setUp(self): self.c = self.Kind()
    def tearDown(self): self.c.destroy()
    def test_empty(self):
        v = self.c.filter("", u"")
        self.failUnlessEqual(v, "")
        self.failUnless(isinstance(v, unicode))
    def test_safe(self):
        self.failUnlessEqual(self.c.filter("", u"safe"), "safe")

class TSpacesToUnderscores(TFilter):
    Kind = SpacesToUnderscores
    def test_conv(self):
        self.failUnlessEqual(self.c.filter("", "foo bar "), "foo_bar_")
add(TSpacesToUnderscores)

class TStripWindowsIncompat(TFilter):
    Kind = StripWindowsIncompat
    def test_conv(self):
        self.failUnlessEqual(self.c.filter("", 'foo\\:*?;"<>|'), "foo_________")

    def test_ends_with_dots_or_spaces(self):
        self.failUnlessEqual(self.c.filter("", 'foo. . '), "foo. ._")
        self.failUnlessEqual(self.c.filter("", 'foo. /bar .'), "foo._/bar _")
add(TStripWindowsIncompat)

class TStripDiacriticals(TFilter):
    Kind = StripDiacriticals
    def test_conv(self):
        self.failUnlessEqual(self.c.filter("", u"\u00c1 test"), "A test")
add(TStripDiacriticals)

class TStripNonASCII(TFilter):
    Kind = StripNonASCII
    def test_conv(self):
        self.failUnlessEqual(
            self.c.filter("", u"foo \u00c1 \u1234"), "foo _ _")
add(TStripNonASCII)
