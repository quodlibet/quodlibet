from unittest import TestCase, makeSuite
from tests import registerCase

import parser

class ParserTests(TestCase):
    def test_valid(self):
        self.failUnless(parser.is_valid("t = /an re/"))
        self.failUnless(parser.is_valid("t, b = /an re/"))
        self.failUnless(parser.is_valid("t = !/an re/"))
        self.failUnless(parser.is_valid("t = &(/an re/)"))
        self.failUnless(parser.is_valid("&(=t = /an re/, a = /re2/)"))
        self.failUnless(parser.is_valid("!t = /re/c"))
        self.failIf(parser.is_valid("a = /b"))
        self.failIf(parser.is_valid("/bar/"))
        self.failIf(parser.is_valid("a = b"))
        self.failIf(parser.is_valid("a != /b/"))
        self.failIf(parser.is_valid("a != /b/"))
        self.failIf(parser.is_valid("=a= = /b/"))
        self.failIf(parser.is_valid("a = /b//"))
        self.failIf(parser.is_valid("a, d = /b/, /c/"))
        self.failIf(parser.is_valid("a = &(/b//"))
        self.failIf(parser.is_valid("(a = &(/b//)"))

registerCase(ParserTests)
