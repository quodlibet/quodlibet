from tests import TestCase

from quodlibet.util.path import pathname2url_win32


class Tpathname2url(TestCase):
    def test_win(self):
        cases = {
            r"c:\abc\def": "/c:/abc/def",
            r"C:\a b\c.txt": "/C:/a%20b/c.txt",
            r"\\xy\z.txt": "xy/z.txt",
            r"C:\a:b\c:d": "/C:/a%3Ab/c%3Ad"
            }
        p2u = pathname2url_win32
        for inp, should in cases.iteritems():
            self.failUnlessEqual(p2u(inp), should)
