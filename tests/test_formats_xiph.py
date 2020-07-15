# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.config import RATINGS
from tests import get_data_path, skipUnless, mkstemp, TestCase

import os
import sys
import base64
from io import BytesIO

from quodlibet import config, const, formats
from quodlibet.formats.xiph import OggFile, FLACFile, OggOpusFile, OggOpus
from quodlibet.formats._image import EmbeddedImage, APICType

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, ID3NoHeaderError
from mutagen.oggvorbis import OggVorbis

from .helper import get_temp_copy


def _get_jpeg(size=5):
    from gi.repository import GdkPixbuf
    pb = GdkPixbuf.Pixbuf.new(
        GdkPixbuf.Colorspace.RGB, False, 8, size, size)
    fd, fn = mkstemp()
    pb.savev(fn, "jpeg", [], [])
    with os.fdopen(fd, "rb") as h:
        data = h.read()
    os.unlink(fn)
    return data


class TXiphPickle(TestCase):
    # make sure the classes are available at the old paths
    # so unpickling old libraries works.

    def test_modules_flac(self):
        self.failUnless("formats.flac" in sys.modules)
        mod = sys.modules["formats.flac"]
        self.failUnless(mod.FLACFile is FLACFile)

    def test_modules_vorbis(self):
        self.failUnless("formats.oggvorbis" in sys.modules)
        mod = sys.modules["formats.oggvorbis"]
        self.failUnless(mod.OggFile is OggFile)


class TVCFile(TestCase):
    # Mixin to test Vorbis writing features

    def setUp(self):
        config.init()
        config.set("editing", "save_email", "")
        config.set("editing", "save_to_songs", "1")


class TVCFileMixin(object):

    def test_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_channels(self):
        assert self.song("~#channels") == 2

    def test_deletes_rating(self):
        config.set("editing", "save_email", "foo@Bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        self.song["~#rating"] = RATINGS.default
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song("~#rating"), RATINGS.default)

    def test_new_email_rating(self):
        config.set("editing", "save_email", "foo@Bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_default_email_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", "foo@Bar.org")
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_different_email_rating(self):
        config.set("editing", "save_email", "foo@Bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        config.set("editing", "save_email", const.EMAIL)
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song("~#rating"), RATINGS.default)

        song.write()
        config.set("editing", "save_email", "foo@Bar.org")
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_huge_playcount(self):
        count = 1000000000000000
        self.song["~#playcount"] = count
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#playcount"], count)

    def test_parameter(self):
        for bad in ["rating", "playcount", "rating:foo", "playcount:bar"]:
            self.failIf(self.song.can_change(bad))

    def test_parameter_ci(self):
        for bad in ["ratinG", "plaYcount", "raTing:foo", "playCount:bar"]:
            self.failIf(self.song.can_change(bad))

    def test_case_insensitive(self):
        self.song["foo"] = "1"
        self.song["FOO"] = "1"
        self.song.write()
        self.song.reload()
        self.failUnlessEqual(self.song.list("foo"), ["1", "1"])

    def test_case_insensitive_total(self):
        self.song["TRacKNUMBER"] = "1/10"
        self.song.write()
        self.song.reload()
        self.failUnlessEqual(self.song["tracknumber"], "1/10")

    def test_dont_save(self):
        config.set("editing", "save_to_songs", "false")
        self.song["~#rating"] = 1.0
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_to_songs", "true")
        self.failUnlessEqual(song("~#rating"), RATINGS.default)

    def test_can_change(self):
        self.failUnless(self.song.can_change())


class TTotalTagsBase(TestCase):
    """Test conversation between the tracknumber/totaltracks/tracktotal
    format and the tracknumber="x/y" format.

    """

    MAIN = None
    FALLBACK = None
    SINGLE = None

    def setUp(self):
        config.init()
        self.filename = get_temp_copy(get_data_path('empty.ogg'))

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()


