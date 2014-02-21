# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests.plugin import PluginTestCase
from quodlibet.formats._audio import AudioFile

brainz = None


class TBrainz(PluginTestCase):
    """Test CustomCommands plugin and associated classes"""

    def setUp(self):
        globals()["brainz"] = self.modules["MusicBrainz lookup"]

    def test(self):
        album = [
            AudioFile({"tracknumber": "7"}),
            AudioFile({"tracknumber": "garbage"}),
            AudioFile({"tracknumber": "10/42"}),
        ]
        self.assertEqual(brainz.get_trackcount([]), 0)
        self.assertEqual(brainz.get_trackcount(album), 42)
