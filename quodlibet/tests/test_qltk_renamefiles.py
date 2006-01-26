from tests import add, TestCase
from qltk.renamefiles import SpacesToUnderscores, StripWindowsIncompat, StripDiacriticals, StripNonASCII

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
