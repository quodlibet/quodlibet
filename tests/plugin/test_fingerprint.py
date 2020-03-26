# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

from gi.repository import Gtk

try:
    from gi.repository import Gst
    Gst
except ImportError:
    Gst = None
else:
    chromaprint = Gst.ElementFactory.find("chromaprint")
    vorbisdec = Gst.ElementFactory.find("vorbisdec")


from tests.plugin import PluginTestCase
from tests import skipUnless, get_data_path
from quodlibet import config
from quodlibet.formats import MusicFile


@skipUnless(Gst and chromaprint and vorbisdec, "gstreamer plugins missing")
class TFingerprint(PluginTestCase):

    TIMEOUT = 20.0

    def setUp(self):
        config.init()
        self.mod = self.modules["AcoustidSearch"]

    def tearDown(self):
        config.quit()

        self.mod

    def test_analyze_silence(self):
        pipeline = self.mod.analyze.FingerPrintPipeline()
        song = MusicFile(get_data_path("silence-44-s.ogg"))
        done = []

        def callback(self, *args):
            done.extend(args)
        pipeline.start(song, callback)
        t = time.time()
        while not done and time.time() - t < self.TIMEOUT:
            Gtk.main_iteration_do(False)
        self.assertTrue(done)
        s, result, error = done
        # silence doesn't produce a fingerprint
        self.assertTrue(error)
        self.assertFalse(result)
        self.assertTrue(song is s)

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
            Gtk.main_iteration_do(False)

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
        self.assertEqual(tags["title"], u'Merkw\xfcrdig/Unangenehm')
        self.assertEqual(tags["artist"], u'Kinderzimmer Productions')
        self.assertEqual(tags["date"], u'2002-01')
        self.assertEqual(tags["tracknumber"], u'7/15')
        self.assertEqual(tags["discnumber"], "")
        self.assertTrue("musicbrainz_albumid" in tags)

    def test_parse_response_2(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release = parse(ACOUSTID_RESPONSE)[1]
        self.assertEqual(release.id, "ed90bff9-ab41-4669-8d44-13c78e678507")
        tags = release.tags
        self.assertEqual(tags["albumartist"], u"Kinderzimmer Productions")
        self.assertEqual(tags["album"], u'Wir sind da wo oben ist')
        self.assertTrue("musicbrainz_albumid" in tags)

    def test_parse_response_2_mb(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release = parse(ACOUSTID_RESPONSE)[1]
        self.assertTrue("musicbrainz_albumid" in release.tags)
        self.assertEqual(release.sources, 6)
        self.assertEqual(
            release.tags["musicbrainz_trackid"],
            "bc970841-b7d9-415a-b7e2-645b1d263cc3")


ACOUSTID_RESPONSE = {
u'status': u'ok', u'results': [{u'recordings': [{u'releases':
[{u'track_count': 15, u'title': u'Spex CD #15', u'country': u'DE', u'artists':
[{u'id': u'89ad4ac3-39f7-470e-963a-56509c546377', u'name': u'Various \
Artists'}], u'date': {u'year': 2002, u'month': 1}, u'releaseevents':
[{u'date': {u'year': 2002, u'month': 1}, u'country': u'DE'}], u'mediums':
[{u'position': 1, u'tracks': [{u'position': 7, u'title':
u'Merkw\xfcrdig/Unangenehm', u'id': u'7426320b-7646-3d06-bd5a-4762ecc0536b',
u'artists': [{u'id': u'ad728059-6823-4f98-a283-0dac3fb79a91', u'name':
u'Kinderzimmer Productions'}]}], u'track_count': 15, u'format': u'CD'}],
u'medium_count': 1, u'id': u'14bb7304-b763-456b-a438-7bab619d41e3'}],
u'title': u'Merkw\xfcrdig/Unangenehm', u'sources': 1, u'artists': [{u'id':
u'ad728059-6823-4f98-a283-0dac3fb79a91', u'name': u'Kinderzimmer \
Productions'}], u'duration': 272, u'id':
u'9104a525-40b2-40dc-83bf-c31c3d6d1861'}, {u'releases': [{u'track_count': 12,
u'title': u'Wir sind da wo oben ist', u'country': u'DE', u'artists': [{u'id':
u'ad728059-6823-4f98-a283-0dac3fb79a91', u'name': u'Kinderzimmer \
Productions'}], u'date': {u'year': 2002, u'day': 22, u'month': 2},
u'releaseevents': [{u'date': {u'year': 2002, u'day': 22, u'month': 2},
u'country': u'DE'}], u'mediums': [{u'position': 1, u'tracks': [{u'position':
11, u'title': u'Merkw\xfcrdig/unangenehm', u'id':
u'2520fe8a-005b-3a18-a8e2-ba9bef6009fb', u'artists': [{u'joinphrase':
u' feat. ', u'name': u'Kinderzimmer Productions', u'id':
u'ad728059-6823-4f98-a283-0dac3fb79a91'}, {u'id':
u'bf02bc50-251d-4a47-b5f9-ca462038ae8a', u'name': u'Tek Beton'}]}],
u'track_count': 12, u'format': u'CD'}], u'medium_count': 1, u'id':
u'ed90bff9-ab41-4669-8d44-13c78e678507'}], u'title':
u'Merkw\xfcrdig/unangenehm', u'sources': 6, u'artists': [{u'joinphrase': u' \
feat. ', u'name': u'Kinderzimmer Productions', u'id':
u'ad728059-6823-4f98-a283-0dac3fb79a91'}, {u'id':
u'bf02bc50-251d-4a47-b5f9-ca462038ae8a', u'name': u'Tek Beton'}], u'duration':
272, u'id': u'bc970841-b7d9-415a-b7e2-645b1d263cc3'}], u'score': 1.0, u'id':
u'f176baca-a4f7-4f39-906b-43136d9b3815'}]}
