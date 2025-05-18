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
        self.assertEqual("Mama's Boy", title("mama's boy"))
        self.assertEqual("The A-Sides", title("the a-sides"))
        self.assertEqual("Hello Goodbye", title("hello goodbye"))
        self.assertEqual("HELLO GOODBYE", title("HELLO GOODBYE"))
        self.assertEqual("", title(""))

    def test_extra_spaces(self):
        self.assertEqual("  Space", title("  space"))
        self.assertEqual(" Dodgy  Spaces ", title(" dodgy  spaces "))

    def test_quirks(self):
        # This character is not an apostrophe, it's a single quote!
        self.assertEqual("Mama’S Boy", title("mama’s boy"))
        # This is actually an accent character, not an apostrophe either.
        self.assertEqual("Mama`S Boy", title("mama`s boy"))

    def test_quotes(self):
        self.assertEqual("Hello Goodbye (A Song)", title("hello goodbye (a song)"))
        self.assertEqual("Hello Goodbye 'A Song'", title("hello goodbye 'a song'"))
        self.assertEqual('Hello Goodbye "A Song"', title('hello goodbye "a song"'))
        self.assertEqual("Hello Goodbye „A Song”", title("hello goodbye „a song”"))
        self.assertEqual("Hello Goodbye ‘A Song’", title("hello goodbye ‘a song’"))
        self.assertEqual("Hello Goodbye “A Song”", title("hello goodbye “a song”"))
        self.assertEqual("Hello Goodbye »A Song«", title("hello goodbye »a song«"))
        self.assertEqual("Hello Goodbye «A Song»", title("hello goodbye «a song»"))
        self.assertEqual('"24" Theme', title('"24" theme'))
        self.assertEqual('"Mad-Dog" Mike', title('"mad-dog" mike'))

    def test_unicode(self):
        self.assertEqual("Fooäbar", title("fooäbar"))
        self.assertEqual("Los Años Felices", title("los años felices"))
        self.assertEqual("Ñandú", title("ñandú"))
        self.assertEqual("Österreich", title("österreich"))

    # Old tests, somewhat redundant with the above, but you can never have
    # too many tests...

    def test_empty(self):
        self.assertEqual(title(""), "")

    def test_oneword(self):
        self.assertEqual(title("foobar"), "Foobar")

    def test_twowords(self):
        self.assertEqual(title("foo bar"), "Foo Bar")

    def test_preserve(self):
        self.assertEqual(title("fooBar"), "FooBar")

    def test_nonalphabet(self):
        self.assertEqual(title("foo 1bar"), "Foo 1bar")

    def test_two_words_and_one_not(self):
        self.assertEqual(title("foo 1  bar"), "Foo 1  Bar")

    def test_apostrophe(self):
        self.assertEqual(title("it's"), "It's")

    def test_english_human_title_case(self):
        self.assertEqual("System of a Down", ht("System Of A Down"))
        self.assertEqual(
            "The Man with the Golden Gun", ht("The Man With The Golden gun")
        )
        self.assertEqual("Live and Let Die", ht("Live And Let Die"))
        # Updated to match modifications to is/are/am rules:
        self.assertEqual(
            "The Vitamins Are in My Fresh California Raisins",
            ht("the vitamins are in my fresh california raisins"),
        )
        self.assertEqual("Dig In", ht("dig in"))
        self.assertEqual("In da Club", ht("in da club"))
        # See Issue 616
        self.assertEqual(" Dodgy Are  the Spaces ", ht(" dodgy are  the spaces "))
        self.assertEqual("Space:  The Final Frontier", ht("Space:  the final frontier"))
        self.assertEqual("- Out of Space", ht("- out Of space"))

    def test_tricky_apostrophes(self):
        self.assertEqual("Guns 'n' Roses", ht("Guns 'n' roses"))
        self.assertEqual("Scarlett O'Hara", ht("scarlett o'hara"))
        self.assertEqual("Scarlett O'Hara", ht("Scarlett O'hara"))
        self.assertEqual("No Life 'til Leather", ht("no life 'til leather"))

    def test_english_humanise_sentences(self):
        """Checks trickier human title casing"""
        self.assertEqual(
            "Buffy the Vampire Slayer: The Album",
            ht("Buffy the vampire slayer: the album"),
        )
        self.assertEqual(
            "Killing Is My Business... and Business Is Good!",
            ht("Killing is my business... And business is good!"),
        )
        self.assertEqual(
            "Herbie Hancock - The Definitive", ht("herbie hancock - the definitive")
        )
