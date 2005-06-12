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

    def test_metadata(self):
        for file in [self.vorb, self.mp3, self.flac]:
            self.failUnlessEqual(file["~#playcount"], 0)
            self.failUnlessEqual(file("~#track"), 2)

    def test_reload(self):
        for file in [self.vorb, self.mp3, self.flac]:
            d = dict(file)
            file.reload()
            d["~#added"] = file["~#added"] # this key could change
            self.failUnlessEqual(d, file)
        

registerCase(TestFileTypes)
