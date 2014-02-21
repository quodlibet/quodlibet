# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.formats._audio import AudioFile
from . import PluginTestCase, modules, skipUnless

brainz = modules.get("MusicBrainz lookup", None)


@skipUnless(brainz, "brainz plugin not loaded")
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
