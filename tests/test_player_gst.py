# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import contextlib

try:
    from gi.repository import Gst
except ImportError:
    Gst = None

from tests import TestCase, skipUnless, get_data_path

try:
    from quodlibet.player.gstbe.util import gstreamer_sink
    from quodlibet.player.gstbe.util import parse_gstreamer_taglist
    from quodlibet.player.gstbe.util import find_audio_sink
    from quodlibet.player.gstbe.prefs import GstPlayerPreferences
except ImportError:
    pass

from quodlibet.player import PlayerError
from quodlibet.util import sanitize_tags, is_flatpak
from quodlibet.formats import MusicFile
from quodlibet import config


@contextlib.contextmanager
def ignore_gst_errors():
    old = Gst.debug_get_default_threshold()
    Gst.debug_set_default_threshold(Gst.DebugLevel.NONE)
    yield
    Gst.debug_set_default_threshold(old)


@skipUnless(Gst, "GStreamer missing")
class TGstPlayerPrefs(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_main(self):
        widget = GstPlayerPreferences(None, True)
        widget.destroy()


@skipUnless(Gst, "GStreamer missing")
class TGStreamerSink(TestCase):
    def test_simple(self):
        sinks = ["gconfaudiosink", "alsasink"]
        for n in filter(Gst.ElementFactory.find, sinks):
            obj, name = gstreamer_sink(n)
            assert obj
            self.assertEqual(name, n)

    def test_invalid(self):
        with ignore_gst_errors():
            self.assertRaises(PlayerError, gstreamer_sink, "notarealsink")

    def test_fallback(self):
        obj, name = gstreamer_sink("")
        assert obj
        if os.name == "nt":
            self.assertEqual(name, "wasapi2sink")
        else:
            self.assertEqual(name, find_audio_sink()[1])

    def test_append_sink(self):
        obj, name = gstreamer_sink("volume")
        assert obj
        self.assertEqual(name.split("!")[-1].strip(), gstreamer_sink("")[1])


@skipUnless(Gst, "GStreamer missing")
class TGstreamerTagList(TestCase):
    def test_parse(self):
        # gst.TagList can't be filled using pyGtk... so use a dict instead

        l = {}
        l["extended-comment"] = "foo=bar"
        assert "foo" in parse_gstreamer_taglist(l)

        l["extended-comment"] = ["foo=bar", "bar=foo", "bar=foo2"]
        assert "foo" in parse_gstreamer_taglist(l)
        assert "bar" in parse_gstreamer_taglist(l)
        self.assertEqual(parse_gstreamer_taglist(l)["bar"], "foo\nfoo2")

        # date is abstract, so define our own
        # (might work with pygobject now)
        class Foo:
            def to_iso8601_string(self):
                return "3000-10-2"

        l["date"] = Foo()
        date = Gst.DateTime
        Gst.DateTime = Foo
        self.assertEqual(parse_gstreamer_taglist(l)["date"], "3000-10-2")
        Gst.DateTime = date

        l["foo"] = "äöü"
        parsed = parse_gstreamer_taglist(l)
        assert isinstance(parsed["foo"], str)
        assert "äöü" in parsed["foo"].split("\n")

        l["foo"] = "äöü".encode()
        parsed = parse_gstreamer_taglist(l)
        assert isinstance(parsed["foo"], str)
        assert "äöü" in parsed["foo"].split("\n")

        l["bar"] = 1.2
        self.assertEqual(parse_gstreamer_taglist(l)["bar"], 1.2)

        l["bar"] = 9
        self.assertEqual(parse_gstreamer_taglist(l)["bar"], 9)

        l["bar"] = Gst.TagList()  # some random gst instance
        self.assertTrue(isinstance(parse_gstreamer_taglist(l)["bar"], str))
        assert "GstTagList" in parse_gstreamer_taglist(l)["bar"]

    def test_sanitize(self):
        l = sanitize_tags({"location": "http://foo"})
        assert "website" in l

        l = sanitize_tags({"channel-mode": "joint-stereo"})
        self.assertEqual(l["channel-mode"], "stereo")

        l = sanitize_tags({"channel-mode": "dual"})
        self.assertEqual(l["channel-mode"], "stereo")

        l = sanitize_tags({"audio-codec": "mp3"})
        self.assertEqual(l["audio-codec"], "MP3")

        l = sanitize_tags({"audio-codec": "Advanced Audio Coding"})
        self.assertEqual(l["audio-codec"], "MPEG-4 AAC")

        l = sanitize_tags({"audio-codec": "vorbis"})
        self.assertEqual(l["audio-codec"], "Ogg Vorbis")

        l = {"a": "http://www.shoutcast.com", "b": "default genre"}
        l = sanitize_tags(l)
        assert not l

        l = sanitize_tags({"duration": 1000 * 42}, stream=True)
        self.assertEqual(l["~#length"], 42)
        l = sanitize_tags({"duration": 1000 * 42})
        assert not l

        l = sanitize_tags({"duration": "bla"}, stream=True)
        self.assertEqual(l["duration"], "bla")

        l = sanitize_tags({"bitrate": 1000 * 42}, stream=True)
        self.assertEqual(l["~#bitrate"], 42)
        l = sanitize_tags({"bitrate": 1000 * 42})
        assert not l

        l = sanitize_tags({"bitrate": "bla"})
        self.assertEqual(l["bitrate"], "bla")

        l = sanitize_tags({"nominal-bitrate": 1000 * 42})
        self.assertEqual(l["~#bitrate"], 42)
        l = sanitize_tags({"nominal-bitrate": 1000 * 42}, stream=True)
        assert not l

        l = sanitize_tags({"nominal-bitrate": "bla"})
        self.assertEqual(l["nominal-bitrate"], "bla")

        l = {"emphasis": "something"}
        assert not sanitize_tags(l)
        assert not sanitize_tags(l)

        l = {"title": "something"}
        assert not sanitize_tags(l)
        assert sanitize_tags(l, stream=True)

        l = {"artist": "something"}
        assert not sanitize_tags(l)
        assert sanitize_tags(l, stream=True)

        l = {"~#foo": 42, "bar": 42, "~#bla": "42"}
        assert "~#foo" in sanitize_tags(l)
        assert "~#bar" in sanitize_tags(l)
        assert "bla" in sanitize_tags(l)

        l = {}
        l["extended-comment"] = ["location=1", "website=2", "website=3"]
        l = parse_gstreamer_taglist(l)
        l = sanitize_tags(l)["website"].split("\n")
        assert "1" in l
        assert "2" in l
        assert "3" in l


@skipUnless(Gst, "GStreamer missing")
@skipUnless(
    sys.platform == "darwin" or os.name == "nt" or is_flatpak(), "no control over gst"
)
class TGStreamerCodecs(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def _check(self, song):
        old_threshold = Gst.debug_get_default_threshold()
        Gst.debug_set_default_threshold(Gst.DebugLevel.NONE)

        pipeline = Gst.parse_launch(
            "uridecodebin uri={} ! fakesink".format(song("~uri"))
        )
        bus = pipeline.get_bus()
        pipeline.set_state(Gst.State.PLAYING)
        error = None
        try:
            while 1:
                message = bus.timed_pop(Gst.SECOND * 40)
                if not message or message.type == Gst.MessageType.ERROR:
                    if message:
                        error = message.parse_error()[0].message
                    else:
                        error = "timed out"
                    break
                if message.type == Gst.MessageType.EOS:
                    break
        finally:
            pipeline.set_state(Gst.State.NULL)

        Gst.debug_set_default_threshold(old_threshold)
        return error

    def test_decode_all(self):
        """Decode all kinds of formats using Gstreamer, to check if
        they all work and to notify us if a plugin is missing on
        platforms where we control the packaging.
        """

        files = [
            "empty.aac",
            "empty.flac",
            "empty.ogg",
            "empty.opus",
            "silence-44-s.mpc",
            "silence-44-s.tta",
            # "test.mid",
            "silence-44-s.spx",
            "test.spc",
            "test.vgm",
            "test.wma",
            "empty.xm",
            "h264_aac.mp4",
            "h265_aac.mp4",
        ]

        gst_version = Gst.version()
        if gst_version >= (1, 24, 7):
            # https://gitlab.freedesktop.org/gstreamer/gstreamer/-/issues/3369
            files.append("silence-44-s.sv8.mpc")
        if gst_version >= (1, 24, 2):
            # https://gitlab.freedesktop.org/gstreamer/gstreamer/-/merge_requests/6498
            files.append("coverart.wv")

        errors = []
        for file_ in files:
            path = get_data_path(file_)
            song = MusicFile(path)
            if song is not None:
                error = self._check(song)
                if error:
                    errors.append((song("~format"), error))

        if errors:
            raise Exception(f"Decoding failed {errors!r}")
