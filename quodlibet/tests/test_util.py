from unittest import TestCase, makeSuite
from tests import registerCase

from util import escape, unescape, re_esc, encode, decode, mkdir, iscommand
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
        self.failUnlessEqual(escape(""), "")
        self.failUnlessEqual(escape("foo&"), "foo&amp;")
        self.failUnlessEqual(escape("<&>"), "&lt;&amp;&gt;")
        self.failUnlessEqual(unescape("&"), "&")
        self.failUnlessEqual(unescape("&amp;"), "&")
        self.failUnlessEqual(unescape(escape("<&testing&amp;>amp;")),
                          "<&testing&amp;>amp;")

    def test_re_esc(self):
        self.failUnlessEqual(re_esc(""), "")
        self.failUnlessEqual(re_esc("fo o"), "fo o")
        self.failUnlessEqual(re_esc("!bar"), "\\!bar")
        self.failUnlessEqual(re_esc("*quux#argh?woo"), "\\*quux\\#argh\\?woo")

    def test_unicode(self):
        self.failUnlessEqual(decode(""), "")
        self.failUnlessEqual(decode("foo!"), "foo!")
        self.failUnlessEqual(decode("foo\xde"), u'foo\ufffd [Invalid Unicode]')
        self.failUnlessEqual(encode(u"abcde"), "abcde")

    def test_iscommand(self):
        self.failUnless(iscommand("ls"))
        self.failUnless(iscommand("/bin/ls"))
        self.failUnless(iscommand("/bin/asdfjkl"))
        self.failUnless(iscommand("asdfjkl"))

registerCase(UtilTests)
