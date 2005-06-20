import os
from tests import registerCase
from unittest import TestCase
import musepack

DIR = os.path.dirname(__file__)
SAMPLE = os.path.join(DIR, "click.mpc")
OLD = os.path.join(DIR, "oldtag.apev2")

class APEWriter(TestCase):
    def setUp(self):
        import shutil
        shutil.copy(SAMPLE, SAMPLE + ".new")
        tag = musepack.APETag(SAMPLE + ".new")
        self.values = {"artist": "Joe Wreschnig\0unittest",
                       "album": "Pymusepack tests",
                       "title": "Not really a song"}
        for k, v in self.values.items():
            tag[k] = v
        tag.write()
        tag.write(SAMPLE + ".justtag")
        self.tag = musepack.APETag(SAMPLE + ".new")

    def test_readback(self):
        for k, v in self.tag.items():
            self.failUnlessEqual(str(v), self.values[k])

    def test_size(self):
        self.failUnlessEqual(
            os.path.getsize(SAMPLE + ".new"),
            os.path.getsize(SAMPLE) + os.path.getsize(SAMPLE + ".justtag"))

    def tearDown(self):
        os.unlink(SAMPLE + ".new")
        os.unlink(SAMPLE + ".justtag")

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
        self.failUnless("Track" in self.tag.keys())
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

class APEKeyTest(TestCase):
    from musepack.apev2 import APEKey

    def test_eq(self):
        self.failUnlessEqual(self.APEKey("foo"), "foo")
        self.failUnlessEqual("foo", self.APEKey("foo"))
        self.failUnlessEqual(self.APEKey("foo"), u"foo")
        self.failUnlessEqual(u"foo", self.APEKey("foo"))

        self.failUnlessEqual(self.APEKey("Bar"), "baR")
        self.failUnlessEqual(u"baR", self.APEKey("Bar"))

    def test_hash(self):
        self.failUnlessEqual(hash("foo"), hash(self.APEKey("foo")))
        self.failUnlessEqual(hash("foo"), hash(self.APEKey("FoO")))

class APEBinaryTest(TestCase):
    from musepack.apev2 import APEBinaryValue as BV

    def setUp(self):
        self.sample = "\x12\x45\xde"
        self.value = musepack.apev2.APEValue(self.sample,musepack.apev2.BINARY)

    def test_type(self):
        self.failUnless(isinstance(self.value, self.BV))

    def test_const(self):
        self.failUnlessEqual(self.sample, str(self.value))

class APETextTest(TestCase):
    from musepack.apev2 import APETextValue as TV
    def setUp(self):
        self.sample = ["foo", "bar", "baz"]
        self.value = musepack.apev2.APEValue(
            "\0".join(self.sample), musepack.apev2.TEXT)

    def test_type(self):
        self.failUnless(isinstance(self.value, self.TV))

    def test_list(self):
        self.failUnlessEqual(self.sample, list(self.value))

    def test_setitem(self):
        self.value[2] = self.sample[2] = 'quux'
        self.test_list()
        self.test_getitem()
        self.value[2] = self.sample[2] = 'baz'

    def test_getitem(self):
        for i in range(len(self.value)):
            self.failUnlessEqual(self.sample[i], self.value[i])

class APEExtTest(TestCase):
    from musepack.apev2 import APEExtValue as EV

    def setUp(self):
        self.sample = "http://foo"
        self.value = musepack.apev2.APEValue(
            self.sample, musepack.apev2.EXTERNAL)

    def test_type(self):
        self.failUnless(isinstance(self.value, self.EV))

    def test_const(self):
        self.failUnlessEqual(self.sample, str(self.value))

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
        self.failUnlessEqual(self.mpc.bitrate, 194530.0)

    def test_replaygain(self):
        self.failUnlessEqual(self.mpc.gain_radio, 927) # +9.27 dB
        self.failUnlessEqual(self.mpc.gain_audiophile, 927)
        self.failUnlessEqual(self.mpc.peak_radio, 7527) # / 32767
        self.failUnlessEqual(self.mpc.peak_audiophile, 7527)

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

    def test_set_scale(self):
        f1 = musepack.MPCFile(SAMPLE)
        fe = musepack.MPCFile(SAMPLE)
        f2 = musepack.MPCFile(SAMPLE)
        f2.set_scale(0.5)
        # sanity check to make sure equal decodes do happen...
        self.failUnlessEqual(fe.read(), self.mpc.read())
        # and so a scaled decode should not be equal.
        self.failIfEqual(f1.read(), f2.read())

    def test_set_scale_fail(self):
        self.failUnlessRaises(ValueError, self.mpc.set_scale, -1.0)

    def tearDown(self):
        del(self.mpc)

registerCase(APEReader)
registerCase(APEWriter)
registerCase(APEKeyTest)
registerCase(APEBinaryTest)
registerCase(APETextTest)
registerCase(APEExtTest)
registerCase(MPCTest)
