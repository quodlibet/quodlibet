from unittest import TestCase, makeSuite
from tests import registerCase

from util import escape, unescape, re_esc, encode, decode, mkdir
import os

class UtilTests(TestCase):
    def test_mkdir(self):
        self.failUnless(not os.path.isdir("nonext"))
        mkdir("nonext/test/test2/test3")
        self.failUnless(os.path.isdir("nonext/test/test2/test3"))
        self.failUnless(os.path.isdir("nonext/test/test2"))
        os.rmdir("nonext/test/test2/test3")
        os.rmdir("nonext/test/test2")
        os.rmdir("nonext/test")
        mkdir("nonext/test/foo")
        self.failUnless(os.path.isdir("nonext/test/foo"))
        os.rmdir("nonext/test/foo")
        os.rmdir("nonext/test")
        mkdir("nonext")
        os.rmdir("nonext")
        self.failUnless(not os.path.isdir("nonext"))

    def test_escape(self):
        self.assertEquals(escape(""), "")
        self.assertEquals(escape("foo&"), "foo&amp;")
        self.assertEquals(escape("<&>"), "&lt;&amp;&gt;")
        self.assertEquals(unescape("&"), "&")
        self.assertEquals(unescape("&amp;"), "&")
        self.assertEquals(unescape(escape("<&testing&amp;>amp;")),
                          "<&testing&amp;>amp;")

    def test_re_esc(self):
        self.assertEquals(re_esc(""), "")
        self.assertEquals(re_esc("fo o"), "fo o")
        self.assertEquals(re_esc("!bar"), "\\!bar")
        self.assertEquals(re_esc("*quux#argh?woo"), "\\*quux\\#argh\\?woo")

    def test_unicode(self):
        self.assertEquals(decode(""), "")
        self.assertEquals(decode("foo!"), "foo!")
        self.assertEquals(decode("foo\xde"), u'foo\ufffd [Invalid Unicode]')
        self.assertEquals(encode(u"abcde"), "abcde")

registerCase(UtilTests)
