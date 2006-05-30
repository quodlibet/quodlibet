from tests import TestCase

import shutil

import config
import const
import formats._vorbis

class TVCFile(TestCase):
    # Mixin to test Vorbis writing features

    def test_rating(self):
        self.song["~#rating"] = 0.2
        self.song.write()
        song = type(self.song)(self.filename)
        self.failUnlessEqual(song["~#rating"], 0.2)

    def test_deletes_rating(self):
        config.set("editing", "save_email", "foo@bar.org")
        self.song["~#rating"] = 0.2
        self.song.write()
        self.song["~#rating"] = 0.5
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
        self.failUnlessEqual(song["~#rating"], 0.5)

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
        self.failUnlessEqual(song["~#rating"], 0.5)

        song.write()
        config.set("editing", "save_email", "foo@bar.org")
        song = type(self.song)(self.filename)
        config.set("editing", "save_email", const.EMAIL)
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

    def test_dont_save(self):
        config.set("editing", "save_to_songs", "false")
        self.song["~#rating"] = 1.0
        self.song.write()
        song = type(self.song)(self.filename)
        config.set("editing", "save_to_songs", "true")
        self.failUnlessEqual(song["~#rating"], 0.5)

    def test_can_change(self):
        self.failUnless(self.song.can_change())
