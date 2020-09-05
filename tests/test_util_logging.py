# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util.logging import Logs


class TLogging(TestCase):

    def test_logging(self):
        l = Logs()
        self.assertEqual(l.get_content(), [])
        l.log("foo")
        l.log("bar")
        self.assertEqual(l.get_content(), ["foo", "bar"])
        l.log("quux")
        self.assertEqual(l.get_content(), ["foo", "bar", "quux"])

    def test_binary(self):
        l = Logs()
        l.log(b"\xff")
        self.assertEqual(l.get_content(), [u"\ufffd"])

    def test_max_logs(self):
        l = Logs(2)
        l.log("foo")
        l.log("bar")
        self.assertEqual(l.get_content(), ["foo", "bar"])
        l.log("quux")
        self.assertEqual(l.get_content(), ["bar", "quux"])

    def test_limit(self):
        l = Logs()
        l.log("foo")
        l.log("bar")
        self.assertEqual(l.get_content(limit=1), ["bar"])
        self.assertEqual(l.get_content(limit=2), ["foo", "bar"])

    def test_clear(self):
        l = Logs(2)
        l.log("foo")
        l.log("bar")
        l.clear()
        self.assertEqual(l.get_content(), [])
        l.clear()
        self.assertEqual(l.get_content(), [])

    def test_cat(self):
        l = Logs()
        l.log("foo")
        l.log("bar", "cat5")
        l.log("quux", "cat5")
        self.assertEqual(l.get_content(), ["foo", "bar", "quux"])
        self.assertEqual(l.get_content("cat5"), ["bar", "quux"])
        self.assertEqual(l.get_content("cat5", limit=2), ["bar", "quux"])
        self.assertEqual(l.get_content("cat5", limit=1), ["quux"])
