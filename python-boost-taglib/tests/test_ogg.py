import os, taglib
from unittest import TestCase

OGG_FN = "tests/data/silence-44-s.ogg"

class VorbisLoad(TestCase):
    OGG = taglib.VorbisFile(OGG_FN)
    PROPS = OGG.audioProperties()

    def test_load(self):
        self.failUnless(self.OGG)
    def test_name(self):
        self.failUnlessEqual(OGG_FN, self.OGG.name)
    def test_size(self):
        self.failUnlessEqual(os.path.getsize(OGG_FN), self.OGG.size)
    def test_readtell(self):
        pos = self.OGG.tell()
        data = self.OGG.read(10)
        self.failUnless(data)
        self.failUnless(self.OGG.tell() > pos)
    def test_seektoendandback(self):
        pos = self.OGG.tell()
        self.OGG.seek(0, taglib.Position.END)
        self.failUnlessEqual(self.OGG.size, self.OGG.tell())
        self.OGG.seek(pos, taglib.Position.BEGINNING)
        self.failUnlessEqual(self.OGG.tell(), pos)

class DNEVorbisLoad(TestCase):
    OGG = taglib.VorbisFile("/doesnotexist")

    def test_open(self): self.failUnless(self.OGG.closed)
    def test_name(self): self.failUnlessEqual("/doesnotexist", self.OGG.name)
    def test_size(self): self.failUnlessEqual(0, self.OGG.size)
    def test_properties(self): self.failIf(self.OGG.audioProperties())

class VorbisProperties(TestCase):
    OGG = taglib.VorbisFile(OGG_FN)
    PROPS = OGG.audioProperties()

    def test_bitrate(self):
        self.failUnlessEqual(45, self.PROPS.bitrate)
    def test_sampleRate(self):
        self.failUnlessEqual(44100, self.PROPS.sampleRate)
    def test_channels(self):
        self.failUnlessEqual(2, self.PROPS.channels)
    def test_length(self):
        self.failUnlessEqual(3, self.PROPS.length)

class VorbisTag(TestCase):
    OGG = taglib.VorbisFile(OGG_FN)
    TAG = OGG.tag()

    def test_title(self): self.failUnlessEqual(self.TAG.title, "Silence")
    def test_year(self): self.failUnlessEqual(self.TAG.year, 2004)
    def test_comment(self): self.failIf(self.TAG.comment)
    def test_artist(self): self.failUnlessEqual(self.TAG.artist, "piman")

cases = [VorbisLoad, VorbisProperties, DNEVorbisLoad, VorbisTag]
