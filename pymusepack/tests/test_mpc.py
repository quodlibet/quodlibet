import os
from tests import registerCase
from unittest import TestCase
import musepack

SAMPLE = os.path.join(os.path.dirname(__file__), "click.mpc")

class MPCTest(TestCase):
    def setUp(self):
        self.mpc = musepack.MPCFile(SAMPLE)

    def test_open_fail(self):
        self.failUnlessRaises(OSError, musepack.MPCFile, "dne")

    def test_frequency(self):
        self.failUnlessEqual(self.mpc.frequency, 44100)
    def test_channels(self):
        self.failUnlessEqual(self.mpc.channels, 2)
    def test_frames(self):
        self.failUnlessEqual(self.mpc.frames, 3)
    def test_samples(self):
        self.failUnlessEqual(self.mpc.samples, 2880)
    def test_length(self):
        self.failUnlessEqual(self.mpc.length, 61)
    def test_consistency(self):
        self.failUnlessEqual(
            int(self.mpc.samples / (self.mpc.frequency / 1000.0)) // 10,
            self.mpc.length // 10)

    def test_streamversion(self):
        self.failUnlessEqual(self.mpc.stream_version, 7)
    def test_encoder(self):
        self.failUnlessEqual(self.mpc.encoder_version, 115)
        self.failUnlessEqual(self.mpc.encoder, '--Alpha-- 1.15')
    def test_profile(self):
        self.failUnlessEqual(self.mpc.profile, 10)
        self.failUnlessEqual(self.mpc.profile_name, "'Standard'")

    def test_bitrate(self):
        self.failUnlessEqual(self.mpc.bitrate, 207760.0)

    def test_replaygain(self):
        self.failUnlessEqual(self.mpc.gain_radio, 0)
        self.failUnlessEqual(self.mpc.gain_audiophile, 0)
        self.failUnlessEqual(self.mpc.peak_radio, 0)
        self.failUnlessEqual(self.mpc.peak_audiophile, 0)

    def test_seek(self):
        self.failUnlessEqual(self.mpc.position, 0.0)
        self.mpc.seek(15)
        self.failUnlessEqual(self.mpc.position, 15.0)
        self.failUnless(self.mpc.read())
        self.failUnless(self.mpc.position > 15.0)
    def test_seek_fail(self):
        self.failUnlessRaises(IOError, self.mpc.seek, 10000)
    def test_end(self):
        self.mpc.seek(self.mpc.length)
        self.mpc.read() # clear out end of buffer
        self.failIf(self.mpc.read())

    def tearDown(self):
        del(self.mpc)

registerCase(MPCTest)
