# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import io
from bz2 import BZ2Compressor
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from collections.abc import Generator

import pytest

import quodlibet.config
from quodlibet.browsers.iradio import (
    InternetRadio,
    IRFile,
    QuestionBar,
    parse_taglist,
    parse_pls,
    parse_m3u,
    download_taglist,
)
from quodlibet.formats import AudioFile
from quodlibet.library import SongLibrary
from quodlibet.util import is_windows, is_osx
from tests import TestCase, skipIf, run_gtk_loop

quodlibet.config.RATINGS = quodlibet.config.HardCodedRatingsPrefs()

FAKE_URLS = ["http://example.com", "https://quodlibet.readthedocs.io"]


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
        assert not b.get_visible()


class TInternetRadio(TestCase):
    def setUp(self):
        quodlibet.config.init()
        # Ugh
        InternetRadio._InternetRadio__fav_stations = None
        InternetRadio._InternetRadio__stations = None
        self.browser = InternetRadio(SongLibrary())

    def test_can_filter(self):
        assert self.browser.can_filter("foo")
        assert self.browser.can_filter_text()

    def test_status_bar_text(self):
        assert self.browser.status_text(1) == "1 station"
        assert self.browser.status_text(101, 123) == "101 stations"

    @pytest.mark.network
    @skipIf(is_windows() or is_osx(), "Don't need to test downloads all the time")
    def test_click_add_station(self):
        self.browser._update_button.emit("clicked")
        assert not self.browser.has_stations
        # Run the actual download from real URL
        run_gtk_loop()
        assert self.browser.has_stations

    def test_qbar_visible_by_default(self):
        assert self.browser.qbar.is_visible()

    def test_qbar_invisible_with_faves(self):
        InternetRadio._InternetRadio__fav_stations = [1, 2, 3]
        self.browser = InternetRadio(SongLibrary())
        assert not self.browser.qbar.is_visible()
        self.browser.destroy()

    def tearDown(self):
        self.browser.destroy()
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
        assert not self.s("artist")
        self.s["title"] = "artist - title"
        self.s.multisong = False
        self.assertEqual(self.s("title"), "title")
        self.assertEqual(self.s.get("title"), "title")
        self.assertEqual(self.s("artist"), "artist")
        self.assertEqual(self.s.get("artist"), "artist")

    def test_title_split(self):
        assert self.s.multisong
        self.s["title"] = "artist - title"
        self.assertEqual(self.s("title"), self.s["title"])

    def test_format(self):
        self.assertEqual(self.s("~format"), self.s.format)
        self.s["audio-codec"] = "SomeCodec"
        assert "SomeCodec" in self.s("~format")
        assert self.s.format in self.s("~format")

    def test_people(self):
        self.s["title"] = "artist - title"
        self.s.multisong = False
        self.assertEqual(self.s("~people"), "artist")
        self.assertEqual(self.s("~~people~foo"), "artist")

    def testcan_write(self):
        assert self.s.can_change("title")
        self.s.streamsong = True
        assert not self.s.can_change("title")

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
        assert "title" not in new
        assert "artist" not in new


class Bzip2GetHandler(BaseHTTPRequestHandler):
    # Not thread-safe, but won't be an issue here
    compressor = BZ2Compressor()

    def do_GET(self) -> None:
        uris = [f"uri={url}" for url in FAKE_URLS]
        content = "\n".join(uris).encode("utf-8")
        self.compressor.compress(content)
        bz2 = self.compressor.flush()
        self.send_response(200)
        self.send_header("Content-Length", str(len(bz2)))
        self.send_header("Content-type", "application/x-bzip2")
        self.end_headers()
        self.wfile.write(bz2)


@pytest.fixture
def test_server() -> Generator[HTTPServer, None, None]:
    server = HTTPServer(("localhost", 0), Bzip2GetHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()


def test_download_tags(test_server):
    received = []
    host, port = test_server.server_address
    url = f"http://{host}:{port:d}"

    ret = list(download_taglist(url, received.extend, None))
    run_gtk_loop()
    assert len(ret), "No stations"
    assert all(ret), "Got some falsey stations"
    assert received, f"No stations received from {url}"
    assert {s("~filename") for s in received} == set(FAKE_URLS)
