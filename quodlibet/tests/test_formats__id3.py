# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path

import os
from io import BytesIO

from quodlibet import const
from quodlibet.formats._image import EmbeddedImage
from quodlibet.formats.mp3 import MP3File
from quodlibet.formats.aiff import AIFFFile

import mutagen

from .helper import get_temp_copy


class TID3ImagesBase(TestCase):

    KIND = None
    PATH = None

    def setUp(self):
        self.filename = get_temp_copy(self.PATH)

    def tearDown(self):
        os.remove(self.filename)


class TID3ImagesMixin(object):

    def test_can_change_images(self):
        self.failUnless(self.KIND(self.filename).can_change_images)

    def test_get_primary_image(self):
        self.failIf(self.KIND(self.filename).has_images)

        f = mutagen.File(self.filename)
        apic = mutagen.id3.APIC(encoding=3, mime="image/jpeg", type=4,
                                desc="foo", data=b"bar")
        f.tags.add(apic)
        f.save()

        song = self.KIND(self.filename)
        self.failUnless(song.has_images)
        image = song.get_primary_image()
        self.assertEqual(image.mime_type, "image/jpeg")
        fn = image.file
        self.failUnlessEqual(fn.read(), b"bar")

        apic = mutagen.id3.APIC(encoding=3, mime="image/jpeg", type=3,
                                desc="xx", data=b"bar2")
        f.tags.add(apic)
        f.save()

        song = self.KIND(self.filename)
        self.failUnless(song.has_images)
        image = song.get_primary_image()
        self.failUnlessEqual(image.read(), b"bar2")

        # get_images()
        images = song.get_images()
        self.assertTrue(images and len(images) == 2)
        self.assertEqual(images[0].type, 3)
        self.assertEqual(images[1].type, 4)

    def test_clear_images(self):
        f = mutagen.File(self.filename)
        apic = mutagen.id3.APIC(encoding=3, mime="image/jpeg", type=4,
                                desc="foo", data=b"bar")
        f.tags.add(apic)
        f.save()

        song = self.KIND(self.filename)
        self.failUnless(song.has_images)
        song.clear_images()

        song = self.KIND(self.filename)
        self.assertFalse(song.has_images)

    def test_set_image(self):
        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)

        song = self.KIND(self.filename)
        self.failIf(song.has_images)
        song.set_image(image)
        self.assertTrue(song.has_images)

        song = self.KIND(self.filename)
        self.assertTrue(song.has_images)
        self.assertEqual(song.get_primary_image().mime_type, "image/jpeg")

    def test_set_image_no_tag(self):
        f = mutagen.File(self.filename)
        f.delete()
        song = self.KIND(self.filename)
        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)
        song.set_image(image)

        song = self.KIND(self.filename)
        self.assertTrue(song.has_images)


class TID3ImagesMP3(TID3ImagesBase, TID3ImagesMixin):

    KIND = MP3File
    PATH = get_data_path('silence-44-s.mp3')


class TID3ImagesAIFF(TID3ImagesBase, TID3ImagesMixin):

    KIND = AIFFFile
    PATH = get_data_path('test.aiff')


class TID3FileBase(TestCase):

    KIND = None
    PATH = None

    def setUp(self):
        self.filename = get_temp_copy(self.PATH)

    def tearDown(self):
        os.unlink(self.filename)


