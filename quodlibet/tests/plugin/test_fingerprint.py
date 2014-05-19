# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from gi.repository import Gtk

try:
    from gi.repository import Gst
    Gst
except ImportError:
    Gst = None
else:
    if not Gst.ElementFactory.find("chromaprint"):
        Gst = None

from tests.plugin import PluginTestCase
from tests import skipUnless
from quodlibet import config


@skipUnless(Gst)
class TAcoustidLookup(PluginTestCase):

    def setUp(self):
        config.init()
        self.mod = self.modules["AcoustidSearch"]

    def tearDown(self):
        config.quit()

    def test_parse_response_1(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release, score, src, asrc, mc, tags = parse(
            ACOUSTID_RESPONSE)[0]
        self.assertEqual(release, "14bb7304-b763-456b-a438-7bab619d41e3")
        self.assertEqual(src, 1)
        self.assertEqual(asrc, 7)

        self.assertEqual(tags["title"], u'Merkw\xfcrdig/Unangenehm')
        self.assertEqual(tags["artist"], u'Kinderzimmer Productions')
        self.assertEqual(tags["date"], u'2002-01')
        self.assertEqual(tags["tracknumber"], u'7/15')
        self.assertEqual(tags["discnumber"], u'1/1')
        self.assertTrue("musicbrainz_albumid" in tags)

    def test_parse_response_2(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release, score, src, asrc, mc, tags = parse(
            ACOUSTID_RESPONSE)[1]
        self.assertEqual(release, "ed90bff9-ab41-4669-8d44-13c78e678507")
        self.assertEqual(tags["albumartist"], u"Kinderzimmer Productions")
        self.assertEqual(tags["album"], u'Wir sind da wo oben ist')
        self.assertTrue("musicbrainz_albumid" in tags)

    def test_parse_response_2_mb(self):
        parse = self.mod.acoustid.parse_acoustid_response

        release, score, src, asrc, mc, tags = parse(
            ACOUSTID_RESPONSE)[1]
        self.assertTrue("musicbrainz_albumid" in tags)
        self.assertEqual(src, 6)
        self.assertEqual(
            tags["musicbrainz_trackid"],
            "bc970841-b7d9-415a-b7e2-645b1d263cc3")

    def test_plugin_prefs(self):
        self.mod.AcoustidSearch.PluginPreferences(Gtk.Window())


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
