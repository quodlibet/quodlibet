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


TEST_DATA = \
{'status': 'Official', 'artist-credit': [{'artist': {'sort-name':
'Autechre', 'id': '410c9baf-5469-44f6-9852-826524b80c61', 'name':
'Autechre'}}, ' & ', {'artist': {'sort-name': 'Hafler Trio, The', 'id':
'146c01d0-d3a2-44c3-acb5-9208bce75e14', 'name': 'The Hafler Trio'}}],
'medium-list': [{'position': '1', 'title': u'\xe6\xb3o', 'track-list':
[{'artist-credit': [{'artist': {'sort-name': 'Autechre', 'id':
'410c9baf-5469-44f6-9852-826524b80c61', 'name': 'Autechre'}}, ' & ',
{'artist': {'sort-name': 'Hafler Trio, The', 'id':
'146c01d0-d3a2-44c3-acb5-9208bce75e14', 'name': 'The Hafler Trio'}}],
'number': '1', 'artist-credit-phrase': 'Autechre & The Hafler Trio',
'recording': {'artist-credit': [{'artist': {'sort-name': 'Autechre', 'id':
'410c9baf-5469-44f6-9852-826524b80c61', 'name': 'Autechre'}}, ' & ',
{'artist': {'sort-name': 'Hafler Trio, The', 'id':
'146c01d0-d3a2-44c3-acb5-9208bce75e14', 'name': 'The Hafler Trio'}}],
'length': '974546', 'artist-credit-phrase': 'Autechre & The Hafler Trio',
'id': 'af87f070-238b-46c1-aa3e-f831ab91fa20', 'title': u'\xe6\xb3o'},
'length': '974546', 'position': '1', 'id':
'61af3e5a-14e0-350d-9826-a884c6e586b1', 'track_or_recording_length':
'974546'}], 'track-count': 1, 'format': 'CD'}, {'position': '2', 'title':
u'h\xb3\xe6', 'track-list': [{'artist-credit': [{'artist': {'sort-name':
'Autechre', 'id': '410c9baf-5469-44f6-9852-826524b80c61', 'name':
'Autechre'}}, ' & ', {'artist': {'sort-name': 'Hafler Trio, The', 'id':
'146c01d0-d3a2-44c3-acb5-9208bce75e14', 'name': 'The Hafler Trio'}}],
'number': '1', 'artist-credit-phrase': 'Autechre & The Hafler Trio',
'recording': {'artist-credit': [{'artist': {'sort-name': 'Autechre', 'id':
'410c9baf-5469-44f6-9852-826524b80c61', 'name': 'Autechre'}}, ' & ',
{'artist': {'sort-name': 'Hafler Trio, The', 'id':
'146c01d0-d3a2-44c3-acb5-9208bce75e14', 'name': 'The Hafler Trio'}}],
'length': '922546', 'artist-credit-phrase': 'Autechre & The Hafler Trio',
'id': '5aff6309-2e02-4a47-9233-32d7dcc9a960', 'title': u'h\xb3\xe6'},
'length': '922546', 'position': '1', 'id':
'5f2031a2-c67d-3bec-8ae5-8d22847ab0a5', 'track_or_recording_length':
'922546'}], 'track-count': 1, 'format': 'CD'}], 'title': u'\xe6\xb3o &'
u'h\xb3\xe6', 'release-event-count': 1, 'medium-count': 2, 'cover-art-archive':
{'count': '1', 'front': 'true', 'back': 'false', 'artwork': 'true'},
'release-event-list': [{'date': '2003-12-04', 'area': {'sort-name': 'United '
'Kingdom', 'iso-3166-1-code-list': ['GB'], 'id':
'8a754a16-0027-3a29-b6d7-2b40ea0481ed', 'name': 'United Kingdom'}}],
'text-representation': {'language': 'eng', 'script': 'Latn'}, 'country': 'GB',
'date': '2003-12-04', 'artist-credit-phrase': 'Autechre & The Hafler Trio',
'quality': 'normal', 'id': '59211ea4-ffd2-4ad9-9a4e-941d3148024a'}


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

    def test_build_query(self):
        build_query = brainz.widgets.build_query

        album = [
            AudioFile({"artist": u"garbage", "album": "blah"}),
            AudioFile({"albumartist": u"foo"}),
        ]

        self.assertEqual(
            build_query(album), '"blah" AND artist:"foo" AND tracks:2')

    def test_release(self):
        Release = brainz.mb.Release

        release = Release(TEST_DATA)
        self.assertEqual(release.id, "59211ea4-ffd2-4ad9-9a4e-941d3148024a")
        self.assertEqual(release.date, "2003-12-04")
        self.assertEqual(release.medium_format, "CD")
        self.assertEqual(release.country, "GB")
        self.assertEqual(release.disc_count, 2)
        self.assertEqual(release.track_count, 2)
        self.assertEqual(len(release.tracks), 2)
        self.assertEqual(release.title, u'\xe6\xb3o &h\xb3\xe6')
        self.assertTrue(release.is_single_artist)
        self.assertFalse(release.is_various_artists)
        self.assertTrue(release.artists)

    def test_release_tracks(self):
        Release = brainz.mb.Release

        release = Release(TEST_DATA)
        track = release.tracks[0]
        self.assertEqual(track.id, "61af3e5a-14e0-350d-9826-a884c6e586b1")
        self.assertEqual(len(track.artists), 2)
        self.assertEqual(track.title, u'\xe6\xb3o')
        self.assertEqual(track.tracknumber, "1")
        self.assertEqual(track.discnumber, "1")
        self.assertEqual(track.track_count, 1)
        self.assertEqual(track.disctitle, u"\xe6\xb3o")

    def test_release_artist(self):
        Release = brainz.mb.Release

        release = Release(TEST_DATA)
        artist = release.artists[0]

        self.assertEqual(artist.id, "410c9baf-5469-44f6-9852-826524b80c61")
        self.assertEqual(artist.name, "Autechre")
        self.assertEqual(artist.sort_name, "Autechre")
        self.assertFalse(artist.is_various)

    def test_build_metadata(self):
        Release = brainz.mb.Release
        build_song_data = brainz.widgets.build_song_data
        apply_options = brainz.widgets.apply_options
        apply_to_song = brainz.widgets.apply_to_song

        release = Release(TEST_DATA)
        track = release.tracks[1]
        meta = build_song_data(release, track)
        self.assertEqual(meta["tracknumber"], "1/1")
        self.assertEqual(meta["discnumber"], "2/2")

        apply_options(meta, True, False, False, False)
        dummy = AudioFile()
        apply_to_song(meta, dummy)
        self.assertEqual(dummy("album"), u'\xe6\xb3o &h\xb3\xe6')
        self.assertEqual(dummy("date"), u'2003')
        self.assertEqual(dummy("title"), u'h\xb3\xe6')
