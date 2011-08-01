from tests import TestCase, add

from quodlibet.player.gstbe import GStreamerSink as Sink

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
