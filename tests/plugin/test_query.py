# Copyright 2016 Ryan Dellenbaugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from tests.plugin import PluginTestCase
from tests import mkstemp

from quodlibet.plugins import Plugin
from quodlibet.plugins.query import QueryPlugin, QueryPluginError
from quodlibet.plugins.query import QUERY_HANDLER
from quodlibet.formats import AudioFile


class FakeQueryPlugin(QueryPlugin):
    PLUGIN_ID = "fake_query_plugin"
    PLUGIN_NAME = "fake_query"

    key = "fake"

    def search(self, data, body):
        return True

fake_plugin = Plugin(FakeQueryPlugin)


class TQueryPlugins(PluginTestCase):

    def test_handler(self):
        self.failUnlessRaises(KeyError, QUERY_HANDLER.get_plugin, "fake")
        QUERY_HANDLER.plugin_enable(fake_plugin)
        self.failUnless(
            isinstance(QUERY_HANDLER.get_plugin("fake"), FakeQueryPlugin))
        QUERY_HANDLER.plugin_disable(fake_plugin)
        self.failUnlessRaises(KeyError, QUERY_HANDLER.get_plugin, "fake")

    def test_conditional(self):
        if "conditional_query" not in self.plugins:
            return

        plugin = self.plugins["conditional_query"].cls()

        self.failUnlessRaises(QueryPluginError, plugin.parse_body, None)
        self.failUnlessRaises(QueryPluginError, plugin.parse_body, "")
        self.failUnlessRaises(QueryPluginError, plugin.parse_body,
                              "single=query")
        self.failUnlessRaises(QueryPluginError, plugin.parse_body,
                              "a=first,b=second")
        self.failUnlessRaises(QueryPluginError, plugin.parse_body,
                              "invalid/query")

        self.failUnless(plugin.parse_body("a=first,b=second,c=third"))
        self.failUnless(plugin.parse_body("@(ext),#(numcmp > 0),!negation"))

        body = plugin.parse_body("artist=a, genre=rock, genre=classical")

        self.failUnless(plugin.search(
            AudioFile({"artist": u"a", "genre": u"rock"}), body))
        self.failIf(plugin.search(
            AudioFile({"artist": u"a", "genre": u"classical"}), body))
        self.failIf(plugin.search(
            AudioFile({"artist": u"b", "genre": u"rock"}), body))
        self.failUnless(plugin.search(
            AudioFile({"artist": u"b", "genre": u"classical"}), body))

    def test_savedsearch(self):
        if "include_saved" not in self.plugins:
            return

        plugin = self.plugins["include_saved"].cls()

        self.failUnlessRaises(QueryPluginError, plugin.parse_body, None)

        try:
            fd, filename = mkstemp(text=True)
            file = os.fdopen(fd, "w")
            file.write("artist=a\nQuery 1\ngenre=classical\nAnother query")
            file.close()

            self.failUnlessRaises(QueryPluginError, plugin.parse_body,
                                  "missing query")
            self.failUnlessRaises(QueryPluginError, plugin.parse_body,
                                  "artist=a")

            self.failUnless(plugin.parse_body("  quEry 1",
                            query_path_=filename))

            query1 = plugin.parse_body("Query 1", query_path_=filename)
            query2 = plugin.parse_body("another query", query_path_=filename)
            song = AudioFile({"artist": u"a", "genre": u"dance"})
            self.failUnless(plugin.search(song, query1))
            self.failIf(plugin.search(song, query2))
        finally:
            os.remove(filename)

    def test_python_expression(self):
        if "python_query" not in self.plugins:
            return

        plugin = self.plugins["python_query"].cls()

        self.failUnlessRaises(QueryPluginError, plugin.parse_body, None)
        self.failUnlessRaises(QueryPluginError, plugin.parse_body, "")
        self.failUnlessRaises(QueryPluginError, plugin.parse_body, "\\")
        self.failUnlessRaises(QueryPluginError, plugin.parse_body, "unclosed[")
        self.failUnlessRaises(QueryPluginError, plugin.parse_body, "return s")
        self.failUnless(plugin.parse_body("3"))
        self.failUnless(plugin.parse_body("s"))

        body1 = plugin.parse_body("s('~#rating') > 0.5")
        body2 = plugin.parse_body(
            "s('genre').lower()[2:] in ('rock', 'pop')")
        body3 = plugin.parse_body("len(s('title')) < 6")

        song1 = AudioFile({"title": "foobar", "~#rating": 0.8,
                           "genre": "jazz"})
        song2 = AudioFile({"title": "baz", "~#rating": 0.4, "genre": "aapop"})

        self.failUnless(plugin.search(song1, body1))
        self.failIf(plugin.search(song1, body2))
        self.failIf(plugin.search(song1, body3))
        self.failIf(plugin.search(song2, body1))
        self.failUnless(plugin.search(song2, body2))
        self.failUnless(plugin.search(song2, body3))
