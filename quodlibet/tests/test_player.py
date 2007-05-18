from tests import TestCase, add

from quodlibet.player import GStreamerSink as Sink

class TGStreamerSink(TestCase):
    def test_simple(self):
        for n in ["gconfaudiosink", "alsasink"]:
            obj, name = Sink(n)
            self.failUnless(obj)
            self.failUnlessEqual(name, n)

    def test_fallback(self):
            obj, name = Sink("notarealsink")
            self.failUnless(obj)
            self.failUnlessEqual(name, "autoaudiosink")

add(TGStreamerSink)