class TTotalTagsMixin(object):

    def __load_tags(self, tags, expected):
        m = OggVorbis(self.filename)
        for key, value in tags.items():
            m.tags[key] = value
        m.save()
        song = OggFile(self.filename)
        for key, value in expected.items():
            self.failUnlessEqual(song(key), value)
        if self.MAIN not in expected:
            self.failIf(self.MAIN in song)
        if self.SINGLE not in expected:
            self.failIf(self.SINGLE in song)
        if self.FALLBACK not in expected:
            self.failIf(self.FALLBACK in song)

    def test_load_old_single(self):
        self.__load_tags(
            {self.SINGLE: "1/42"},
            {self.SINGLE: "1/42"})

    def test_load_main(self):
        self.__load_tags(
            {self.SINGLE: "3", self.MAIN: "10"},
            {self.SINGLE: "3/10"})

    def test_load_fallback(self):
        self.__load_tags(
            {self.SINGLE: "3", self.FALLBACK: "10"},
            {self.SINGLE: "3/10"})

    def test_load_all(self):
        self.__load_tags(
            {self.SINGLE: "3", self.FALLBACK: "10", self.MAIN: "5"},
            {self.SINGLE: "3/5", self.FALLBACK: "10"})

    def test_load_main_no_single(self):
        self.__load_tags(
            {self.MAIN: "5"},
            {self.SINGLE: "/5"})

    def test_load_fallback_no_single(self):
        self.__load_tags(
            {self.FALLBACK: "6"},
            {self.SINGLE: "/6"})

    def test_load_both_no_single(self):
        self.__load_tags(
            {self.FALLBACK: "6", self.MAIN: "5"},
            {self.FALLBACK: "6", self.SINGLE: "/5"})

    def __save_tags(self, tags, expected):
        #return
        song = OggFile(self.filename)
        for key, value in tags.items():
            song[key] = value
        song.write()
        m = OggVorbis(self.filename)
        # test if all values ended up where we wanted
        for key, value in expected.items():
            self.failUnless(key in m.tags)
            self.failUnlessEqual(m.tags[key], [value])

        # test if not specified are not there
        if self.MAIN not in expected:
            self.failIf(self.MAIN in m.tags)
        if self.FALLBACK not in expected:
            self.failIf(self.FALLBACK in m.tags)
        if self.SINGLE not in expected:
            self.failIf(self.SINGLE in m.tags)

    def test_save_single(self):
        self.__save_tags(
            {self.SINGLE: "1/2"},
            {self.SINGLE: "1", self.MAIN: "2"})

    def test_save_main(self):
        self.__save_tags(
            {self.MAIN: "3"},
            {self.MAIN: "3"})

    def test_save_fallback(self):
        self.__save_tags(
            {self.FALLBACK: "3"},
            {self.MAIN: "3"})

    def test_save_single_and_main(self):
        # not clear what to do here...
        self.__save_tags(
            {self.SINGLE: "1/2", self.MAIN: "3"},
            {self.SINGLE: "1", self.MAIN: "3"})

    def test_save_single_and_fallback(self):
        self.__save_tags(
            {self.SINGLE: "1/2", self.FALLBACK: "3"},
            {self.SINGLE: "1", self.MAIN: "2", self.FALLBACK: "3"})

    def test_save_all(self):
        # not clear what to do here...
        self.__save_tags(
            {self.SINGLE: "1/2", self.MAIN: "4", self.FALLBACK: "3"},
            {self.SINGLE: "1", self.MAIN: "4", self.FALLBACK: "3"})


class TTrackTotal(TTotalTagsBase, TTotalTagsMixin):
    MAIN = "tracktotal"
    FALLBACK = "totaltracks"
    SINGLE = "tracknumber"


class TDiscTotal(TTotalTagsBase, TTotalTagsMixin):
    MAIN = "disctotal"
    FALLBACK = "totaldiscs"
    SINGLE = "discnumber"


class TFLACFile(TVCFile, TVCFileMixin):
    def setUp(self):
        TVCFile.setUp(self)

        self.filename = get_temp_copy(get_data_path('empty.flac'))
        self.song = FLACFile(self.filename)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "FLAC")
        self.assertEqual(self.song("~codec"), "FLAC")
        self.assertEqual(self.song("~encoding"), "")

    def test_audio_props(self):
        assert self.song("~#channels") == 2
        assert self.song("~#samplerate") == 44100
        assert self.song("~#bitdepth") == 16

    def test_mime(self):
        self.failUnless(self.song.mimes)

    def test_save_empty(self):
        self.song.write()
        flac = FLAC(self.filename)
        self.failIf(flac.tags)
        self.failIf(flac.tags is None)

    def test_strip_id3(self):
        self.song["title"] = "Test"
        self.song.write()
        id3 = ID3()
        id3.add(TIT2(encoding=2, text=u"Test but differently"))
        id3.save(filename=self.filename)
        song2 = formats.MusicFile(self.filename)
        self.failUnlessEqual(type(self.song), type(song2))
        self.failUnlessEqual(self.song["title"], song2["title"])
        song2.write()
        self.assertRaises(ID3NoHeaderError, ID3, self.filename)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()


