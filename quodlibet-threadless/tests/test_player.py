from unittest import TestCase, makeSuite
from tests import registerCase
import config
from formats.mp3 import MP3Player
from formats.oggvorbis import OggPlayer
import os

class FakeDev(object):
    volume = 50
    def play(self, buf): pass
    def set_info(self, rate, channels):
        self.rate = rate
        self.channels = channels

class TestAudio(TestCase):
    def setUp(self):
        self.dev = FakeDev()

    def test_audio(self):
        for rate in [22050, 44100, 48000]:
            for mode in ["s", "m"]:
                for Type, ext in [(OggPlayer, "ogg"),
                                  (MP3Player, "mp3")]:
                    f = Type(self.dev,
                             {"~filename": "tests/data/silence-%d-%s.%s"%(
                        rate / 1000, mode, ext)})
                    self.failUnlessEqual(self.dev.rate, rate)
                    i = iter(f)
                    self.failUnless(f.length == 4000 or # mp3
                                    f.length == 3684) # ogg
                    f.seek(2000)
                    pos = i.next()
                    self.failUnless(abs(pos - 2000) < 50)
                    npos = i.next()
                    self.failUnless(npos > pos)
                    f.end()
                    self.failUnlessRaises(StopIteration, f.next)
                    self.failUnless(f.stopped)

registerCase(TestAudio)
