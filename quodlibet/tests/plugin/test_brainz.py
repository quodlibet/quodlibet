# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.formats import AudioFile

from tests import skipUnless
from . import PluginTestCase, modules

brainz = modules.get("MusicBrainz lookup", None)


@skipUnless(brainz, "brainz plugin not loaded")
class TBrainz(PluginTestCase):
    """Test CustomCommands plugin and associated classes"""

    def setUp(self):
        globals()["brainz"] = self.modules["MusicBrainz lookup"]

    def test_get_trackcount(self):
        get_trackcount = brainz.widgets.get_trackcount

        album = [
            AudioFile({"tracknumber": "7"}),
            AudioFile({"tracknumber": "garbage"}),
            AudioFile({"tracknumber": "10/42"}),
        ]
        self.assertEqual(get_trackcount([]), 0)
        self.assertEqual(get_trackcount(album), 42)

    def test_get_artist(self):
        get_artist = brainz.widgets.get_artist

        self.assertEqual(get_artist([]), None)

        album = [
            AudioFile({"artist": u"garbage"}),
            AudioFile({"albumartist": u"foo"}),
        ]

        self.assertEqual(get_artist(album), u"foo")

        album = [
            AudioFile({"artist": u"garbage"}),
            AudioFile({"artist": u"bla"}),
        ]

        self.assertEqual(get_artist(album), None)

        album = [
            AudioFile({"artist": u"bla"}),
            AudioFile({"artist": u"bla"}),
        ]

        self.assertEqual(get_artist(album), u"bla")
