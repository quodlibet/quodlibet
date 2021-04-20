# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import io

from quodlibet.util import is_windows, is_osx
from tests import TestCase, skipIf

from quodlibet.library import SongLibrary
from quodlibet.formats import AudioFile
from quodlibet.browsers.iradio import (InternetRadio, IRFile, QuestionBar,
                                       parse_taglist, parse_pls, parse_m3u,
                                       download_taglist, STATION_LIST_URL)
import quodlibet.config
from gi.repository import Gtk

quodlibet.config.RATINGS = quodlibet.config.HardCodedRatingsPrefs()


def test_parse_taglist():
    parse_taglist(b"")
    stations = parse_taglist(b"""\
uri=http://foo.bar
artist=foo
artist=bar
~listenerpeak=42
""")

    assert len(stations) == 1
    assert stations[0]["~#listenerpeak"] == 42
    assert stations[0].list("artist") == ["foo", "bar"]


class FakeTask:
    def __init__(self):
        self.pulsed = 0

    def pulse(self):
        self.pulsed += 1


def test_parse_pls():
    f = io.BytesIO(b"""\
[playlist]
Title1=Here enter name of the station
File1=http://stream2.streamq.net:8020/
NumberOfEntries=1
""")

    r = parse_pls(f)
    assert len(r) == 1
    assert r[0]("~uri") == "http://stream2.streamq.net:8020/"
    assert r[0]("title") == "Here enter name of the station"


def test_parse_m3u():
    f = io.BytesIO(b"""\
#EXTM3U

#EXTINF:123, Sample artist - Sample title
http://stream2.streamq.net:8020/
""")

    r = parse_m3u(f)
    assert len(r) == 1
    assert r[0]("~uri") == "http://stream2.streamq.net:8020/"


class TQuestionBar(TestCase):

    def test_main(self):
        b = QuestionBar()
        self.assertFalse(b.get_visible())


class TInternetRadio(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.bar = InternetRadio(SongLibrary())

    def test_can_filter(self):
        self.assertTrue(self.bar.can_filter("foo"))
        self.assertTrue(self.bar.can_filter_text())

    def test_status_bar_text(self):
        self.assertEqual(self.bar.status_text(1), "1 station")
        self.assertEqual(self.bar.status_text(101, 123), "101 stations")

    def tearDown(self):
        self.bar.destroy()
        quodlibet.config.quit()


class TIRFile(TestCase):
    def setUp(self):
        self.s = IRFile("http://foo.bar")

    def test_website(self):
        self.s["website"] = "abc"
        self.assertEqual(self.s.get("artist"), "abc")
        self.assertEqual(self.s("artist"), "abc")
        self.assertEqual(self.s.list("artist"), ["abc"])

    def test_organisation(self):
        self.s["organization"] = "foo"
        self.assertEqual(self.s("title"), "foo")
        self.assertEqual(self.s.get("title"), "foo")

    def test_title_split_stream(self):
        self.assertFalse(self.s("artist"))
        self.s["title"] = "artist - title"
        self.s.multisong = False
        self.assertEqual(self.s("title"), "title")
        self.assertEqual(self.s.get("title"), "title")
        self.assertEqual(self.s("artist"), "artist")
        self.assertEqual(self.s.get("artist"), "artist")

    def test_title_split(self):
        self.assertTrue(self.s.multisong)
        self.s["title"] = "artist - title"
        self.assertEqual(self.s("title"), self.s["title"])

    def test_format(self):
        self.assertEqual(self.s("~format"), self.s.format)
        self.s["audio-codec"] = "SomeCodec"
        self.assertTrue("SomeCodec" in self.s("~format"))
        self.assertTrue(self.s.format in self.s("~format"))

    def test_people(self):
        self.s["title"] = "artist - title"
        self.s.multisong = False
        self.assertEqual(self.s("~people"), "artist")
        self.assertEqual(self.s("~~people~foo"), "artist")

    def testcan_write(self):
        self.failUnless(self.s.can_change("title"))
        self.s.streamsong = True
        self.failIf(self.s.can_change("title"))

    def test_dump_to_file(self):
        self.s["title"] = "artist - title"
        self.s.multisong = False
        dump = self.s.to_dump()
        new = AudioFile()
        new.from_dump(dump)
        self.assertEqual(new["title"], "title")
        self.assertEqual(new["artist"], "artist")

        del self.s["title"]
        dump = self.s.to_dump()
        new = AudioFile()
        new.from_dump(dump)
        self.assertTrue("title" not in new)
        self.assertTrue("artist" not in new)

    @skipIf(is_windows() or is_osx(), "Don't need to test all the time")
    def test_download_tags(self):
        self.received = []
        # TODO: parameterise this, spin up a local HTTP server, inject this.
        url = STATION_LIST_URL

        def cb(data):
            assert data
            self.received += data

        ret = list(download_taglist(cb, None))
        run_loop()
        assert all(ret)
        assert self.received, "No stations received from %s" % url
        assert len(self.received) > 100
        # TODO: some more targeted tests


def run_loop():
    while Gtk.events_pending():
        Gtk.main_iteration()
