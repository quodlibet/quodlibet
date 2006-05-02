from tests import TestCase

import shutil

import formats._vorbis

class TVCFile(TestCase):
    # Mixin to test Vorbis writing features

    def test_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_deletes_rating(self):
        formats._vorbis.EMAIL = "foo@bar.org"
        self.song["~#rating"] = 0.2
        self.song.write()
        self.song["~#rating"] = 0.5
        self.song.write()
        song = type(self.song)(self.filename)
        formats._vorbis.EMAIL = formats._vorbis.DEFAULT_EMAIL
        self.failUnlessEqual(song["~#rating"], 0.5)

    def test_new_email_rating(self):
        formats._vorbis.EMAIL = "foo@bar.org"
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        formats._vorbis.EMAIL = formats._vorbis.DEFAULT_EMAIL
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_default_email_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        formats._vorbis.EMAIL = "foo@bar.org"
        formats._vorbis.EMAIL = formats._vorbis.DEFAULT_EMAIL
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_different_email_rating(self):
        formats._vorbis.EMAIL = "foo@bar.org"
        self.song["~#rating"] = 0.2
        self.song.write()
        formats._vorbis.EMAIL = formats._vorbis.DEFAULT_EMAIL
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#rating"], 0.5)

        song.write()
        formats._vorbis.EMAIL = "foo@bar.org"
        song = type(self.song)(self.filename)
        formats._vorbis.EMAIL = formats._vorbis.DEFAULT_EMAIL
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_invalid_rating(self):
        self.song["~#rating"] = "invalid"
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#rating"], 0.5)

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

    def test_can_change(self):
        self.failUnless(self.song.can_change())