class TVCCover(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()


class TVCCoverMixin(object):

    def test_can_change_images(self):
        song = self.QLType(self.filename)
        self.assertTrue(song.can_change_images)

    def test_no_cover(self):
        song = self.QLType(self.filename)
        self.failIf(song("~picture"))
        self.failIf(song.get_primary_image())

    def test_get_images(self):
        # coverart + coverartmime
        data = _get_jpeg()
        song = self.MutagenType(self.filename)
        song["coverart"] = base64.b64encode(data).decode("ascii")
        song["coverartmime"] = u"image/jpeg"
        song.save()

        song = self.QLType(self.filename)
        self.assertEqual(len(song.get_images()), 1)
        self.assertEqual(song.get_images()[0].mime_type, "image/jpeg")

        # metadata_block_picture
        pic = Picture()
        pic.data = _get_jpeg()
        pic.type = APICType.COVER_FRONT
        b64pic_cover = base64.b64encode(pic.write()).decode("ascii")

        song = self.MutagenType(self.filename)
        song["metadata_block_picture"] = [b64pic_cover]
        song.save()

        song = self.QLType(self.filename)
        self.assertEqual(len(song.get_images()), 2)
        self.assertEqual(song.get_images()[0].type, APICType.COVER_FRONT)

    def test_handle_old_coverart(self):
        data = _get_jpeg()
        song = self.MutagenType(self.filename)
        song["coverart"] = base64.b64encode(data).decode("ascii")
        song["coverartmime"] = "image/jpeg"
        song.save()

        song = self.QLType(self.filename)
        self.failUnlessEqual(song("~picture"), "y")
        self.failIf(song("coverart"))
        self.failIf(song("coverartmime"))
        song.write()

        self.assertEqual(song.get_primary_image().mime_type, "image/jpeg")
        fn = song.get_primary_image().file
        cov_data = fn.read()
        self.failUnlessEqual(data, cov_data)

        song = self.MutagenType(self.filename)
        self.failUnlessEqual(base64.b64decode(song["coverart"][0]), data)
        self.failUnlessEqual(song["coverartmime"][0], "image/jpeg")

    def test_handle_invalid_coverart(self):
        crap = u".-a,a.f,afa-,.-"
        song = self.MutagenType(self.filename)
        song["coverart"] = crap
        song.save()

        song = self.QLType(self.filename)
        self.failUnlessEqual(song("~picture"), "y")
        self.failIf(song("coverart"))
        self.failIf(song.get_primary_image())
        self.failIf(song("~picture"))
        song.write()

        song = self.MutagenType(self.filename)
        self.failUnlessEqual(song["coverart"][0], crap)

    def test_handle_picture_block(self):
        pic = Picture()
        pic.data = _get_jpeg()
        pic.type = APICType.COVER_FRONT
        b64pic_cover = base64.b64encode(pic.write()).decode("ascii")

        pic2 = Picture()
        pic2.data = _get_jpeg(size=6)
        pic2.type = APICType.COVER_BACK
        b64pic_other = base64.b64encode(pic2.write()).decode("ascii")

        song = self.MutagenType(self.filename)
        song["metadata_block_picture"] = [b64pic_other, b64pic_cover]
        song.save()

        song = self.QLType(self.filename)
        self.failUnlessEqual(song("~picture"), "y")

        fn = song.get_primary_image().file
        self.failUnlessEqual(pic.data, fn.read())
        song.write()

        song = self.MutagenType(self.filename)
        self.failUnless(b64pic_other in song["metadata_block_picture"])
        self.failUnless(b64pic_cover in song["metadata_block_picture"])
        song["metadata_block_picture"] = [b64pic_other]
        song.save()

        song = self.QLType(self.filename)
        fn = song.get_primary_image().file
        self.failUnlessEqual(pic2.data, fn.read())

    def test_handle_invalid_picture_block(self):
        crap = ".-a,a.f,afa-,.-"
        song = self.MutagenType(self.filename)
        song["metadata_block_picture"] = crap
        song.save()

        song = self.QLType(self.filename)
        self.failUnlessEqual(song("~picture"), "y")
        self.failIf(song("metadata_block_picture"))
        self.failIf(song.get_primary_image())
        self.failIf(song("~picture"))
        song.write()

        song = self.MutagenType(self.filename)
        self.failUnlessEqual(song["metadata_block_picture"][0], crap)

    def test_handle_invalid_flac_picture(self):
        crap = b".-a,a.f,afa-,.-"
        song = self.MutagenType(self.filename)
        song["metadata_block_picture"] = base64.b64encode(crap).decode("ascii")
        song.save()
        song = self.QLType(self.filename)
        self.failIf(song.get_primary_image())
        self.failIf(song.get_images())

    def test_set_image(self):
        data = _get_jpeg()
        song = self.MutagenType(self.filename)
        song["coverart"] = base64.b64encode(data).decode("ascii")
        song["coverartmime"] = "image/jpeg"
        song.save()

        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)

        song = self.QLType(self.filename)
        self.assertTrue(song.has_images)
        self.assertTrue(song.get_primary_image())
        self.assertTrue(song.has_images)
        song.set_image(image)
        self.assertTrue(song.has_images)
        self.assertEqual(song.get_primary_image().width, 10)

        song = self.MutagenType(self.filename)
        self.assertTrue("coverart" not in song)
        self.assertTrue("coverartmime" not in song)


