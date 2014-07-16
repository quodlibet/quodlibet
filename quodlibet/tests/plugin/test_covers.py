# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation


from tests.plugin import PluginTestCase
from quodlibet.formats._audio import AudioFile
from quodlibet.util.path import is_fsnative


class TCovers(PluginTestCase):

    def test_cover_path(self):
        song = AudioFile({"musicbrainz_albumid": u"foobar"})
        song2 = AudioFile()

        # missing Soup
        if "lastfm-cover" in self.plugins:
            cls = self.plugins["lastfm-cover"].cls
            self.assertTrue(is_fsnative(cls(song).cover_path))
            self.assertTrue(is_fsnative(cls(song2).cover_path))

        # missing Soup
        if "musicbrainz-cover" in self.plugins:
            cls = self.plugins["musicbrainz-cover"].cls
            self.assertTrue(is_fsnative(cls(song).cover_path))
            self.assertTrue(is_fsnative(cls(song2).cover_path))
