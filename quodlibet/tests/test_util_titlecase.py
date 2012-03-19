# -*- coding: utf-8 -*-
# Copyright 2007 Javier Kohen, 2010 Nick Boultbee
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

    # human title case got moved in the plugin..
    # move once we have a test suite for plugins
    def __skip_test_english_human_titlecase(s):
        """Checks human title casing, assuming that it defaults to enabled"""
        s.assertEquals(u"System of a Down",
                 title(u"System Of A Down"))
        s.assertEquals(u"The Man with the Golden Gun",
                 title(u"The Man With The Golden gun"))
        s.assertEquals(u"Live and Let Die",
                 title(u"Live And Let Die"))
        # s.assertEquals(u"The Vitamins are in my Fresh California Raisins",
        # Updated to match modifications to is/are/am rules:
        s.assertEquals(u"The Vitamins Are in My Fresh California Raisins",
                 title(u"the vitamins are in my fresh california raisins"))
        s.assertEquals(u"Dig In",
                 title(u"dig in"))
        s.assertEquals(u"In da Club",
                 title(u"in da club"))
        # See Issue 616
        s.assertEquals(u" Dodgy Are  the Spaces ",
                 title(u" dodgy are  the spaces "))
        s.assertEquals(u"Space:  The Final Frontier",
                 title(u"Space:  the final frontier"))

    def __skip_test_tricky_apostrophes(s):
        s.assertEquals(u"Guns 'n' Roses", title(u"Guns 'n' roses"))
        s.assertEquals(u"Scarlett O'Hara", title(u"scarlett o'hara"))
        s.assertEquals(u"Scarlett O'Hara", title(u"Scarlett O'hara"))
        s.assertEquals(u"No Life 'til Leather", title(u"no life 'til leather"))


    def __skip_test_english_human_titlecase_sentences(s):
        """Checks trickier human title casing, also assuming it's enabled"""
        s.assertEquals(u"Buffy the Vampire Slayer: The Album",
                 title(u"Buffy the vampire slayer: the album"))
        s.assertEquals(u"Killing Is My Business... and Business Is Good!",
                 title(u"Killing is my business... And business is good!"))
        s.assertEquals(u"Herbie Hancock - The Definitive",
                 title(u"herbie hancock - the definitive"))


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
