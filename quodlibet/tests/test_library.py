from unittest import TestCase, makeSuite
from tests import registerCase
from formats.audio import AudioFile, Unknown
from formats import MusicFile
import config; config.init()

class TestFileTypes(TestCase):
    def setUp(self):
        self.vorb = MusicFile("tests/data/silence-44-s.ogg")
        self.mp3 = MusicFile("tests/data/silence-44-s.mp3")
        self.flac = MusicFile("tests/data/silence-44-s.flac")
        self.failUnless(self.vorb)
        self.failUnless(self.mp3)
        self.failUnless(self.flac)

    def test_changable(self):
        for file in [self.vorb, self.mp3, self.flac]:
            self.failIf(file.can_change("=foo"))
            self.failIf(file.can_change("vendor"))
            self.failIf(file.can_change("foo~bar"))
            self.failUnless(file.can_change("artist"))
            self.failUnless(file.can_change("title"))
            self.failUnless(file.can_change("tracknumber"))
        self.failUnless(self.vorb.can_change("somebadtag"))
        self.failUnless(self.flac.can_change("somebadtag"))
        self.failUnless(self.mp3.can_change("somebadtag"))

    def test_metadata(self):
        for file in [self.vorb, self.mp3, self.flac]:
            self.failUnlessEqual(file["artist"], "piman\njzig")
            self.failUnlessEqual(file["album"], "Quod Libet Test Data")
            self.failUnlessEqual(file["title"], "Silence")
            self.failUnlessEqual(file["~#playcount"], 0)
            self.failUnlessEqual(file("~#track"), 2)

    def test_reload(self):
        for file in [self.vorb, self.mp3, self.flac]:
            d = dict(file)
            file.reload()
            d["~#added"] = file["~#added"] # this key could change
            self.failUnlessEqual(d, file)
        

registerCase(TestFileTypes)
