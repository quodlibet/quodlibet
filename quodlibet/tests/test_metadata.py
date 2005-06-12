from unittest import TestCase
from tests import registerCase
from shutil import copyfileobj
from tempfile import mkstemp, mkdtemp
import os, formats, formats.mp3

class TestMetaData(TestCase):
    base = 'tests/data/silence-44-s'

    def setUp(self):
        """Copy the base silent file to a temp name/location and load it"""
        fd, self.filename = mkstemp(suffix=self.ext, text=False)
        dst = os.fdopen(fd, 'w')
        src = open(self.base + self.ext, 'rb')
        copyfileobj(src, dst)
        dst.close()
        self.song = formats.MusicFile(self.filename)

    def tearDown(self):
        """Delete the temp file"""
        os.remove(self.filename)
        del self.filename
        del self.song

    def test_base_data(self):
        self.failUnlessEqual(self.song['artist'], 'piman\njzig')
        self.failUnlessEqual(self.song['album'], 'Quod Libet Test Data')
        self.failUnlessEqual(self.song['title'], 'Silence')

    def test_mutability(self):
        self.failIf(self.song.can_change('=foo'))
        self.failIf(self.song.can_change('vendor'))
        self.failIf(self.song.can_change('foo~bar'))
        self.failUnless(self.song.can_change('artist'))
        self.failUnless(self.song.can_change('title'))
        self.failUnless(self.song.can_change('tracknumber'))
        self.failUnless(self.song.can_change('somebadtag'))
        self.failUnless(self.song.can_change('some%punctuated:tag.'))

    def _test_tag(self, tag, values):
        self.failUnless(self.song.can_change(tag))
        for value in values:
            self.song[tag] = value
            self.song.write()
            written = formats.MusicFile(self.filename)
            self.failUnlessEqual(written[tag], value)

    def test_artist(self): # a normalish tag
        self._test_tag('artist', ['me', 'you\nme',
            u'\u6d5c\u5d0e\u3042\u3086\u307f'])

    def test_date(self): # unusual special handling for mp3s
        self._test_tag('date', ['2004', '2005', '2005-06-12'])

    def test_genre(self): # unusual special handling for mp3s
        self._test_tag('genre', ['Pop', 'Rock\nClassical', 'Big Bird',
             u'\u30a2\u30cb\u30e1\u30b5\u30f3\u30c8\u30e9',])

    def test_wackjob(self): # undefined tag
        self._test_tag('wackjob', ['Jelly\nDanish', 'Muppet',
             u'\u30cf\u30f3\u30d0\u30fc\u30ac\u30fc'])

for ext in formats._infos.keys():
    if os.path.exists(TestMetaData.base + ext):

        extra_tests = {}
        for tag in formats.mp3.MP3File.IDS.itervalues():
            if tag in ['artist', 'date', 'genre']: continue
            def test_tag(self, tag=tag): self._test_tag(tag, ['a'])
            extra_tests['test_tag_' + tag] = test_tag
            def test_tags(self, tag=tag): self._test_tag(tag, ['b\nc'])
            extra_tests['test_tags_' + tag] = test_tags

        testcase = type('MetaData' + ext, (TestMetaData,), extra_tests)
        testcase.ext = ext
        registerCase(testcase)
