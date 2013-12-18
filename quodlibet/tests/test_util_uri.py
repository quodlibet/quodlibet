import os

from tests import TestCase, add

from quodlibet.util.uri import URI
from quodlibet.util.path import is_fsnative


class TURI(TestCase):
    def setUp(s):
        s.http_uri = URI("http://www.example.com/~piman;woo?bar=quux#whee")
        s.rfile_uri = URI("file://example.com/home/piman/crazy")
        s.file_uri = URI.frompath("/home/piman/cr!azy")
        s.extra_uri = URI("file:///////////home/piman")

    def test_windows_path(self):
        if os.name != "nt":
            return

        win_path = u"C:\\SomeDir\xe4"
        uri = URI.frompath(win_path)
        self.assertEqual(uri, "file:///C:/SomeDir%C3%A4")
        self.assertTrue(uri.is_filename)
        self.assertTrue(is_fsnative(uri.filename))
        self.assertEqual(uri.filename, win_path)

    def test_type(s):
        s.failUnless(isinstance(s.http_uri, URI))
        s.failUnless(isinstance(s.http_uri, basestring))

    # bad constructor tests
    def test_empty(s):
        s.failUnlessRaises(ValueError, URI, "")
    def test_no_scheme(s):
        s.failUnlessRaises(ValueError, URI, "foobar/?quux")
    def test_no_loc_or_path(s):
        s.failUnlessRaises(ValueError, URI, "http://")

    # good constructor tests
    def test_scheme(s):
        s.failUnlessEqual(s.http_uri.scheme, "http")
    def test_netlocl(s):
        s.failUnlessEqual(s.http_uri.netloc, "www.example.com")
    def test_path(s):
        s.failUnlessEqual(s.http_uri.path, "/~piman")
    def test_params(s):
        s.failUnless(s.http_uri.params, "woo")
    def test_query(s):
        s.failUnlessEqual(s.http_uri.query, "bar=quux")
    def test_fragment(s):
        s.failUnlessEqual(s.http_uri.fragment, "whee")

    # unescaping
    def test_unescaped(s):
        s.failUnlessEqual(s.file_uri.unescaped, "file:///home/piman/cr!azy")
        s.failUnlessEqual(s.http_uri.unescaped, s.http_uri)

    # local file handling
    def test_frompath(s):
        s.failUnlessEqual(s.file_uri, "file:///home/piman/cr%21azy")
        expected = os.path.sep + os.path.join("home", "piman", "cr!azy")
        s.failUnlessEqual(s.file_uri.filename, expected)
        s.assertTrue(is_fsnative(s.file_uri.filename))

    def test_bad_files(s):
        s.failUnlessRaises(ValueError, lambda: s.http_uri.filename)
        s.failUnlessRaises(ValueError, lambda: s.http_uri.filename)

    def test_is_filename(s):
        s.failUnless(s.file_uri.is_filename)
        s.failIf(s.rfile_uri.is_filename)
        s.failIf(s.http_uri.is_filename)

    # test urlparse workaround
    def test_urlparse_workaround(s):
        s.failUnless(s.extra_uri.is_filename)
        s.failIf(s.extra_uri.netloc)
        expected = os.path.sep + os.path.join("home", "piman")
        s.failUnlessEqual(s.extra_uri.filename, expected)
        s.assertTrue(is_fsnative(s.extra_uri.filename))

add(TURI)
