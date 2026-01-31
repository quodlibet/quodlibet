# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

from gi.repository import Gtk, GLib

try:
    from gi.repository import Gst

    Gst  # noqa
except ImportError:
    Gst = None
else:
    chromaprint = Gst.ElementFactory.find("chromaprint")
    vorbisdec = Gst.ElementFactory.find("vorbisdec")


from quodlibet import config
from quodlibet.formats import MusicFile
from tests import get_data_path, skipUnless, run_gtk_loop
from tests.plugin import PluginTestCase


@skipUnless(Gst and chromaprint and vorbisdec, "gstreamer plugins missing")
class TFingerprint(PluginTestCase):
    TIMEOUT = 20.0

    def setUp(self):
        config.init()
        self.mod = self.modules["AcoustidSearch"]

    def tearDown(self):
        config.quit()

        self.mod  # noqa

    def test_analyze_silence(self):
        pipeline = self.mod.analyze.FingerPrintPipeline()
        song = MusicFile(get_data_path("silence-44-s.ogg"))
        done = []

        def callback(self, *args):
            done.extend(args)

        pipeline.start(song, callback)
        t = time.time()
        while not done and time.time() - t < self.TIMEOUT:
            run_gtk_loop()
        assert done
        s, result, error = done
        # silence doesn't produce a fingerprint
        assert error
        assert not result
        assert song is s

    def test_analyze_pool(self):
        pool = self.mod.analyze.FingerPrintPool()
        song = MusicFile(get_data_path("silence-44-s.ogg"))

        events = []

        def handler(*args):
            events.append(args)

        pool.connect("fingerprint-started", handler, "start")
        pool.connect("fingerprint-done", handler, "done")
        pool.connect("fingerprint-error", handler, "error")
        pool.push(song)

        t = time.time()
        while len(events) < 2 and time.time() - t < self.TIMEOUT:
            run_gtk_loop()

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0][-1], "start")
        self.assertEqual(events[1][-1], "error")


@skipUnless(Gst and chromaprint, "gstreamer plugins missing")
class TAcoustidLookup(PluginTestCase):
    def setUp(self):
        config.init()
        self.mod = self.modules["AcoustidSearch"]

    def tearDown(self):
        config.quit()

    def test_parse_response_1(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release = parse(ACOUSTID_RESPONSE)[0]
        self.assertEqual(release.id, "14bb7304-b763-456b-a438-7bab619d41e3")
        self.assertEqual(release.sources, 1)
        self.assertEqual(release.all_sources, 7)

        tags = release.tags
        self.assertEqual(tags["title"], "Merkw\xfcrdig/Unangenehm")
        self.assertEqual(tags["artist"], "Kinderzimmer Productions")
        self.assertEqual(tags["date"], "2002-01")
        self.assertEqual(tags["tracknumber"], "7/15")
        self.assertEqual(tags["discnumber"], "")
        assert "musicbrainz_albumid" in tags

    def test_parse_response_2(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release = parse(ACOUSTID_RESPONSE)[1]
        self.assertEqual(release.id, "ed90bff9-ab41-4669-8d44-13c78e678507")
        tags = release.tags
        self.assertEqual(tags["albumartist"], "Kinderzimmer Productions")
        self.assertEqual(tags["album"], "Wir sind da wo oben ist")
        assert "musicbrainz_albumid" in tags

    def test_parse_response_2_mb(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release = parse(ACOUSTID_RESPONSE)[1]
        assert "musicbrainz_albumid" in release.tags
        self.assertEqual(release.sources, 6)
        self.assertEqual(
            release.tags["musicbrainz_trackid"], "bc970841-b7d9-415a-b7e2-645b1d263cc3"
        )


result = {
    "recordings": [
        {
            "releases": [
                {
                    "track_count": 15,
                    "title": "Spex CD #15",
                    "country": "DE",
                    "artists": [
                        {
                            "id": "89ad4ac3-39f7-470e-963a-56509c546377",
                            "name": "Various Artists",
                        }
                    ],
                    "date": {"year": 2002, "month": 1},
                    "releaseevents": [
                        {"date": {"year": 2002, "month": 1}, "country": "DE"}
                    ],
                    "mediums": [
                        {
                            "position": 1,
                            "tracks": [
                                {
                                    "position": 7,
                                    "title": "Merkw\xfcrdig/Unangenehm",
                                    "id": "7426320b-7646-3d06-bd5a-4762ecc0536b",
                                    "artists": [
                                        {
                                            "id": "ad728059-6823-4f98-a283-0dac3fb79a91",  # noqa: E501
                                            "name": "Kinderzimmer Productions",
                                        }
                                    ],
                                }
                            ],
                            "track_count": 15,
                            "format": "CD",
                        }
                    ],
                    "medium_count": 1,
                    "id": "14bb7304-b763-456b-a438-7bab619d41e3",
                }
            ],
            "title": "Merkw\xfcrdig/Unangenehm",
            "sources": 1,
            "artists": [
                {
                    "id": "ad728059-6823-4f98-a283-0dac3fb79a91",
                    "name": "Kinderzimmer Productions",
                }
            ],
            "duration": 272,
            "id": "9104a525-40b2-40dc-83bf-c31c3d6d1861",
        },
        {
            "releases": [
                {
                    "track_count": 12,
                    "title": "Wir sind da wo oben ist",
                    "country": "DE",
                    "artists": [
                        {
                            "id": "ad728059-6823-4f98-a283-0dac3fb79a91",
                            "name": "Kinderzimmer Productions",
                        }
                    ],
                    "date": {"year": 2002, "day": 22, "month": 2},
                    "releaseevents": [
                        {
                            "date": {"year": 2002, "day": 22, "month": 2},
                            "country": "DE",
                        }
                    ],
                    "mediums": [
                        {
                            "position": 1,
                            "tracks": [
                                {
                                    "position": 11,
                                    "title": "Merkw\xfcrdig/unangenehm",
                                    "id": "2520fe8a-005b-3a18-a8e2-ba9bef6009fb",
                                    "artists": [
                                        {
                                            "joinphrase": " feat. ",
                                            "name": "Kinderzimmer Productions",
                                            "id": "ad728059-6823-4f98-a283-0dac3fb79a91",  # noqa: E501
                                        },
                                        {
                                            "id": "bf02bc50-251d-4a47-b5f9-ca462038ae8a",  # noqa: E501
                                            "name": "Tek Beton",
                                        },
                                    ],
                                }
                            ],
                            "track_count": 12,
                            "format": "CD",
                        }
                    ],
                    "medium_count": 1,
                    "id": "ed90bff9-ab41-4669-8d44-13c78e678507",
                }
            ],
            "title": "Merkw\xfcrdig/unangenehm",
            "sources": 6,
            "artists": [
                {
                    "joinphrase": " feat. ",
                    "name": "Kinderzimmer Productions",
                    "id": "ad728059-6823-4f98-a283-0dac3fb79a91",
                },
                {
                    "id": "bf02bc50-251d-4a47-b5f9-ca462038ae8a",
                    "name": "Tek Beton",
                },
            ],
            "duration": 272,
            "id": "bc970841-b7d9-415a-b7e2-645b1d263cc3",
        },
    ],
    "score": 1.0,
    "id": "f176baca-a4f7-4f39-906b-43136d9b3815",
}
ACOUSTID_RESPONSE = {
    "status": "ok",
    "results": [result],
}
