# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import json
from pathlib import Path

from quodlibet import config
from quodlibet.browsers.soundcloud.api import SoundcloudApiClient
from quodlibet.browsers.soundcloud.library import SoundcloudLibrary
from quodlibet.browsers.soundcloud.query import SoundcloudQuery
from tests import TestCase

PERMALINK = "https://soundcloud.com/"
"kerstineden/banging-techno-sets-098-kerstin-eden-02-2015"

AVATAR_URL = u'https://i1.sndcdn.com/avatars-000127864033-q70sz6-large.jpg'

TEST_DATA_PATH = Path(__file__).parent.parent / "tests" / "data"


class TSoundcloudLibrary(TestCase):
    class FakeClient(SoundcloudApiClient):

        def get_tracks(self, query):
            self._on_track_data(None, [self._track], None)

        def __init__(self):
            super().__init__()
            with open(TEST_DATA_PATH / "soundcloud_track_response.json") as f:
                self._track = json.load(f)

        def authenticate_user(self):
            pass

    def setUp(self):
        SoundcloudLibrary.librarian = None
        self.lib = SoundcloudLibrary(self.FakeClient())

    def tearDown(self):
        self.lib.destroy()

    @classmethod
    def setUpClass(cls):
        config.RATINGS = config.HardCodedRatingsPrefs()

    def test_parse(self):
        lib = self.lib
        lib.query_with_refresh(SoundcloudQuery("dummy search"))
        songs = list(lib._contents.values())
        assert len(songs) == 1
        s = songs[0]
        assert s("artist") == "ANDY C ram"
        assert s("date") == "2015-06-29"
        assert s("~year") == "2015"
        assert s("~#download_count") == 0
        assert s("~#playback_count") == 363310
        assert s("~#favoritings_count") == 10061
        assert s("~#rating") == 1.0
        assert s("~#playcount") == 4
        assert int(s("~#bitrate")) == 128

    def test_artwork_url(self):
        lib = SoundcloudLibrary(self.FakeClient())
        lib.query_with_refresh(SoundcloudQuery(""))
        s = list(lib._contents.values())[0]
        url = s("artwork_url")
        assert url == "https://i1.sndcdn.com/artworks-000121689963-0b0pdr-t500x500.jpg"
