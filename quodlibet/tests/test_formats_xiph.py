from tests import add, TestCase

import os
import shutil
import tempfile
import base64

from quodlibet import config, const, formats
from quodlibet.formats.xiph import OggFile, FLACFile, OggOpusFile, OggOpus

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, TIT2, ID3NoHeaderError
from mutagen.oggvorbis import OggVorbis

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
        self.song["~#rating"] = const.DEFAULT_RATING
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song("~#rating"), const.DEFAULT_RATING)

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
        self.failUnlessEqual(song("~#rating"), const.DEFAULT_RATING)

        song.write()
        config.set("editing", "save_email", "foo@bar.org")
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_invalid_rating(self):
        self.song["~#rating"] = "invalid"
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song("~#rating"), const.DEFAULT_RATING)

    def test_huge_playcount(self):
        count = 1000000000000000L
        self.song["~#playcount"] = count
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#playcount"], count)

    def test_totaltracks(self):
        self.song["tracknumber"] = "1"
        self.song["totaltracks"] = "1"
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["tracknumber"], "1/1")
        self.failIf("totaltracks" in song)

    def test_tracktotal(self):
        self.song["tracknumber"] = "1"
        self.song["tracktotal"] = "1"
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["tracknumber"], "1/1")
        self.failIf("tracktotal" in song)

    def test_parameter(self):
        for bad in ["rating", "playcount", "rating:foo", "playcount:bar"]:
            self.failIf(self.song.can_change(bad))

    def test_dont_save(self):
        config.set("editing", "save_to_songs", "false")
        self.song["~#rating"] = 1.0
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_to_songs", "true")
        self.failUnlessEqual(song("~#rating"), const.DEFAULT_RATING)

    def test_can_change(self):
        self.failUnless(self.song.can_change())


class TOggVorbis(TestCase):
    def setUp(self):
        config.init()
        self.filename = tempfile.mkstemp(".ogg")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.ogg'), self.filename)

    def test_load_new(self):
        m = OggVorbis(self.filename)
        m.tags["tracknumber"] = "3"
        m.tags["totaltracks"] = "10"
        m.save()

        song = OggFile(self.filename)
        self.failUnlessEqual(song["tracknumber"], "3/10")

    def test_load_old_format(self):
        m = OggVorbis(self.filename)
        m.tags["tracknumber"] = "6/7"
        m.save()

        song = OggFile(self.filename)
        self.failUnlessEqual(song["tracknumber"], "6/7")

    def test_toaltracks_save(self):
        self.failIf(OggVorbis(self.filename).tags)
        song = OggFile(self.filename)
        song["tracknumber"] = "4/5"
        song.write()

        m = OggVorbis(self.filename)
        self.failUnlessEqual(m.tags["tracknumber"], ["4"])
        self.failUnlessEqual(m.tags["totaltracks"], ["5"])

    def test_save_single(self):
        song = OggFile(self.filename)
        song["tracknumber"] = "12"
        song.write()

        m = OggVorbis(self.filename)
        self.failUnlessEqual(m.tags["tracknumber"], ["12"])
        self.failIf("totaltracks" in m.tags)

    def test_both(self):
        song = OggFile(self.filename)
        song["tracknumber"] = "1/50"
        song["totaltracks"] = "100"
        song.write()
        song.reload()
        self.failUnlessEqual(song["tracknumber"], "1/100")

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()
add(TOggVorbis)


class TFLACFile(TVCFile):
    def setUp(self):
        TVCFile.setUp(self)
        self.filename = tempfile.mkstemp(".flac")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.flac'), self.filename)
        self.song = FLACFile(self.filename)

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
        import gtk
        pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, size, size)
        fn = tempfile.NamedTemporaryFile()
        pb.save(fn.name, "jpeg")
        return fn.read()

    def test_no_cover(self):
        song = self.QLType(self.filename)
        self.failIf(song("~picture"))
        self.failIf(song.find_cover())

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

        fn = song.find_cover()
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
        self.failIf(song.find_cover())
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

        fn = song.find_cover()
        self.failUnlessEqual(pic.data, fn.read())
        song.write()

        song = self.MutagenType(self.filename)
        self.failUnless(b64pic_other in song["metadata_block_picture"])
        self.failUnless(b64pic_cover in song["metadata_block_picture"])
        song["metadata_block_picture"] = [b64pic_other]
        song.save()

        song = self.QLType(self.filename)
        fn = song.find_cover()
        self.failUnlessEqual(pic2.data, fn.read())

    def test_handle_invalid_picture_block(self):
        crap = ".-a,a.f,afa-,.-"
        song = self.MutagenType(self.filename)
        song["metadata_block_picture"] = crap
        song.save()

        song = self.QLType(self.filename)
        self.failUnlessEqual(song("~picture"), "y")
        self.failIf(song("metadata_block_picture"))
        self.failIf(song.find_cover())
        self.failIf(song("~picture"))
        song.write()

        song = self.MutagenType(self.filename)
        self.failUnlessEqual(song["metadata_block_picture"][0], crap)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()


class TVCCoverOgg(TVCCover):
    def setUp(self):
        TVCCover.setUp(self)
        self.filename = tempfile.mkstemp(".ogg")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.ogg'), self.filename)
        self.MutagenType = OggVorbis
        self.QLType = OggFile
add(TVCCoverOgg)


class TVCCoverFlac(TVCCover):
    def setUp(self):
        TVCCover.setUp(self)
        self.filename = tempfile.mkstemp(".flac")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.flac'), self.filename)
        self.MutagenType = FLAC
        self.QLType = FLACFile
add(TVCCoverFlac)


class TFlacPicture(TestCase):
    def setUp(self):
        config.init()
        self.filename = tempfile.mkstemp(".flac")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.flac'), self.filename)

    def test_picture(self):
        data = "abc"
        song = FLAC(self.filename)
        pic = Picture()
        pic.data = data
        song.add_picture(pic)
        song.save()

        song = FLACFile(self.filename)
        self.failUnless(song("~picture"))
        fn = song.find_cover()
        self.failUnlessEqual(fn.read(), pic.data)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()
add(TFlacPicture)


class TOggFile(TVCFile):
    def setUp(self):
        TVCFile.setUp(self)
        self.filename = tempfile.mkstemp(".ogg")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.ogg'), self.filename)
        self.song = OggFile(self.filename)

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()
add(TOggFile)


class TOggOpusFile(TVCFile):
    def setUp(self):
        TVCFile.setUp(self)
        self.filename = tempfile.mkstemp(".ogg")[1]
        shutil.copy(os.path.join('tests', 'data', 'empty.opus'), self.filename)
        self.song = OggOpusFile(self.filename)

    def test_length(self):
        self.failUnlessEqual(self.song("~#length"), 3)
        self.failUnless("opusenc" in self.song("encoder"))

    def tearDown(self):
        os.unlink(self.filename)
        config.quit()

if OggOpus:
    add(TOggOpusFile)

