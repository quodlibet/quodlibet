from unittest import TestCase, makeSuite
from tests import registerCase

import parser

class ValidityTests(TestCase):
    def test_re(self):
        self.failUnless(parser.is_valid('t = /an re/'))
        self.failUnless(parser.is_valid('t = /an re/c'))
        self.failUnless(parser.is_valid('t = /an\\/re/'))
        self.failIf(parser.is_valid('t = /an/re/'))
    def test_str(self):
        self.failUnless(parser.is_valid('t = "a str"'))
        self.failUnless(parser.is_valid('t = "a str"c'))
        self.failUnless(parser.is_valid('t = "a\\"str"'))
        # there's no equivalent failure for strings

    def test_empty(self):
        self.failUnless(parser.is_valid(''))

    def test_nonsense(self):
        self.failIf(parser.is_valid('a string'))
        self.failIf(parser.is_valid('t = a'))
        self.failIf(parser.is_valid('t = #(a > b)'))
        self.failIf(parser.is_valid("=a= = /b/"))
        self.failIf(parser.is_valid("a = &(/b//"))
        self.failIf(parser.is_valid("(a = &(/b//)"))

    def test_trailing(self):
        self.failIf(parser.is_valid('t = /an re/)'))
        self.failIf(parser.is_valid('|(a, b = /a/, c, d = /q/) woo'))

    def test_not(self):
        self.failUnless(parser.is_valid('t = !/a/'))
        self.failUnless(parser.is_valid('t = !!/a/'))
        self.failUnless(parser.is_valid('!t = "a"'))
        self.failUnless(parser.is_valid('!!t = "a"'))
        self.failUnless(parser.is_valid('t = !|(/a/, !"b")'))
        self.failUnless(parser.is_valid('t = !!|(/a/, !"b")'))
        self.failUnless(parser.is_valid('!|(t = /a/)'))

    def test_taglist(self):
        self.failUnless(parser.is_valid('a, b = /a/'))
        self.failUnless(parser.is_valid('a, b, c = |(/a/)'))
        self.failUnless(parser.is_valid('|(a, b = /a/, c, d = /q/)'))
        self.failIf(parser.is_valid('a = /a/, b'))

    def test_andor(self):
        self.failUnless(parser.is_valid('a = |(/a/, /b/)'))
        self.failUnless(parser.is_valid('a = |(/b/)'))
        self.failUnless(parser.is_valid('|(a = /b/, c = /d/)'))

        self.failUnless(parser.is_valid('a = &(/a/, /b/)'))
        self.failUnless(parser.is_valid('a = &(/b/)'))
        self.failUnless(parser.is_valid('&(a = /b/, c = /d/)'))
        
    def test_numcmp(self):
        self.failUnless(parser.is_valid("#(t < 3)"))
        self.failUnless(parser.is_valid("#(t <= 3)"))
        self.failUnless(parser.is_valid("#(t > 3)"))
        self.failUnless(parser.is_valid("#(t >= 3)"))
        self.failUnless(parser.is_valid("#(t = 3)"))
        self.failUnless(parser.is_valid("#(t != 3)"))

        self.failIf(parser.is_valid("#(t !> 3)"))
        self.failIf(parser.is_valid("#(t >> 3)"))

    def test_trinary(self):
        self.failUnless(parser.is_valid("#(2 < t < 3)"))
        self.failUnless(parser.is_valid("#(2 >= t > 3)"))
        # useless, but valid
        self.failUnless(parser.is_valid("#(5 > t = 2)"))

    def test_list(self):
        self.failUnless(parser.is_valid("#(t < 3, t > 9)"))
        self.failUnless(parser.is_valid("t = &(/a/, /b/)"))
        self.failUnless(parser.is_valid("s, t = |(/a/, /b/)"))
        self.failUnless(parser.is_valid("|(t = /a/, s = /b/)"))

    def test_nesting(self):
        self.failUnless(parser.is_valid("|(s, t = &(/a/, /b/),!#(2 > q > 3))"))

class ParserTests(TestCase):
    from formats.audio import AudioFile as AF

    def setUp(self):
        self.s1 = self.AF(
            { "album": "I Hate: Tests", "artist": "piman", "title": "Quuxly",
              "version": "cake mix", "~filename": "foobar.ogg" })
        self.s2 = self.AF(
            { "album": "Foo the Bar", "artist": "mu", "title": "Rockin' Out",
              "~filename": "something.mp3", "tracknumber": "12/15" })

    def test_re(self):
        for s in ["album = /i hate/", "artist = /pi*/", "title = /x.y/"]:
            self.failUnless(parser.parse(s).search(self.s1))
            self.failIf(parser.parse(s).search(self.s2))
        f = parser.parse("artist = /mu|piman/").search
        self.failUnless(f(self.s1))
        self.failUnless(f(self.s2))

    def test_str(self):
        for k in self.s2.keys():
            v = self.s2[k]
            self.failUnless(parser.parse('%s = "%s"' % (k, v)).search(self.s2))

    def test_numcmp(self):
        self.failUnless(parser.parse("#(track = 0)").search(self.s1))
        self.failUnless(parser.parse("#(notatag = 0)").search(self.s1))
        self.failUnless(parser.parse("#(track = 12)").search(self.s2))

    def test_not(self):
        for s in ["album = !/i hate/", "artist = !/pi*/", "title = !/x.y/"]:
            self.failUnless(parser.parse(s).search(self.s2))
            self.failIf(parser.parse(s).search(self.s1))

    def test_matching(self):
        matchn = ["discnumber = /./",
                  "artist = /MU/c",
                  
                  ]
        match0 = ["version = /./",
                  "* = /Tests/",
                  "&(t = /Quuxly/, filename = /.ogg/)",
                  "album = /Hate: Tests/",
                  ]
        match1 = ["artist = /mu/",
                  "title = /Rocking?/",
                  "tracknumber = /./",
                  ]
        match2 = ["artist = /./",
                  "|(artist = /piman/, title = /Out/c)",
                  ]

        l = [self.s1, self.s2]
        for s in matchn:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, l), [])

        for s in match0:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, l), [self.s1])
        
        for s in match1:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, l), [self.s2])
        
        for s in match2:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, l), l)

registerCase(ValidityTests)
registerCase(ParserTests)
