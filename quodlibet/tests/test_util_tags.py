# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add

from quodlibet.util import tags


class TTagsSortkey(TestCase):

    def test_basic(self):
        t = ["album", "title", "artist", "part", "musicbrainz_trackid"]
        t.sort(key=tags.sortkey)
        expected = ["title", "artist", "album", "part", "musicbrainz_trackid"]
        self.failUnlessEqual(t, expected)

add(TTagsSortkey)
