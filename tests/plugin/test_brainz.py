# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import AudioFile

import pytest

from tests import skipUnless
from . import PluginTestCase, modules

brainz = modules.get("MusicBrainz lookup", None)

TEST_SEARCH_RESULT = \
{"release-count": 1, "release-list": [{"status": "Official", "artist-credit":
[{"artist": {"sort-name": "Necks, The", "id":
"51f8d454-f4a8-41e6-8bd7-a35921eeedd0", "name": "The Necks"}}],
"label-info-list": [{"catalog-number": "FOM 0008", "label": {"id":
"b887f682-e9e5-40d2-b4c7-cdbbcd2b3787", "name": "Fish of Milk"}}], "title":
"Athenaeum, Homebush, Quay & Raab", "country": "AU", "medium-count": 4,
"release-event-list": [{"date": "2002", "area": {"sort-name": "Australia",
"iso-3166-1-code-list": ["AU"], "id": "106e0bec-b638-3b37-b731-f53d507dc00e",
"name": "Australia"}}], "medium-list": [{}, {"disc-list": [], "format": "CD",
"track-list": [], "track-count": 1, "disc-count": 1}, {"disc-list": [],
"format": "CD", "track-list": [], "track-count": 1, "disc-count": 1},
{"disc-list": [], "format": "CD", "track-list": [], "track-count": 1,
"disc-count": 1}, {"disc-list": [], "format": "CD", "track-list": [],
"track-count": 1, "disc-count": 1}], "text-representation": {"language":
"eng", "script": "Latn"}, "ext:score": "100", "date": "2002",
"artist-credit-phrase": "The Necks", "release-group": {"secondary-type-list":
["Live"], "type": "Live", "id": "88e47489-a3d0-3344-864d-4b09188ba9e0",
"primary-type": "Album"}, "id": "3663a8a9-1c67-41c2-82c8-6a241d1558f7",
"asin": "B00007FKRD"}]}


TEST_SEARCH_RESULT_2 = \
{"release-count": 1, "release-list": [{"artist-credit": [{"artist":
{"alias-list": [{"alias": "\u30a2\u30d0", "locale": "ja", "primary":
"primary", "sort-name": "\u30a2\u30d0", "type": "Artist name"}, {"alias":
"\u15c5\u15fa\u15f7\u15c5", "sort-name": "\u15c5\u15fa\u15f7\u15c5", "type":
"Search hint"}, {"alias": "Abba", "sort-name": "Abba"}, {"alias":
"Bj\xf6rn + Benny + Anna + Frieda", "sort-name":
"Bj\xf6rn + Benny + Anna + Frieda"}],
"id": "d87e52c5-bb8d-4da8-b941-9f4928627dc8", "name": "ABBA", "sort-name":
"ABBA"}}], "artist-credit-phrase": "ABBA", "barcode": "602537784608",
"country": "XW", "date": "2014-04-04", "ext:score": "100", "id":
"9daa9d6e-7780-487f-9ef8-885755b73125", "label-info-list": [{"label": {"id":
"91edee57-cbb2-44f4-a6c7-a1a022aead78", "name": "Polar"}}], "medium-count": 1,
"medium-list": [{}, {"disc-count": 0, "disc-list": [], "format":
"Digital Media", "track-count": 19, "track-list": []}], "packaging": "None",
"release-event-list": [{"area": {"id": "525d4e18-3d00-31b9-a58b-a146a916de8f",
"iso-3166-1-code-list": ["XW"], "name": "[Worldwide]", "sort-name":
"[Worldwide]"}, "date": "2014-04-04"}], "release-group": {"id":
"b69d665a-3eee-39f3-b156-58b122232304", "primary-type": "Album",
"secondary-type-list": ["Compilation"], "type": "Compilation"}, "status":
"Official", "text-representation": {"language": "eng", "script": "Latn"},
"title": "Gold: Greatest Hits"}]}


