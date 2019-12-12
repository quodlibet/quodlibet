# Copyright 2007 Javier Kohen
#     2010, 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util import title
from quodlibet.util.string.titlecase import human_title as ht


class Ttitle(TestCase):

    def test_basics(s):
        s.assertEquals(u"Mama's Boy", title(u"mama's boy"))
        s.assertEquals(u"The A-Sides", title(u"the a-sides"))
        s.assertEquals(u"Hello Goodbye", title(u"hello goodbye"))
        s.assertEquals(u"HELLO GOODBYE", title(u"HELLO GOODBYE"))
        s.assertEquals(u"", title(u""))

    def test_extra_spaces(s):
        s.assertEquals(u"  Space", title(u"  space"))
        s.assertEquals(u" Dodgy  Spaces ", title(u" dodgy  spaces "))

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
        s.assertEquals(u"\"24\" Theme",
                 title(u"\"24\" theme"))
        s.assertEquals(u"\"Mad-Dog\" Mike",
                 title(u"\"mad-dog\" mike"))

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

    def test_english_human_title_case(s):
        s.assertEquals(u"System of a Down", ht(u"System Of A Down"))
        s.assertEquals(u"The Man with the Golden Gun",
                       ht(u"The Man With The Golden gun"))
        s.assertEquals(u"Live and Let Die", ht(u"Live And Let Die"))
        # Updated to match modifications to is/are/am rules:
        s.assertEquals(u"The Vitamins Are in My Fresh California Raisins",
                       ht(u"the vitamins are in my fresh california raisins"))
        s.assertEquals(u"Dig In",
                       ht(u"dig in"))
        s.assertEquals(u"In da Club",
                       ht(u"in da club"))
        # See Issue 616
        s.assertEquals(u" Dodgy Are  the Spaces ",
                       ht(u" dodgy are  the spaces "))
        s.assertEquals(u"Space:  The Final Frontier",
                       ht(u"Space:  the final frontier"))
        s.assertEquals(u"- Out of Space", ht(u"- out Of space"))

    def test_tricky_apostrophes(s):
        s.assertEquals(u"Guns 'n' Roses", ht(u"Guns 'n' roses"))
        s.assertEquals(u"Scarlett O'Hara", ht(u"scarlett o'hara"))
        s.assertEquals(u"Scarlett O'Hara", ht(u"Scarlett O'hara"))
        s.assertEquals(u"No Life 'til Leather", ht(u"no life 'til leather"))

    def test_english_humanise_sentences(s):
        """Checks trickier human title casing"""
        s.assertEquals(u"Buffy the Vampire Slayer: The Album",
                       ht(u"Buffy the vampire slayer: the album"))
        s.assertEquals(u"Killing Is My Business... and Business Is Good!",
                       ht(u"Killing is my business... And business is good!"))
        s.assertEquals(u"Herbie Hancock - The Definitive",
                       ht(u"herbie hancock - the definitive"))
