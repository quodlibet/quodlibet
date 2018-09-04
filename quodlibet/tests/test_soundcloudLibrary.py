# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config
from quodlibet.browsers.soundcloud.api import SoundcloudApiClient
from quodlibet.browsers.soundcloud.library import SoundcloudLibrary
from tests import TestCase

PERMALINK = "https://soundcloud.com/"
"kerstineden/banging-techno-sets-098-kerstin-eden-02-2015"

AVATAR_URL = u'https://i1.sndcdn.com/avatars-000127864033-q70sz6-large.jpg'

TRACK = {
    u'reposts_count': 134,
    u'attachments_uri':
        u'https://api.soundcloud.com/tracks/193910405/attachments',
    u'video_url': None, u'track_type': None, u'release_month': 3,
    u'original_format': u'mp3',
    u'uri': u'https://api.soundcloud.com/tracks/193910405',
    u'label_name': None, u'duration': 3944440, u'id': 193910405,
    u'streamable': True, u'user_id': 313827, u'user_favorite': True,
    u'title': u'Banging Techno Sets :: 098 Kerstin Eden // 03-2015',
    u'favoritings_count': 882, u'commentable': True,
    u'comment_count': 39,
    u'download_url': u'https://api.soundcloud.com/tracks/193910405/download',
    u'label_id': None, u'downloadable': True,
    u'last_modified': u'2015/03/02 22:32:30 +0000',
    u'waveform_url': u'https://w1.sndcdn.com/Ugov31icy2XG_m.png',
    u'sharing': u'public',
    u'description': u'Banging Techno sets :: 098 '
                    u'>> Kerstin Eden // Timao \n'
                    u'fnoob techno - http://www.fnoobtechno.com/radio',
    u'release_day': 2, u'purchase_url': None,
    u'permalink': u'banging-techno-sets-098-kerstin-eden-02-2015',
    u'purchase_title': None,
    u'stream_url': u'https://api.soundcloud.com/tracks/193910405/stream',
    u'key_signature': u'',
    u'user': {u'username': u'Kerstin Eden', u'kind': u'user',
              u'uri': u'https://api.soundcloud.com/users/313827',
              u'permalink': u'kerstineden',
              u'avatar_url': AVATAR_URL,
              u'last_modified': u'2016/02/25 14:21:56 +0000',
              u'permalink_url': u'http://soundcloud.com/kerstineden',
              u'id': 313827}, u'genre': u'banging techno',
    u'isrc': None, u'download_count': 2062,
    u'permalink_url': PERMALINK,
    u'kind': u'track', u'playback_count': 23656,
    u'license': u'all-rights-reserved',
    u'artwork_url':
        u'https://i1.sndcdn.com/artworks-000108682375-q4j7y6-large.jpg',
    u'embeddable_by': u'all', u'bpm': None, u'state': u'finished',
    u'original_content_size': 157768013, u'release_year': 2015,
    u'user_playback_count': 4, u'release': u'',
    u'tag_list': u'"kerstin eden" eden nimmersatt abstract frankfurt Techno',
    u'created_at': u'2015/03/02 22:31:30 +0000'}


class TSoundcloudLibrary(TestCase):
    class FakeClient(SoundcloudApiClient):

        def get_tracks(self, query):
            self._on_track_data(None, [TRACK], None)

        def __init__(self):
            super(TSoundcloudLibrary.FakeClient, self).__init__()

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
        lib.query_with_refresh("dummy search")
        songs = list(lib._contents.values())
        self.failUnlessEqual(len(songs), 1)
        s = songs[0]
        self.failUnlessEqual(s("artist"), "Kerstin Eden")
        self.failUnlessEqual(s("date"), "2015-03-02")
        self.failUnlessEqual(s("~#download_count"), 2062)
        self.failUnlessEqual(s("~#playback_count"), 23656)
        self.failUnlessEqual(s("~#favoritings_count"), 882)
        self.failUnlessEqual(s("~#rating"), 1.0)
        self.failUnlessEqual(s("~#playcount"), 4)
        assert int(s("~#bitrate")) == 319

    def test_artwork_url(self):
        lib = SoundcloudLibrary(self.FakeClient())
        lib.query_with_refresh("")
        s = list(lib._contents.values())[0]
        self.failUnlessEqual(
            s("artwork_url"),
            "https://i1.sndcdn.com/artworks-000108682375-q4j7y6-t500x500.jpg")