TEST_DATA = \
{"status": "Official", "artist-credit": [{"artist": {"sort-name": "Autechre",
"id": "410c9baf-5469-44f6-9852-826524b80c61", "name": "Autechre"}}, " & ",
{"artist": {"sort-name": "Hafler Trio, The", "id":
"146c01d0-d3a2-44c3-acb5-9208bce75e14", "name": "The Hafler Trio"}}],
"label-info-list": [{"catalog-number": "pgram002", "label": {"sort-name":
"Phonometrography", "id": "a0759efa-f583-49ea-9a8d-d5bbce55541c", "name":
"Phonometrography"}}], "title": "\xe6\xb3o & h\xb3\xe6",
"release-event-count": 1, "medium-count": 2, "cover-art-archive": {"count":
"1", "front": "true", "back": "false", "artwork": "true"},
"release-event-list": [{"date": "2003-12-04", "area": {"sort-name":
"United Kingdom", "iso-3166-1-code-list": ["GB"], "id":
"8a754a16-0027-3a29-b6d7-2b40ea0481ed", "name": "United Kingdom"}}],
"medium-list": [{"position": "1", "title": "\xe6\xb3o", "track-list":
[{"artist-credit": [{"artist": {"sort-name": "Autechre", "id":
"410c9baf-5469-44f6-9852-826524b80c61", "name": "Autechre"}}, " & ",
{"artist": {"sort-name": "Hafler Trio, The", "id":
"146c01d0-d3a2-44c3-acb5-9208bce75e14", "name": "The Hafler Trio"}}],
"number": "1", "artist-credit-phrase": "Autechre & The Hafler Trio",
"recording": {"artist-credit": [{"artist": {"sort-name": "Autechre", "id":
"410c9baf-5469-44f6-9852-826524b80c61", "name": "Autechre"}}, " & ",
{"artist": {"sort-name": "Hafler Trio, The", "id":
"146c01d0-d3a2-44c3-acb5-9208bce75e14", "name": "The Hafler Trio"}}],
"length": "974546", "artist-credit-phrase": "Autechre & The Hafler Trio",
"id": "af87f070-238b-46c1-aa3e-f831ab91fa20", "title": "\xe6\xb3o"},
"length": "974546", "position": "1", "id":
"61af3e5a-14e0-350d-9826-a884c6e586b1", "track_or_recording_length":
"974546"}], "track-count": 1, "format": "CD"}, {"position": "2", "title":
"h\xb3\xe6", "track-list": [{"artist-credit": [{"artist": {"sort-name":
"Autechre", "id": "410c9baf-5469-44f6-9852-826524b80c61", "name":
"Autechre"}}, " & ", {"artist": {"sort-name": "Hafler Trio, The", "id":
"146c01d0-d3a2-44c3-acb5-9208bce75e14", "name": "The Hafler Trio"}}],
"number": "1", "artist-credit-phrase": "Autechre & The Hafler Trio",
"recording": {"artist-credit": [{"artist": {"sort-name": "Autechre", "id":
"410c9baf-5469-44f6-9852-826524b80c61", "name": "Autechre"}}, " & ",
{"artist": {"sort-name": "Hafler Trio, The", "id":
"146c01d0-d3a2-44c3-acb5-9208bce75e14", "name": "The Hafler Trio"}}],
"length": "922546", "artist-credit-phrase": "Autechre & The Hafler Trio",
"id": "5aff6309-2e02-4a47-9233-32d7dcc9a960", "title": "h\xb3\xe6"},
"length": "922546", "position": "1", "id":
"5f2031a2-c67d-3bec-8ae5-8d22847ab0a5", "track_or_recording_length":
"922546"}], "track-count": 1, "format": "CD"}], "text-representation":
{"language": "eng", "script": "Latn"}, "label-info-count": 1, "country": "GB",
"date": "2003-12-04", "artist-credit-phrase": "Autechre & The Hafler Trio",
"quality": "normal", "id": "59211ea4-ffd2-4ad9-9a4e-941d3148024a"}


# This isn't a complete/original ngs result, it just contains the minimum
# a pregap track and a normal track.
# The original release used here does also contain a pregap.
TEST_PREGAP = \
{"artist-credit": [],
"date": "2008-10-17",
"id": "87c070fc-90d5-39d1-b0ca-777236588378",
"medium-count": 1,
"medium-list": [{"format": "CD",
"position": "1",
"pregap": {"artist-credit": [
{"artist": {"id": "90b18d97-718b-4a95-982d-b14019d084c0",
"name": "Polarkreis 18",
"sort-name": "Polarkreis 18"}}],
"artist-credit-phrase": "Polarkreis 18",
"id": "2edd640f-2365-4440-b6e5-1f65dd72440b",
"length": "63000",
"number": "0",
"position": "0",
"recording": {"artist-credit": [
{"artist": {"id": "90b18d97-718b-4a95-982d-b14019d084c0",
"name": "Polarkreis 18",
"sort-name": "Polarkreis 18"}}],
"artist-credit-phrase": "Polarkreis 18",
"id": "e7f3e14b-7acf-47cc-bc26-d66269b821f4",
"length": "63000",
"title": "Herbstlied"},
"track_or_recording_length": "63000"},
"track-count": 1,
"track-list": [{"artist-credit": [
{"artist": {"id": "90b18d97-718b-4a95-982d-b14019d084c0",
"name": "Polarkreis 18",
"sort-name": "Polarkreis 18"}}],
"artist-credit-phrase": "Polarkreis 18",
"id": "03cdb09e-5a22-3e0d-88c9-da24793ccbab",
"length": "202106",
"number": "1",
"position": "1",
"recording": {"artist-credit": [
{"artist": {"id": "90b18d97-718b-4a95-982d-b14019d084c0",
"name": "Polarkreis 18",
"sort-name": "Polarkreis 18"}}],
"artist-credit-phrase": "Polarkreis 18",
"id": "b2bcb18f-ef9b-4e7e-ac4a-29234b3bac4e",
"length": "202106",
"title": "Tourist"},
"track_or_recording_length": "202106"}]}]}


