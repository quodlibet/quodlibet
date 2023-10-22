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

    def test_basics(self):
        self.assertEquals(u"Mama's Boy", title(u"mama's boy"))
        self.assertEquals(u"The A-Sides", title(u"the a-sides"))
        self.assertEquals(u"Hello Goodbye", title(u"hello goodbye"))
        self.assertEquals(u"HELLO GOODBYE", title(u"HELLO GOODBYE"))
        self.assertEquals(u"", title(u""))

    def test_extra_spaces(self):
        self.assertEquals(u"  Space", title(u"  space"))
        self.assertEquals(u" Dodgy  Spaces ", title(u" dodgy  spaces "))

    def test_quirks(self):
        # This character is not an apostrophe, it's a single quote!
        self.assertEquals(u"Mama’S Boy", title(u"mama’s boy"))
        # This is actually an accent character, not an apostrophe either.
        self.assertEquals(u"Mama`S Boy", title(u"mama`s boy"))

    def test_quotes(self):
        self.assertEquals(u"Hello Goodbye (A Song)",
                          title(u"hello goodbye (a song)"))
        self.assertEquals(u"Hello Goodbye 'A Song'",
                          title(u"hello goodbye 'a song'"))
        self.assertEquals(u'Hello Goodbye "A Song"',
                          title(u'hello goodbye "a song"'))
        self.assertEquals(u"Hello Goodbye „A Song”",
                          title(u"hello goodbye „a song”"))
        self.assertEquals(u"Hello Goodbye ‘A Song’",
                          title(u"hello goodbye ‘a song’"))
        self.assertEquals(u"Hello Goodbye “A Song”",
                          title(u"hello goodbye “a song”"))
        self.assertEquals(u"Hello Goodbye »A Song«",
                          title(u"hello goodbye »a song«"))
        self.assertEquals(u"Hello Goodbye «A Song»",
                          title(u"hello goodbye «a song»"))
        self.assertEquals(u'"24" Theme',
                          title(u'"24" theme'))
        self.assertEquals(u'"Mad-Dog" Mike',
                          title(u'"mad-dog" mike'))

    def test_unicode(self):
        self.assertEquals(u"Fooäbar",
                          title(u"fooäbar"))
        self.assertEquals(u"Los Años Felices",
                          title(u"los años felices"))
        self.assertEquals(u"Ñandú",
                          title(u"ñandú"))
        self.assertEquals(u"Österreich",
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

    def test_english_human_title_case(self):
        self.assertEquals(u"System of a Down", ht(u"System Of A Down"))
        self.assertEquals(u"The Man with the Golden Gun",
                          ht(u"The Man With The Golden gun"))
        self.assertEquals(u"Live and Let Die", ht(u"Live And Let Die"))
        # Updated to match modifications to is/are/am rules:
        self.assertEquals(u"The Vitamins Are in My Fresh California Raisins",
                          ht(u"the vitamins are in my fresh california raisins"))
        self.assertEquals(u"Dig In",
                          ht(u"dig in"))
        self.assertEquals(u"In da Club",
                          ht(u"in da club"))
        # See Issue 616
        self.assertEquals(u" Dodgy Are  the Spaces ",
                          ht(u" dodgy are  the spaces "))
        self.assertEquals(u"Space:  The Final Frontier",
                          ht(u"Space:  the final frontier"))
        self.assertEquals(u"- Out of Space", ht(u"- out Of space"))

    def test_tricky_apostrophes(self):
        self.assertEquals(u"Guns 'n' Roses", ht(u"Guns 'n' roses"))
        self.assertEquals(u"Scarlett O'Hara", ht(u"scarlett o'hara"))
        self.assertEquals(u"Scarlett O'Hara", ht(u"Scarlett O'hara"))
        self.assertEquals(u"No Life 'til Leather", ht(u"no life 'til leather"))

    def test_english_humanise_sentences(self):
        """Checks trickier human title casing"""
        self.assertEquals(u"Buffy the Vampire Slayer: The Album",
                          ht(u"Buffy the vampire slayer: the album"))
        self.assertEquals(u"Killing Is My Business... and Business Is Good!",
                          ht(u"Killing is my business... And business is good!"))
        self.assertEquals(u"Herbie Hancock - The Definitive",
                          ht(u"herbie hancock - the definitive"))
