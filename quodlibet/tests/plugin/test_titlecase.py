# Copyright 2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from tests import TestCase, add
from tests.plugin import PluginTestCase
from quodlibet import config


class TTitlecase(PluginTestCase):
    def setUp(self):
        config.init()
        self.plugin = self.plugins["Title Case"]

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

    def tearDown(self):
        config.quit()

add(TTitlecase)
