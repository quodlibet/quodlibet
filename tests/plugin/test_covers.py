# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsnative

from tests.plugin import PluginTestCase
from quodlibet.formats import AudioFile


class TCovers(PluginTestCase):

    def test_cover_path(self):
        song = AudioFile({"musicbrainz_albumid": u"foobar"})
        song2 = AudioFile()

        # missing Soup
        if "lastfm-cover" in self.plugins:
            cls = self.plugins["lastfm-cover"].cls
            self.assertTrue(isinstance(cls(song).cover_path, fsnative))
            self.assertTrue(isinstance(cls(song2).cover_path, fsnative))

        # missing Soup
        if "musicbrainz-cover" in self.plugins:
            cls = self.plugins["musicbrainz-cover"].cls
            self.assertTrue(isinstance(cls(song).cover_path, fsnative))
            self.assertTrue(isinstance(cls(song2).cover_path, fsnative))
