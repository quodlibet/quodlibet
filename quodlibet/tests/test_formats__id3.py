from tests import add, TestCase

import os
import shutil
import tempfile

from quodlibet import config, const
from quodlibet.formats.mp3 import MP3File

import mutagen

class TID3File(TestCase):
    def setUp(self):
        config.init()
        self.filename = tempfile.mkstemp(".mp3")[1]
        shutil.copy(os.path.join('tests', 'data', 'silence-44-s.mp3'), self.filename)

    def test_optional_POPM_count(self):
        #http://code.google.com/p/quodlibet/issues/detail?id=364
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.POPM(const.EMAIL, 42))
        try: f.save()
        except TypeError:
            #http://code.google.com/p/mutagen/issues/detail?id=33
            pass
        else:
            MP3File(self.filename)

    def test_TXXX_DATE(self):
        # http://code.google.com/p/quodlibet/issues/detail?id=220
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc=u'DATE',
                                    text=u'2010-01-13'))
        f.tags.add(mutagen.id3.TDRC(encoding=3, text=u'2010-01-14'))
        f.save()
        self.assertEquals(MP3File(self.filename)['date'], '2010-01-14')
        f.tags.delall('TDRC')
        f.save()
        self.assertEquals(MP3File(self.filename)['date'], '2010-01-13')
        f.delete()
        MP3File(self.filename)

    def test_lang_read(self):
        """Tests reading of language from TXXX"""
        # http://code.google.com/p/quodlibet/issues/detail?id=439
        f = mutagen.File(self.filename)
        try:
            lang = u'free-text'
            f.tags.add(mutagen.id3.TXXX(encoding=3, desc=u'QuodLibet::language',
                                        text=lang))
            f.save()
            self.assertEquals(MP3File(self.filename)['language'], lang)
        finally:
            f.delete()

    def test_lang_read_TLAN(self):
        """Tests reading language from TLAN"""
        f = mutagen.File(self.filename)
        lang = u'eng'
        try:
            f.tags.add(mutagen.id3.TLAN(encoding=3, text=lang))
            f.save()
            self.assertEquals(MP3File(self.filename)['language'], lang)
        finally:
            f.delete()

    def test_lang_read_multiple_TLAN(self):
        """Tests reading multiple language from TLAN"""
        f = mutagen.File(self.filename)
        # Include an invalid one; current behaviour is to load anyway
        lang = u'eng\0der\0fra\0fooooo'
        exp = u'eng\nder\nfra\nfooooo'
        try:
            f.tags.add(mutagen.id3.TLAN(encoding=3, text=lang))
            f.save()
            self.assertEquals(MP3File(self.filename)['language'], exp)
        finally:
            f.delete()


    def test_write_lang_freetext(self):
        """Tests that if you don't use an ISO 639-2 code, TXXX gets populated"""
        af = MP3File(self.filename)
        for val in ["free-text", "foo", "de", "en"]:
            af["language"] = val
            # Just checking...
            self.failUnlessEqual(af("language"), val)
            af.write()
            tags = mutagen.File(self.filename).tags
            self.failUnlessEqual(tags[u'TXXX:QuodLibet::language'], val)
            self.failIf("TLAN" in tags)

    def test_write_lang_iso(self):
        """Tests that if you use an ISO 639-2 code, TLAN gets populated"""
        for iso_lang in ['eng', 'ger', 'zho']:
            af = MP3File(self.filename)
            af["language"] = iso_lang
            self.failUnlessEqual(af("language"), iso_lang)
            af.write()
            tags = mutagen.File(self.filename).tags
            self.failIf(u'TXXX:QuodLibet::language' in tags,
                    "Should have used TLAN tag for '%s'" % iso_lang)
            self.failUnlessEqual(tags[u'TLAN'], iso_lang)
            af.clear()

    def test_write_multiple_lang_iso(self):
        """Tests using multiple ISO 639-2 codes"""
        iso_langs = ['eng', 'ger', 'zho']
        iso_langs_str = "\n".join(iso_langs)
        af = MP3File(self.filename)
        af["language"] = iso_langs_str
        self.failUnlessEqual(af("language"), iso_langs_str)
        af.write()
        tags = mutagen.File(self.filename).tags
        self.failIf(u'TXXX:QuodLibet::language' in tags,
                    "Should have used TLAN for %s" % iso_langs)
        self.failUnlessEqual(tags[u'TLAN'], iso_langs,
                msg="Wrong tags: %s" % tags)
        af.clear()

    def test_tlen(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TLEN(encoding=0, text=['20000']))
        f.save()
        self.failUnlessEqual(MP3File(self.filename)("~#length"), 20)

        # ignore <= 0 [issue 222]
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TLEN(encoding=0, text=['0']))
        f.save()
        self.failUnless(MP3File(self.filename)("~#length") > 0)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

add(TID3File)