@pytest.mark.network
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
            AudioFile({"artist": "garbage"}),
            AudioFile({"albumartist": "foo"}),
        ]

        self.assertEqual(get_artist(album), "foo")

        album = [
            AudioFile({"artist": "garbage"}),
            AudioFile({"artist": "bla"}),
        ]

        self.assertEqual(get_artist(album), None)

        album = [
            AudioFile({"artist": "bla"}),
            AudioFile({"artist": "bla"}),
        ]

        self.assertEqual(get_artist(album), "bla")

    def test_build_query(self):
        build_query = brainz.widgets.build_query

        album = [
            AudioFile({"artist": "garbage", "album": "blah"}),
            AudioFile({"albumartist": "foo"}),
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
        self.assertEqual(release.title, "\xe6\xb3o & h\xb3\xe6")
        self.assertTrue(release.is_single_artist)
        self.assertFalse(release.is_various_artists)
        self.assertTrue(release.artists)

    def test_release_tracks(self):
        Release = brainz.mb.Release

        release = Release(TEST_DATA)
        track = release.tracks[0]
        self.assertEqual(track.id, "61af3e5a-14e0-350d-9826-a884c6e586b1")
        self.assertEqual(len(track.artists), 2)
        self.assertEqual(track.title, "\xe6\xb3o")
        self.assertEqual(track.tracknumber, "1")
        self.assertEqual(track.discnumber, "1")
        self.assertEqual(track.track_count, 1)
        self.assertEqual(track.disctitle, "\xe6\xb3o")

    def test_labelid(self):
        Release = brainz.mb.Release

        release = Release(TEST_SEARCH_RESULT["release-list"][0])
        self.assertEqual(release.labelid, "FOM 0008")

        release = Release(TEST_SEARCH_RESULT_2["release-list"][0])
        self.assertEqual(release.labelid, "")

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
        self.assertEqual(meta["labelid"], "pgram002")

        apply_options(meta, True, False, False, False, False)
        dummy = AudioFile()
        apply_to_song(meta, dummy)
        self.assertEqual(dummy("album"), "\xe6\xb3o & h\xb3\xe6")
        self.assertEqual(dummy("date"), "2003")
        self.assertEqual(dummy("title"), "h\xb3\xe6")
        self.assertEqual(dummy("pgram002"), "")

    def test_build_mbids_labelid(self):
        Release = brainz.mb.Release
        build_song_data = brainz.widgets.build_song_data
        apply_options = brainz.widgets.apply_options
        apply_to_song = brainz.widgets.apply_to_song

        release = Release(TEST_DATA)
        track = release.tracks[1]
        meta = build_song_data(release, track)
        apply_options(meta, True, False, False, True, True)
        dummy = AudioFile()
        apply_to_song(meta, dummy)

        self.assertEqual(dummy("musicbrainz_releasetrackid"), track.id)
        self.assertEqual(dummy("musicbrainz_albumid"), release.id)
        self.assertEqual(
            dummy.list("musicbrainz_artistid"),
            ["410c9baf-5469-44f6-9852-826524b80c61",
             "146c01d0-d3a2-44c3-acb5-9208bce75e14"])
        self.assertEqual(dummy("labelid"), "pgram002")

    def test_pregap(self):
        Release = brainz.mb.Release

        release = Release(TEST_PREGAP)
        self.assertEqual(release.track_count, 2)
        self.assertEqual(len(release.tracks), 2)

        pregap = release.tracks[0]
        self.assertEqual(pregap.title, "Herbstlied")
        self.assertEqual(pregap.tracknumber, "0")
        self.assertEqual(pregap.track_count, 2)
        self.assertEqual(pregap.discnumber, "1")

        track = release.tracks[1]
        self.assertEqual(track.title, "Tourist")
        self.assertEqual(track.tracknumber, "1")
        self.assertEqual(track.track_count, 2)
        self.assertEqual(track.discnumber, "1")
