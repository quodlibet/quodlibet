# -*- coding: utf-8 -*-
# Copyright 2007 Javier Kohen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add

from quodlibet.util import title

class Ttitle(TestCase):
    def test_basics(s):
        s.assertEquals(u"Mama's Boy", title(u"mama's boy"))
        s.assertEquals(u"The A-Sides", title(u"the a-sides"))
        s.assertEquals(u"Hello Goodbye", title(u"hello goodbye"))
        s.assertEquals(u"HELLO GOODBYE", title(u"HELLO GOODBYE"))

    def test_quirks(s):
        # This character is not an apostrophe, it's a single quote!
        s.assertEquals(u"Mama’S Boy", title(u"mama’s boy"))
        # This is actually an accent character, not an apostrophe either.
        s.assertEquals(u"Mama`S Boy", title(u"mama`s boy"))

    def test_quotes(s):
        s.assertEquals(u"Hello Goodbye (A Song)",
                 title(u"hello goodbye (a song)"))
        s.assertEquals(u"Hello Goodbye 'A Song'",
                 title(u"hello goodbye 'a song'"))
        s.assertEquals(u'Hello Goodbye "A Song"',
                 title(u'hello goodbye "a song"'))
        s.assertEquals(u"Hello Goodbye „A Song”",
                 title(u"hello goodbye „a song”"))
        s.assertEquals(u"Hello Goodbye ‘A Song’",
                 title(u"hello goodbye ‘a song’"))
        s.assertEquals(u"Hello Goodbye “A Song”",
                 title(u"hello goodbye “a song”"))
        s.assertEquals(u"Hello Goodbye »A Song«",
                 title(u"hello goodbye »a song«"))
        s.assertEquals(u"Hello Goodbye «A Song»",
                 title(u"hello goodbye «a song»"))

    def test_unicode(s):
        s.assertEquals(u"Fooäbar",
                 title(u"fooäbar"))
        s.assertEquals(u"Los Años Felices",
                 title(u"los años felices"))
        s.assertEquals(u"Ñandú",
                 title(u"ñandú"))
        s.assertEquals(u"Österreich",
                 title(u"österreich"))
        # Not a real word - there is none with this character at the beginning
        # but still Python doesn't capitalize the es-zed properly.
        # s.assertEquals(u"SSbahn", title(u"ßbahn"))

    # Old tests, somewhat redundant with the above, but you can never have
    # too many tests...

    def test_empty(self):
        self.failUnlessEqual(title(""), "")

    def test_oneword(self):
        self.failUnlessEqual(title("foobar"), "Foobar")

    def test_twowords(self):
        self.failUnlessEqual(title("foo bar"), "Foo Bar")

    def test_preserve(self):
        self.failUnlessEqual(title("fooBar"), "FooBar")

    def test_nonalphabet(self):
        self.failUnlessEqual(title("foo 1bar"), "Foo 1bar")

    def test_two_words_and_one_not(self):
        self.failUnlessEqual(title("foo 1  bar"), "Foo 1  Bar")

    def test_apostrophe(self):
        self.failUnlessEqual(title("it's"), "It's")

add(Ttitle)
