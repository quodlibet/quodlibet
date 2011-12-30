# -*- coding: utf-8 -*-
import pygst
pygst.require("0.10")
import gst

from tests import TestCase, add

from quodlibet.player.gstbe import GStreamerSink as Sink
from quodlibet.player.gstbe import parse_gstreamer_taglist
from quodlibet.util import sanitize_tags

class TGStreamerSink(TestCase):
    def test_simple(self):
        import gst
        sinks = ["gconfaudiosink", "alsasink"]
        for n in filter(gst.element_factory_find, sinks):
            obj, name = Sink(n)
            self.failUnless(obj)
            self.failUnlessEqual(name, n)

    def test_fallback(self):
        import __builtin__
        pw = print_w
        __builtin__.__dict__["print_w"] = lambda *x: None
        obj, name = Sink("notarealsink")
        __builtin__.__dict__["print_w"] = pw
        self.failUnless(obj)
        self.failUnlessEqual(name, "autoaudiosink")

    def test_append_sink(self):
        obj, name = Sink("volume")
        self.failUnless(obj)
        self.failUnlessEqual(name.split("!")[-1].strip(), Sink("")[1])

add(TGStreamerSink)

class TGstreamerTagList(TestCase):
    def test_parse(self):
        # gst.TagList can't be filled using pygtk... so use a dict instead

        l = {}
        l["extended-comment"] = u"foo=bar"
        self.failUnless("foo" in parse_gstreamer_taglist(l))

        l["extended-comment"] = [u"foo=bar", u"bar=foo", u"bar=foo2"]
        self.failUnless("foo" in parse_gstreamer_taglist(l))
        self.failUnless("bar" in parse_gstreamer_taglist(l))
        self.failUnlessEqual(parse_gstreamer_taglist(l)["bar"], "foo\nfoo2")


        # date is abstract, so define our own
        class Foo(object):
            year = 3000
            month = 10
            day = 2
        l["date"] = Foo()
        date = gst.Date
        gst.Date = Foo
        self.failUnlessEqual(parse_gstreamer_taglist(l)["date"], "3000-10-2")
        gst.Date = date

        self.failIf(parse_gstreamer_taglist({"bla": ["xyz"]}))

        l["foo"] = u"äöü"
        self.failUnless(isinstance(parse_gstreamer_taglist(l)["foo"], unicode))
        self.failUnlessEqual(parse_gstreamer_taglist(l)["foo"], u"äöü")

        l["foo"] = u"äöü".encode("utf-8")
        self.failUnless(isinstance(parse_gstreamer_taglist(l)["foo"], unicode))
        self.failUnlessEqual(parse_gstreamer_taglist(l)["foo"], u"äöü")

        l["bar"] = 1.2
        self.failUnlessEqual(parse_gstreamer_taglist(l)["bar"], 1.2)

        l["bar"] = 9L
        self.failUnlessEqual(parse_gstreamer_taglist(l)["bar"], 9)

        l["bar"] = 9
        self.failUnlessEqual(parse_gstreamer_taglist(l)["bar"], 9)

        l["bar"] = gst.TagList() # some random gst instance
        self.failUnless(isinstance(parse_gstreamer_taglist(l)["bar"], unicode))
        self.failUnless("GstTagList" in parse_gstreamer_taglist(l)["bar"])

    def test_sanitize(self):
        l = sanitize_tags({"location": u"http://foo"})
        self.failUnless("website" in l)

        l = sanitize_tags({"channel-mode": u"joint-stereo"})
        self.failUnlessEqual(l["channel-mode"], "stereo")

        l = sanitize_tags({"channel-mode": u"dual"})
        self.failUnlessEqual(l["channel-mode"], "stereo")

        l = sanitize_tags({"audio-codec": u"mp3"})
        self.failUnlessEqual(l["audio-codec"], "MP3")

        l = sanitize_tags({"audio-codec": u"Advanced Audio Coding"})
        self.failUnlessEqual(l["audio-codec"], "MPEG-4 AAC")

        l = sanitize_tags({"audio-codec": u"vorbis"})
        self.failUnlessEqual(l["audio-codec"], "Ogg Vorbis")

        l = {"a": u"http://www.shoutcast.com", "b": u"default genre"}
        l = sanitize_tags(l)
        self.failIf(l)

        l = sanitize_tags({"duration": 1000 * 42}, stream=True)
        self.failUnlessEqual(l["~#length"], 42)
        l = sanitize_tags({"duration": 1000 * 42})
        self.failIf(l)

        l = sanitize_tags({"duration": u"bla"}, stream=True)
        self.failUnlessEqual(l["duration"], u"bla")

        l = sanitize_tags({"bitrate": 1000 * 42}, stream=True)
        self.failUnlessEqual(l["~#bitrate"], 42)
        l = sanitize_tags({"bitrate": 1000 * 42})
        self.failIf(l)

        l = sanitize_tags({"bitrate": u"bla"})
        self.failUnlessEqual(l["bitrate"], u"bla")

        l = sanitize_tags({"nominal-bitrate": 1000 * 42})
        self.failUnlessEqual(l["~#bitrate"], 42)
        l = sanitize_tags({"nominal-bitrate": 1000 * 42}, stream=True)
        self.failIf(l)

        l = sanitize_tags({"nominal-bitrate": u"bla"})
        self.failUnlessEqual(l["nominal-bitrate"], u"bla")

        l = {"emphasis": u"something"}
        self.failIf(sanitize_tags(l))
        self.failIf(sanitize_tags(l))

        l = {"title": u"something"}
        self.failIf(sanitize_tags(l))
        self.failUnless(sanitize_tags(l, stream=True))

        l = {"artist": u"something"}
        self.failIf(sanitize_tags(l))
        self.failUnless(sanitize_tags(l, stream=True))

        l = {"~#foo": 42, "bar": 42, "~#bla": u"42"}
        self.failUnless("~#foo" in sanitize_tags(l))
        self.failUnless("~#bar" in sanitize_tags(l))
        self.failUnless("bla" in sanitize_tags(l))

        l = {}
        l["extended-comment"] = [u"location=1", u"website=2", u"website=3"]
        l = parse_gstreamer_taglist(l)
        l = sanitize_tags(l)["website"].split("\n")
        self.failUnless("1" in l)
        self.failUnless("2" in l)
        self.failUnless("3" in l)

        # parse_gstreamer_taglist should only return unicode
        self.failIf(sanitize_tags({"foo": "bar"}))

add(TGstreamerTagList)
