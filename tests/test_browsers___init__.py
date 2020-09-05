# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
from tests import TestCase

from quodlibet import browsers
browsers.init()


class TBrowsers(TestCase):
    def test_presence(self):
        self.failUnless(browsers.search)
        self.failUnless(browsers.paned)
        self.failUnless(browsers.iradio)
        self.failUnless(browsers.audiofeeds)
        self.failUnless(browsers.albums)
        self.failUnless(browsers.playlists)
        self.failUnless(browsers.filesystem)

    def test_get(self):
        self.failUnless(browsers.get("SearchBar") is browsers.search.SearchBar)
        self.failUnless(
            browsers.get("FileSystem") is browsers.filesystem.FileSystem)
        self.assertEqual(browsers.get("Paned"), browsers.paned.PanedBrowser)
        self.assertEqual(browsers.get("paned"), browsers.paned.PanedBrowser)
        self.assertEqual(browsers.get("panedbrowser"),
                         browsers.paned.PanedBrowser)

    def test_default(self):
        self.assertEqual(browsers.default, browsers.search.SearchBar)

    def test_name(self):
        self.assertEqual(browsers.name(browsers.search.SearchBar), "SearchBar")

    def test_get_invalid(self):
        self.assertRaises(ValueError, browsers.get, "DoesNotExist")

    def test_index(self):
        self.assertEqual(
            browsers.browsers[browsers.index("SearchBar")],
            browsers.search.SearchBar)
        self.assertEqual(
            browsers.browsers[browsers.index("FileSystem")],
            browsers.filesystem.FileSystem)

    def test_index_invalid(self):
        self.assertRaises(ValueError, browsers.index, "DoesNotExist")

    def test_migrate(self):
        self.failUnless(
            sys.modules["browsers.audiofeeds"] is browsers.audiofeeds)
        self.failUnless(
            sys.modules["browsers.iradio"] is browsers.iradio)

    def test_old_names(self):
        self.assertEqual(browsers.get("PanedBrowser"),
                         browsers.get("Paned"))
        self.assertEqual(browsers.get("PlaylistsBrowser"),
                         browsers.get("Playlists"))
