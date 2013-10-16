# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>,
#                Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from tests import add
from tests.plugin import PluginTestCase
from quodlibet import config, util


humanise = None

class TTitlecase(PluginTestCase):
    def setUp(self):
        globals().update(vars(self.modules["Title Case"]))
        config.init()
        self.plugin = self.plugins["Title Case"].cls

    def test_no_all_caps(self):
        self.plugin.config_set("allow_all_caps", True)
        p = self.plugin("", "")
        self.failUnlessEqual(p.activated("", "foo bar")[0][1], "Foo Bar")
        self.failUnlessEqual(p.activated("", "FOO BAR")[0][1], "FOO BAR")

    def test_all_caps(self):
        self.plugin.config_set("allow_all_caps", False)
        p = self.plugin("", "")
        self.failUnlessEqual(p.activated("", "foo bar")[0][1], "Foo Bar")
        self.failUnlessEqual(p.activated("", "FOO BAR")[0][1], "Foo Bar")

    def title(self, value):
        """Mimic the plugin's basic operation without config etc"""
        value = util.title(value)
        return humanise(value)

    def test_english_human_title_case(s):
        """Checks human humanise casing, assuming that it defaults to enabled"""
        s.assertEquals(u"System of a Down",
                s.title(u"System Of A Down"))
        s.assertEquals(u"The Man with the Golden Gun",
                s.title(u"The Man With The Golden gun"))
        s.assertEquals(u"Live and Let Die",
                s.title(u"Live And Let Die"))
        # s.assertEquals(u"The Vitamins are in my Fresh California Raisins",
        # Updated to match modifications to is/are/am rules:
        s.assertEquals(u"The Vitamins Are in My Fresh California Raisins",
                s.title(u"the vitamins are in my fresh california raisins"))
        s.assertEquals(u"Dig In",
                s.title(u"dig in"))
        s.assertEquals(u"In da Club",
                s.title(u"in da club"))
        # See Issue 616
        s.assertEquals(u" Dodgy Are  the Spaces ",
                s.title(u" dodgy are  the spaces "))
        s.assertEquals(u"Space:  The Final Frontier",
                s.title(u"Space:  the final frontier"))
        s.assertEquals(u"- Out of Space",
                s.title(u"- out Of space"))

    def test_tricky_apostrophes(s):
        s.assertEquals(u"Guns 'n' Roses", s.title(u"Guns 'n' roses"))
        s.assertEquals(u"Scarlett O'Hara", s.title(u"scarlett o'hara"))
        s.assertEquals(u"Scarlett O'Hara", s.title(u"Scarlett O'hara"))
        s.assertEquals(u"No Life 'til Leather",
                s.title(u"no life 'til leather"))

    def test_english_humanise_sentences(s):
        """Checks trickier human title casing, also assuming it's enabled"""
        s.assertEquals(u"Buffy the Vampire Slayer: The Album",
                s.title(u"Buffy the vampire slayer: the album"))
        s.assertEquals(u"Killing Is My Business... and Business Is Good!",
                s.title(u"Killing is my business... And business is good!"))
        s.assertEquals(u"Herbie Hancock - The Definitive",
                s.title(u"herbie hancock - the definitive"))

    def tearDown(self):
        config.quit()

add(TTitlecase)
