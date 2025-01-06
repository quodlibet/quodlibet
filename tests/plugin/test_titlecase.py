# Copyright 2012 Christoph Reiter <reiter.christoph@gmail.com>,
#      2012,2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests.plugin import PluginTestCase
from quodlibet import config


class TTitlecase(PluginTestCase):
    def setUp(self):
        globals().update(vars(self.modules["Title Case"]))
        config.init()
        self.plugin = self.plugins["Title Case"].cls

    def test_all_caps(self):
        self.plugin.config_set("allow_all_caps", True)
        p = self.plugin("", "")
        self.assertEqual(p.activated("", "foo bar")[0][1], "Foo Bar")
        self.assertEqual(p.activated("", "FOO BAR")[0][1], "FOO BAR")

    def test_no_all_caps(self):
        self.plugin.config_set("allow_all_caps", False)
        p = self.plugin("", "")
        self.assertEqual(p.activated("", "foo bar")[0][1], "Foo Bar")
        self.assertEqual(p.activated("", "FOO BAR")[0][1], "Foo Bar")

    def test_humanise(self):
        self.plugin.config_set("human_title_case", True)
        self.plugin.config_set("allow_all_caps", False)
        p = self.plugin("", "")
        self.assertEqual(p.activated("", "foo bar")[0][1], "Foo Bar")
        self.assertEqual(p.activated("", "FOO the bAR")[0][1], "Foo the Bar")

    def tearDown(self):
        config.quit()
