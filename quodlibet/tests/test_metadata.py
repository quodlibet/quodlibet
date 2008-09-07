from tests import TestCase, add

import os

from quodlibet import formats
from quodlibet import config

from shutil import copyfileobj
from tempfile import mkstemp

class TestMetaData(TestCase):
    base = 'tests/data/silence-44-s'

    def setUp(self):
        """Copy the base silent file to a temp name/location and load it"""
        config.init()
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
        config.quit()

    def test_base_data(self):
        self.failUnlessEqual(self.song['artist'], 'piman\njzig')
        self.failUnlessEqual(self.song['album'], 'Quod Libet Test Data')
        self.failUnlessEqual(self.song['title'], 'Silence')

    def test_mutability(self):
        self.failIf(self.song.can_change('=foo'))
        self.failIf(self.song.can_change('foo~bar'))
        self.failUnless(self.song.can_change('artist'))
        self.failUnless(self.song.can_change('title'))
        self.failUnless(self.song.can_change('tracknumber'))
        self.failUnless(self.song.can_change('somebadtag'))
        self.failUnless(self.song.can_change('some%punctuated:tag.'))

    def _test_tag(self, tag, values, remove=True):
        self.failUnless(self.song.can_change(tag))
        for value in values:
            self.song[tag] = value
            self.song.write()
            written = formats.MusicFile(self.filename)
            self.failUnlessEqual(written[tag], value)
            if remove:
                del self.song[tag]
                self.song.write()
                deleted = formats.MusicFile(self.filename)
                self.failIf(tag in deleted)

    def test_artist(self): # a normalish tag
        self._test_tag('artist', [u'me', u'you\nme',
            u'\u6d5c\u5d0e\u3042\u3086\u307f'])

    def test_date(self): # unusual special handling for mp3s
        self._test_tag('date', [u'2004', u'2005', u'2005-06-12'], False)

    def test_genre(self): # unusual special handling for mp3s
        self._test_tag('genre', [u'Pop', u'Rock\nClassical', u'Big Bird',
             u'\u30a2\u30cb\u30e1\u30b5\u30f3\u30c8\u30e9',])

    def test_odd_performer(self):
        values = [u"A Person", u"Another"]
        self._test_tag("performer:vocals", values)
        self._test_tag("performer:guitar", values)

    def test_wackjob(self): # undefined tag
        self._test_tag('wackjob', [u'Jelly\nDanish', u'Muppet',
             u'\u30cf\u30f3\u30d0\u30fc\u30ac\u30fc'])

tags = ['album', 'arranger', 'artist', 'author', 'comment', 'composer',
'conductor', 'copyright', 'discnumber', 'encodedby', 'genre', 'isrc',
'language', 'license', 'lyricist', 'organization', 'performer', 'title',
'tracknumber', 'version', 'xyzzy_undefined_tag', 'musicbrainz_trackid',
'releasecountry']

for ext in formats._infos.keys():
    if os.path.exists(TestMetaData.base + ext):

        extra_tests = {}
        for tag in tags:
            if tag in ['artist', 'date', 'genre']: continue
            def test_tag(self, tag=tag): self._test_tag(tag, [u'a'])
            extra_tests['test_tag_' + tag] = test_tag
            def test_tags(self, tag=tag): self._test_tag(tag, [u'b\nc'])
            extra_tests['test_tags_' + tag] = test_tags

        testcase = type('MetaData' + ext, (TestMetaData,), extra_tests)
        testcase.ext = ext
        add(testcase)
