import os
from tests import registerCase
from unittest import TestCase
import musepack

DIR = os.path.dirname(__file__)
SAMPLE = os.path.join(DIR, "click.mpc")
OLD = os.path.join(DIR, "oldtag.apev2")
NEW = os.path.join(DIR, "newtag.apev2")

from sets import Set as set

class APEReader(TestCase):
    def setUp(self):
        self.tag = musepack.APETag(OLD)

    def test_invalid(self):
        self.failUnlessRaises(OSError, musepack.APETag, "dne")

    def test_cases(self):
        self.failUnlessEqual(self.tag["artist"], self.tag["ARTIST"])
        self.failUnless("artist" in self.tag)
        self.failUnless("artisT" in self.tag)

    def test_dictlike(self):
        self.failUnlessEqual(set(self.tag.keys()),
                             set(["artist", "title", "album", "track"]))
        self.failUnless("AnArtist" in self.tag.values())

        self.failUnlessEqual(
            self.tag.items(), zip(self.tag.keys(), self.tag.values()))

    def test_del(self):
        s = self.tag["artist"]
        del(self.tag["artist"])
        self.failIf("artist" in self.tag)
        self.failUnlessRaises(KeyError, self.tag.__getitem__, "artist")
        self.tag["Artist"] = s
        self.failUnlessEqual(self.tag["artist"], "AnArtist")

    def test_values(self):
        self.failUnlessEqual(self.tag["artist"], self.tag["artist"])
        self.failUnless(self.tag["artist"] < self.tag["title"])
        self.failUnlessEqual(self.tag["artist"], "AnArtist")
        self.failUnlessEqual(self.tag["title"], "Some Music")
        self.failUnlessEqual(self.tag["album"], "A test case")
        self.failUnlessEqual("07", self.tag["track"])

        self.failIfEqual(self.tag["album"], "A test Case")

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

registerCase(APEReader)
registerCase(MPCTest)
