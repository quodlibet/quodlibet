# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util.tags import sortkey, readable


class TTags(TestCase):

    def test_basic(self):
        t = ["album", "title", "artist", "part", "musicbrainz_trackid"]
        t.sort(key=sortkey)
        expected = ["title", "artist", "album", "part", "musicbrainz_trackid"]
        self.failUnlessEqual(t, expected)

    def test_readable(self):
        self.assertEqual(readable("artistsort"), "artist (sort)")
        self.assertEqual(readable("~people:roles"), "people (roles)")
        self.assertEqual(readable("~peoplesort:roles"), "people (sort, roles)")
        self.assertEqual(readable("artist", plural=True), "artists")
        self.assertEqual(readable("artistsort", plural=True), "artists (sort)")
        self.assertEqual(readable("~"), "Invalid tag")