class TVCCoverOgg(TVCCover, TVCCoverMixin):
    def setUp(self):
        TVCCover.setUp(self)
        self.filename = get_temp_copy(get_data_path('empty.ogg'))
        self.MutagenType = OggVorbis
        self.QLType = OggFile


class TVCCoverFlac(TVCCover, TVCCoverMixin):
    def setUp(self):
        TVCCover.setUp(self)
        self.filename = get_temp_copy(get_data_path('empty.flac'))
        self.MutagenType = FLAC
        self.QLType = FLACFile


class TFlacPicture(TestCase):
    def setUp(self):
        config.init()
        self.filename = get_temp_copy(get_data_path('empty.flac'))

    def test_get_images(self):
        pic = Picture()
        pic.data = _get_jpeg()
        pic.type = APICType.COVER_FRONT
        b64pic_cover = base64.b64encode(pic.write()).decode("ascii")

        # metadata_block_picture
        song = FLAC(self.filename)
        song["metadata_block_picture"] = [b64pic_cover]
        song.save()

        song = FLACFile(self.filename)
        self.assertEqual(len(song.get_images()), 1)
        self.assertEqual(song.get_images()[0].type, APICType.COVER_FRONT)

        # flac Picture
        song = FLAC(self.filename)
        pic = Picture()
        pic.data = _get_jpeg()
        pic.type = APICType.COVER_BACK
        song.add_picture(pic)
        song.save()

        song = FLACFile(self.filename)
        self.assertEqual(len(song.get_images()), 2)
        self.assertEqual(song.get_images()[-1].type, APICType.COVER_BACK)

    def test_get_image(self):
        data = b"abc"
        song = FLAC(self.filename)
        pic = Picture()
        pic.data = data
        song.add_picture(pic)
        song.save()

        song = FLACFile(self.filename)
        self.failUnless(song("~picture"))
        fn = song.get_primary_image().file
        self.failUnlessEqual(fn.read(), pic.data)

    def test_clear_images(self):
        data = b"abc"
        song = FLAC(self.filename)
        pic = Picture()
        pic.data = data
        song.add_picture(pic)
        song.save()

        song = FLACFile(self.filename)
        self.assertTrue(song.get_primary_image())
        song.clear_images()
        song.clear_images()
        song = FLACFile(self.filename)
        self.assertFalse(song.get_primary_image())

    def test_set_image(self):
        fileobj = BytesIO(b"foo")
        image = EmbeddedImage(fileobj, "image/jpeg", 10, 10, 8)

        song = FLACFile(self.filename)
        self.assertFalse(song.get_primary_image())
        song.set_image(image)
        self.assertEqual(song.get_primary_image().width, 10)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()


class TOggFile(TVCFile, TVCFileMixin):
    def setUp(self):
        TVCFile.setUp(self)

        self.filename = get_temp_copy(get_data_path('empty.ogg'))
        self.song = OggFile(self.filename)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

    def test_audio_props(self):
        assert self.song("~#samplerate") == 44100

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "Ogg Vorbis")
        self.assertEqual(self.song("~codec"), "Ogg Vorbis")
        self.assertEqual(self.song("~encoding"), "")


@skipUnless(OggOpus, "Ogg Opus mutagen support missing")
class TOggOpusFile(TVCFile, TVCFileMixin):
    def setUp(self):
        TVCFile.setUp(self)

        self.filename = get_temp_copy(get_data_path('empty.opus'))
        self.song = OggOpusFile(self.filename)

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.6847, 3)
        self.failUnless("opusenc" in self.song("encoder"))

    def test_channels(self):
        assert self.song("~#channels") == 2

    def test_sample_rate(self):
        assert self.song("~#samplerate") == 48000

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "Ogg Opus")
        self.assertEqual(self.song("~codec"), "Ogg Opus")
        self.assertEqual(self.song("~encoding"), "libopus 0.9.14")

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()
