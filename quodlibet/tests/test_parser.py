from unittest import TestCase, makeSuite
from tests import registerCase

import parser

class ParserTests(TestCase):
    def test_valid(self):
        self.failUnless(parser.is_valid("t = /an re/"))
        self.failUnless(parser.is_valid("t, b = /an re/"))
        self.failUnless(parser.is_valid("t = !/an re/"))
        self.failUnless(parser.is_valid("t = &(/an re/)"))
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

    def test_matching(self):
        songs = [{ "album": "I Hate: Tests",
                   "artist": "piman",
                   "title": "Quuxly",
                   "version": "cake mix",
                   "~filename": "foobar.ogg",
                   },
                 { "album": "Foo the Bar",
                   "artist": "mu",
                   "title": "Rockin' Out",
                   "~filename": "something.mp3",
                   "tracknumber": "12/15",
                 }]
        matchn = ["discnumber = /./",
                  "artist = /MU/c",
                  "title = &(!/out/, !/quux/)",
                  ]
        match0 = ["version = /./",
                  "* = /Tests/",
                  "&(t = /Quuxly/, filename = /.ogg/)",
                  "album = :Hate\: Tests:",
                  "album = /Hate\: Tests/",
                  ]
        match1 = ["artist = /mu/",
                  "title = /Rocking?/",
                  "tracknumber = /./",
                  ]
        match2 = ["artist = /./",
                  "|(artist = /piman/, title = /Out/c)",
                  ]

        for s in matchn:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, songs), [])
        
        for s in match0:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, songs), [songs[0]])
        
        for s in match1:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, songs), [songs[1]])
        
        for s in match2:
            m = parser.parse(s)
            self.failUnlessEqual(filter(m.search, songs), songs)

registerCase(ParserTests)
