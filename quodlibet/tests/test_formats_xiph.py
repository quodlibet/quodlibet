from quodlibet.config import RATINGS
from tests import add, TestCase, DATA_DIR, mkstemp

import os
import sys
import shutil
import base64
import StringIO

from quodlibet import config, const, formats
from quodlibet.formats.xiph import OggFile, FLACFile, OggOpusFile, OggOpus
from quodlibet.formats._image import EmbeddedImage

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, ID3NoHeaderError
from mutagen.oggvorbis import OggVorbis


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

add(TXiphPickle)


class TVCFile(TestCase):
    # Mixin to test Vorbis writing features

    def setUp(self):
        config.init()
        config.set("editing", "save_email", "")
        config.set("editing", "save_to_songs", "1")

    def test_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_deletes_rating(self):
        config.set("editing", "save_email", "foo@bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        self.song["~#rating"] = RATINGS.default
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song("~#rating"), RATINGS.default)

    def test_new_email_rating(self):
        config.set("editing", "save_email", "foo@bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_default_email_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", "foo@bar.org")
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_different_email_rating(self):
        config.set("editing", "save_email", "foo@bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        config.set("editing", "save_email", const.EMAIL)
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song("~#rating"), RATINGS.default)

        song.write()
        config.set("editing", "save_email", "foo@bar.org")
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_invalid_rating(self):
        self.song["~#rating"] = "invalid"
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song("~#rating"), RATINGS.default)

    def test_huge_playcount(self):
        count = 1000000000000000L
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
        self.filename = mkstemp(".ogg")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.ogg'), self.filename)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

    def __load_tags(self, tags, expected):
        m = OggVorbis(self.filename)
        for key, value in tags.iteritems():
            m.tags[key] = value
        m.save()
        song = OggFile(self.filename)
        for key, value in expected.iteritems():
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
        for key, value in tags.iteritems():
            song[key] = value
        song.write()
        m = OggVorbis(self.filename)
        # test if all values ended up where we wanted
        for key, value in expected.iteritems():
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


class TTrackTotal(TTotalTagsBase):
    MAIN = "tracktotal"
    FALLBACK = "totaltracks"
    SINGLE = "tracknumber"
add(TTrackTotal)


class TDiscTotal(TTotalTagsBase):
    MAIN = "disctotal"
    FALLBACK = "totaldiscs"
    SINGLE = "discnumber"
add(TDiscTotal)


class TFLACFile(TVCFile):
    def setUp(self):
        TVCFile.setUp(self)
        self.filename = mkstemp(".flac")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.flac'), self.filename)
        self.song = FLACFile(self.filename)

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
add(TFLACFile)


class TVCCover(TestCase):
    def setUp(self):
        config.init()

    def __get_jpeg(self, size=5):
        from gi.repository import GdkPixbuf
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, size, size)
        fd, fn = mkstemp()
        pb.savev(fn, "jpeg", [], [])
        with os.fdopen(fd) as h:
            data = h.read()
        os.unlink(fn)
        return data

    def test_can_change_images(self):
        song = self.QLType(self.filename)
        self.assertTrue(song.can_change_images)

    def test_no_cover(self):
        song = self.QLType(self.filename)
        self.failIf(song("~picture"))
        self.failIf(song.get_primary_image())

    def test_handle_old_coverart(self):
        data = self.__get_jpeg()
        song = self.MutagenType(self.filename)
        song["coverart"] = base64.b64encode(data)
        song["coverartmime"] = "image/jpeg"
        song.save()

        song = self.QLType(self.filename)
        self.failUnlessEqual(song("~picture"), "y")
        self.failIf(song("coverart"))
        self.failIf(song("coverartmime"))
        song.write()

        fn = song.get_primary_image().file
        cov_data = fn.read()
        self.failUnlessEqual(data,cov_data)

        song = self.MutagenType(self.filename)
        self.failUnlessEqual(base64.b64decode(song["coverart"][0]), data)
        self.failUnlessEqual(song["coverartmime"][0], "image/jpeg")

    def test_handle_invalid_coverart(self):
        crap = ".-a,a.f,afa-,.-"
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
        pic.data = self.__get_jpeg()
        pic.type = 3
        b64pic_cover = base64.b64encode(pic.write())

        pic2 = Picture()
        pic2.data = self.__get_jpeg(size=6)
        pic2.type = 4
        b64pic_other= base64.b64encode(pic2.write())

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

    def test_set_image(self):
        data = self.__get_jpeg()
        song = self.MutagenType(self.filename)
        song["coverart"] = base64.b64encode(data)
        song["coverartmime"] = "image/jpeg"
        song.save()

        fileobj = StringIO.StringIO("foo")
        image = EmbeddedImage("image/jpeg", 10, 10, 8, fileobj)

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

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()


class TVCCoverOgg(TVCCover):
    def setUp(self):
        TVCCover.setUp(self)
        self.filename = mkstemp(".ogg")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.ogg'), self.filename)
        self.MutagenType = OggVorbis
        self.QLType = OggFile
add(TVCCoverOgg)


class TVCCoverFlac(TVCCover):
    def setUp(self):
        TVCCover.setUp(self)
        self.filename = mkstemp(".flac")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.flac'), self.filename)
        self.MutagenType = FLAC
        self.QLType = FLACFile
add(TVCCoverFlac)


class TFlacPicture(TestCase):
    def setUp(self):
        config.init()
        self.filename = mkstemp(".flac")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.flac'), self.filename)

    def test_get_image(self):
        data = "abc"
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
        data = "abc"
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
        fileobj = StringIO.StringIO("foo")
        image = EmbeddedImage("image/jpeg", 10, 10, 8, fileobj)

        song = FLACFile(self.filename)
        self.assertFalse(song.get_primary_image())
        song.set_image(image)
        self.assertEqual(song.get_primary_image().width, 10)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

add(TFlacPicture)


class TOggFile(TVCFile):
    def setUp(self):
        TVCFile.setUp(self)
        self.filename = mkstemp(".ogg")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.ogg'), self.filename)
        self.song = OggFile(self.filename)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()
add(TOggFile)


class TOggOpusFile(TVCFile):
    def setUp(self):
        TVCFile.setUp(self)
        self.filename = mkstemp(".ogg")[1]
        shutil.copy(os.path.join(DATA_DIR, 'empty.opus'), self.filename)
        self.song = OggOpusFile(self.filename)

    def test_length(self):
        self.failUnlessEqual(self.song("~#length"), 3)
        self.failUnless("opusenc" in self.song("encoder"))

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

if OggOpus:
    add(TOggOpusFile)