class TID3FileMixin(object):

    def test_optional_POPM_count(self):
        # https://github.com/quodlibet/quodlibet/issues/364
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.POPM(const.EMAIL, 42))
        try:
            f.save()
        except TypeError:
            # https://github.com/quodlibet/quodlibet/issues/33
            pass
        else:
            self.KIND(self.filename)

    def test_write_empty_replaygain_track_gain(self):
        f = self.KIND(self.filename)
        f["replaygain_track_gain"] = ""
        f.write()
        f.reload()
        assert f.replay_gain(["track"]) == 1.0

    def test_TXXX_DATE(self):
        # https://github.com/quodlibet/quodlibet/issues/220
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc=u'DATE',
                                    text=u'2010-01-13'))
        f.tags.add(mutagen.id3.TDRC(encoding=3, text=u'2010-01-14'))
        f.save()
        self.assertEquals(self.KIND(self.filename)['date'], '2010-01-14')
        f.tags.delall('TDRC')
        f.save()
        self.assertEquals(self.KIND(self.filename)['date'], '2010-01-13')
        f.delete()
        self.KIND(self.filename)

    def test_USLT(self):
        """Tests reading and writing of lyrics in USLT"""
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.USLT(encoding=3, desc=u'', lang='\x00\x00\x00',
                   text=u'lyrics'))
        f.tags.add(mutagen.id3.USLT(encoding=3, desc=u'desc',
                   lang='\x00\x00\x00', text=u'lyrics with non-empty desc'))
        f.tags.add(mutagen.id3.USLT(encoding=3, desc=u'', lang='xyz',
                   text=u'lyrics with non-empty lang'))
        f.save()

        f = mutagen.File(self.filename)
        self.failUnlessEqual(f.tags[u'USLT::\x00\x00\x00'], u'lyrics')
        self.failUnlessEqual(f.tags[u'USLT:desc:\x00\x00\x00'],
                             u'lyrics with non-empty desc')
        self.failUnlessEqual(f.tags[u'USLT::xyz'],
                             u'lyrics with non-empty lang')

        f = self.KIND(self.filename)
        self.failUnlessEqual(f['lyrics'], u'lyrics\n'
                                          u'lyrics with non-empty lang\n'
                                          u'lyrics with non-empty desc')
        f['lyrics'] = u'modified lyrics'
        f.write()

        f = self.KIND(self.filename)
        self.failUnlessEqual(f['lyrics'], u'modified lyrics')
        del f['lyrics']
        f.write()

        f = mutagen.File(self.filename)
        self.failIf('USLT' in f.tags,
                    'There should be no USLT tag when lyrics were deleted')

        f = self.KIND(self.filename)
        self.failIf('lyrics' in f,
                   'There should be no lyrics key when there is no USLT')

    def test_lang_read(self):
        """Tests reading of language from TXXX"""
        # https://github.com/quodlibet/quodlibet/issues/439
        f = mutagen.File(self.filename)
        try:
            lang = u'free-text'
            f.tags.add(
                mutagen.id3.TXXX(encoding=3, desc=u'QuodLibet::language',
                                 text=lang))
            f.save()
            self.assertEquals(self.KIND(self.filename)['language'], lang)
        finally:
            f.delete()

    def test_lang_read_TLAN(self):
        """Tests reading language from TLAN"""
        f = mutagen.File(self.filename)
        lang = u'eng'
        try:
            f.tags.add(mutagen.id3.TLAN(encoding=3, text=lang))
            f.save()
            self.assertEquals(self.KIND(self.filename)['language'], lang)
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
            self.assertEquals(self.KIND(self.filename)['language'], exp)
        finally:
            f.delete()

    def test_write_lang_freetext(self):
        """Tests that if you don't use an ISO 639-2 code,
        TXXX gets populated
        """

        af = self.KIND(self.filename)
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
            af = self.KIND(self.filename)
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
        af = self.KIND(self.filename)
        af["language"] = iso_langs_str
        self.failUnlessEqual(af("language"), iso_langs_str)
        af.write()
        tags = mutagen.File(self.filename).tags
        self.failIf(u'TXXX:QuodLibet::language' in tags,
                    "Should have used TLAN for %s" % iso_langs)
        self.failUnlessEqual(tags[u'TLAN'], iso_langs,
                msg="Wrong tags: %s" % tags)
        af.clear()

    def test_ignore_tlen(self):
        f = mutagen.File(self.filename)
        f.tags.delall("TLEN")
        f.save()
        length = self.KIND(self.filename)("~#length")

        for value in ["20000", "0", "x"]:
            f = mutagen.File(self.filename)
            f.tags.add(mutagen.id3.TLEN(encoding=0, text=[value]))
            f.save()
            self.assertAlmostEqual(
                self.KIND(self.filename)("~#length"), length, 2)

    def test_load_tcon(self):
        # check if the mutagen preprocessing is used
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TCON(encoding=3, text=["4", "5"]))
        f.save()
        genres = set(self.KIND(self.filename).list("genre"))
        self.failUnlessEqual(genres, {"Funk", "Disco"})

    def test_mb_track_id(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.UFID(owner="http://musicbrainz.org", data=b"x"))
        f.save()
        song = self.KIND(self.filename)
        self.failUnlessEqual(song("musicbrainz_trackid"), "x")
        song["musicbrainz_trackid"] = "y"
        song.write()
        f = mutagen.File(self.filename)
        self.failUnlessEqual(f.tags["UFID:http://musicbrainz.org"].data, b"y")
        del song["musicbrainz_trackid"]
        song.write()
        f = mutagen.File(self.filename)
        self.failIf(f.tags.get("UFID:http://musicbrainz.org"))

    def test_mb_release_track_id(self):
        f = mutagen.File(self.filename)
        f.tags.add(
            mutagen.id3.TXXX(encoding=3, desc=u"MusicBrainz Release Track Id",
                             text=["bla"]))
        f.save()
        song = self.KIND(self.filename)
        self.assertEqual(song["musicbrainz_releasetrackid"], u"bla")
        song["musicbrainz_releasetrackid"] = u"foo"
        song.write()
        f = mutagen.File(self.filename)
        frames = f.tags.getall("TXXX:MusicBrainz Release Track Id")
        self.assertTrue(frames)
        self.assertEqual(frames[0].text, [u"foo"])

    def test_load_comment(self):
        # comm with empty descriptions => comment
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.COMM(encoding=3, lang="aar",
                                    desc="", text=["foo", "bar"]))
        f.save()
        comments = set(self.KIND(self.filename).list("comment"))
        self.failUnlessEqual(comments, {"bar", "foo"})

    def test_foobar2k_replaygain(self):
        # foobar2k saved gain there
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="replaygain_track_gain",
                                    text=["-6 db"]))
        f.save()
        song = self.KIND(self.filename)
        self.failIfAlmostEqual(song.replay_gain(["track"]), 1.0, 1)

        # check if all keys are str
        for k in self.KIND(self.filename).keys():
            self.failUnless(isinstance(k, str))

        # remove value, save, reload and check if still gone
        del song["replaygain_track_gain"]
        song.write()
        song.reload()

        self.failUnlessAlmostEqual(song.replay_gain(["track"]), 1.0, 1)

    def test_foobar2k_replaygain_read_new(self):
        # Others don't like RVA2, so we have to read/write foobar style
        # https://github.com/quodlibet/quodlibet/issues/1027
        f = mutagen.File(self.filename)

        # use RVA2 in case it's the only one
        f.tags.add(mutagen.id3.RVA2(desc="track", channel=1,
                                    gain=-9, peak=1.0))
        f.save()
        song = self.KIND(self.filename)
        self.failUnlessAlmostEqual(song.replay_gain(["track"]), 0.35, 1)

        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="replaygain_track_gain",
                                    text=["-6 db"]))
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="replaygain_track_peak",
                                    text=["0.9"]))
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="replaygain_album_gain",
                                    text=["3 db"]))
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="replaygain_album_peak",
                                    text=["0.8"]))
        f.save()

        song = self.KIND(self.filename)
        self.failUnlessEqual(song("replaygain_track_gain"), "-6 db")
        self.failUnlessEqual(song("replaygain_track_peak"), "0.9")
        self.failUnlessEqual(song("replaygain_album_gain"), "3 db")
        self.failUnlessEqual(song("replaygain_album_peak"), "0.8")

    def test_foobar2k_replaygain_write_new(self):
        # Others don't like RVA2, so we have to read/write foobar style
        # https://github.com/quodlibet/quodlibet/issues/1027
        song = self.KIND(self.filename)
        song["replaygain_track_gain"] = "-6 db"
        song["replaygain_track_peak"] = "0.9"
        song["replaygain_album_gain"] = "3 db"
        song["replaygain_album_peak"] = "0.8"
        song.write()

        f = mutagen.File(self.filename)
        for k in ["track_peak", "track_gain", "album_peak", "album_gain"]:
            self.failUnless(f["TXXX:replaygain_" + k])

    def test_foobar2k_rg_caseinsensitive(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="REPLAYGAIN_TRACK_GAIN",
                                    text=["-6 db"]))
        f.save()
        song = self.KIND(self.filename)
        self.failUnlessEqual(song("replaygain_track_gain"), "-6 db")
        song.write()
        f = mutagen.File(self.filename)
        frames = f.tags.getall("TXXX:replaygain_track_gain")
        self.assertTrue(frames)
        self.assertEqual(frames[0].desc, "replaygain_track_gain")
        del song["replaygain_track_gain"]
        song.write()
        f = mutagen.File(self.filename)
        self.assertFalse(f.tags.getall("TXXX:replaygain_track_gain"))

    def test_quodlibet_txxx_inval(self):
        # This shouldn't happen in our namespace, but check anyway since
        # we might open the whole TXXX namespace sometime

        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="QuodLibet::valid",
                                    text=["quux"]))
        f.tags.add(mutagen.id3.TXXX(encoding=3, desc="QuodLibet::foo=",
                                    text=["quux", "bar"]))
        f.tags.add(mutagen.id3.COMM(encoding=3, desc=u"QuodLibet::öäü",
                                    text=["quux", "bar"], lang="aar"))
        f.tags.add(mutagen.id3.COMM(encoding=3, desc=u"",
                                    text=["a"], lang="aar"))
        f.tags.add(mutagen.id3.COMM(encoding=3, desc=u"",
                                    text=["b"], lang="foo"))
        f.save()

        # check if all keys are valid
        for k in self.KIND(self.filename).keys():
            self.failUnless(isinstance(k, str))

        song = self.KIND(self.filename)
        self.failIf("foo=" in song)
        self.failIf(u"öäü" in song)
        self.failUnlessEqual(set(song.list("comment")), {"a", "b"})
        self.failUnlessEqual(song("valid"), "quux")
        del song["valid"]
        song.write()

        f = mutagen.File(self.filename)
        self.failUnless(f.tags.getall("TXXX:QuodLibet::foo="))
        self.failIf(f.tags.getall("TXXX:QuodLibet::valid"))
        self.failUnlessEqual(len(f.tags.getall("COMM")), 2)
        self.failUnlessEqual(len(f.tags.getall("COMM:")), 1)

    def test_old_comm_to_txxx(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.COMM(encoding=3, desc=u"QuodLibet::foo",
                                    text=["a"], lang="aar"))
        f.save()

        song = self.KIND(self.filename)
        self.failUnlessEqual(song("foo"), "a")
        song.write()

        f = mutagen.File(self.filename)
        self.failUnlessEqual(f["TXXX:QuodLibet::foo"].text, ["a"])

    def test_txxx_others(self):
        f = mutagen.File(self.filename)
        t1 = mutagen.id3.TXXX(encoding=3, desc="FooBar::invalid", text="quux")
        t2 = mutagen.id3.TXXX(encoding=3, desc="FooBar::öäü", text="bar")

        f.tags.add(t1)
        f.tags.add(t2)
        f.save()

        song = self.KIND(self.filename)
        self.failIf("invalid" in song)
        self.failIf(u"öäü" in song)
        song.write()

        f = mutagen.File(self.filename)
        self.failUnless(f[t1.HashKey])
        self.failUnless(f[t2.HashKey])

    def test_woar(self):
        f = mutagen.File(self.filename)
        t1 = mutagen.id3.WOAR(url="http://this.is.a.test")
        f.tags.add(t1)
        f.save()

        song = self.KIND(self.filename)
        self.failUnlessEqual(song("website"), t1.url)
        song["website"] = "http://another.test\nhttp://omg.another.one"
        song.write()

        f = mutagen.File(self.filename)
        self.failUnlessEqual(len(f.tags.getall("WOAR")), 2)

    def test_unhandled(self):
        f = mutagen.File(self.filename)
        t1 = mutagen.id3.AENC(owner="x", preview_start=1, preview_length=3)
        f.tags.add(t1)
        f.save()

        self.KIND(self.filename)

    def test_encoding(self):
        song = self.KIND(self.filename)
        song["foo"] = u"öäü"
        song["bar"] = u"abc"
        song["comment"] = u"öäü"
        song["artist"] = u"xyz"
        song["album"] = u"öäü"
        song["tracknumber"] = u"ö"
        song["discnumber"] = u"9"
        song.write()

        f = mutagen.File(self.filename)
        self.failUnlessEqual(f.tags["TXXX:QuodLibet::foo"].encoding, 1)
        self.failUnlessEqual(f.tags["TXXX:QuodLibet::bar"].encoding, 3)
        self.failUnlessEqual(f.tags["TPE1"].encoding, 3)
        self.failUnlessEqual(f.tags["TALB"].encoding, 1)
        self.failUnlessEqual(f.tags["TPE1"].encoding, 3)
        # FIXME: we shouldn't write invalid TRCK...
        self.failUnlessEqual(f.tags["TRCK"].encoding, 1)
        self.failUnlessEqual(f.tags["TPOS"].encoding, 3)

    def test_tcon(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TMCL(encoding=3, people=[["foo", "bar"]]))
        f.save()

        song = self.KIND(self.filename)
        self.failUnless("performer:foo" in song)
        self.failUnlessEqual(song("performer:foo"), "bar")

    def test_nonascii_unsup_tcon(self):
        people = [["a=", "a"], ["b~", "b"], [u"äöü", "u"], ["quux", "x"]]
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TMCL(encoding=3, people=people))
        f.save()

        # we only support one of them
        self.failUnlessEqual(
            len(self.KIND(self.filename).list("~performer")), 1)

        # but after writing they should still be there
        song = self.KIND(self.filename)
        song.write()
        f = mutagen.File(self.filename)
        self.failUnlessEqual(len(f.tags["TMCL"].people), 4)
        self.failUnlessEqual(f.tags["TMCL"].people, people)

        # also change something..
        song["performer:quux"] = "foo"
        song.write()
        f = mutagen.File(self.filename)
        self.failUnlessEqual(dict(f.tags["TMCL"].people)["quux"], "foo")

    def test_rva_large(self):
        song = self.KIND(self.filename)
        song["replaygain_track_peak"] = "3"
        song["replaygain_track_gain"] = "100"
        song.write()
        song["replaygain_track_peak"] = "-1"
        song["replaygain_track_gain"] = "-100"
        song.write()

    def test_rva(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.RVA2(desc="track", channel=1,
                                    gain=-3, peak=1.0))
        f.tags.add(mutagen.id3.RVA2(desc="album", channel=1,
                                    gain=-6, peak=1.0))
        f.save()

        song = self.KIND(self.filename)
        self.failUnlessAlmostEqual(song.replay_gain(["track"]), 0.7, 1)
        self.failUnlessAlmostEqual(song.replay_gain(["album"]), 0.5, 1)
        song.write()

        f = mutagen.File(self.filename)
        self.failUnlessEqual(len(f.tags.getall("RVA2")), 2)

    def test_rva_unknown(self):
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.RVA2(desc="track", channel=2,
                                    gain=-6, peak=1.0))
        f.tags.add(mutagen.id3.RVA2(desc="foo", channel=1,
                                    gain=-3, peak=1.0))
        f.save()

        # we use foo as track if nothing else is there
        song = self.KIND(self.filename)
        self.failUnlessAlmostEqual(song.replay_gain(["track"]), 0.7, 1)
        song.write()

        # and we write that over track..
        f = mutagen.File(self.filename)
        self.failUnlessAlmostEqual(f.tags["RVA2:track"].gain, -3.0, 1)

        # now that one is there, ignore foo
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.RVA2(desc="foo", channel=1,
                                    gain=0, peak=1.0))
        f.save()
        song = self.KIND(self.filename)
        self.failUnlessAlmostEqual(song.replay_gain(["track"]), 0.7, 1)

    def test_rva_inval(self):
        song = self.KIND(self.filename)
        song["replaygain_track_peak"] = u"0.1afasf"
        song["replaygain_track_gain"] = u"0.1afasf"
        song.write()

    def test_without_id3_tag(self):
        f = mutagen.File(self.filename)
        f.delete()
        f.save()
        song = self.KIND(self.filename)
        song.get_primary_image()
        song.write()

    def test_distrust_latin1(self):
        x = u"Å"

        # abuse mutagen a bit, and get some utf-8 in with the wrong encoding
        f = mutagen.File(self.filename)
        f.tags.add(mutagen.id3.TPE1(
            encoding=0, text=x.encode("utf-8").decode("latin-1")))
        f.save()

        # back to utf-8
        song = self.KIND(self.filename)
        self.failUnlessEqual(song("artist"), x)
        song.write()

        # because it's not ascii, saved as utf-16
        f = mutagen.File(self.filename)
        self.failUnlessEqual(f.tags["TPE1"].encoding, 1)

        # and now latin-1 that is not decodable using utf-8/16
        x = u"äöü".encode("ibm1026").decode("latin-1")
        f.tags.add(mutagen.id3.TPE1(encoding=0, text=x))
        f.save()

        self.failUnlessEqual(self.KIND(self.filename)("artist"), x)

    def test_handled_txxx_encoding(self):
        song = self.KIND(self.filename)
        song['albumartistsort'] = u'Dvo\u0159\xe1k, Anton\xedn'
        song["replaygain_track_peak"] = u'Dvo\u0159\xe1k, Anton\xedn'
        song.write()

    def test_albumartistsort(self):
        song = self.KIND(self.filename)
        song['albumartistsort'] = u"foo"
        song.write()
        song = self.KIND(self.filename)
        self.assertEqual(song['albumartistsort'], u"foo")


class TID3FileMP3(TID3FileBase, TID3FileMixin):

    KIND = MP3File
    PATH = get_data_path('silence-44-s.mp3')


class TID3FileAIFF(TID3FileBase, TID3FileMixin):

    KIND = AIFFFile
    PATH = get_data_path('test.aiff')
