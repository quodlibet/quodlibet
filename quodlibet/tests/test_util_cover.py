# -*- coding: utf-8 -*-
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import glob
import os

from senf import fsnative

from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.util.cover.manager import CoverManager
from quodlibet.util.path import normalize_path

from tests import TestCase, DATA_DIR


quux = AudioFile({
    "~filename": os.path.join(DATA_DIR, "asong.ogg"),
    "album": u"Quuxly",
})

bar_2_1 = AudioFile({
    "~filename": fsnative(u"does not/exist"),
    "title": "more songs",
    "discnumber": "2/2", "tracknumber": "1",
    "artist": "Foo\nI have two artists", "album": "Bar",
    "lyricist": "Foo", "composer": "Foo", "performer": "I have two artists",
})


class TCoverManager(TestCase):

    def setUp(self):
        config.init()
        self.manager = CoverManager()

        self.dir = os.path.realpath(quux("~dirname"))
        # Safety check
        self.failIf(glob.glob(self.dir + "/*.jpg"))
        self.files = [self.full_path("12345.jpg"),
                      self.full_path("nothing.jpg")
                      ]
        for f in self.files:
            open(f, "w").close()

    def _find_cover(self, song):
        return self.manager.get_cover(song)

    def tearDown(self):
        for f in self.files:
            os.unlink(f)
        config.quit()

    def full_path(self, path):
        return os.path.join(self.dir, path)

    def test_dir_not_exist(self):
        self.failIf(self._find_cover(bar_2_1))

    def test_nothing(self):
        self.failIf(self._find_cover(quux))

    def test_labelid(self):
        quux["labelid"] = "12345"
        self.failUnlessEqual(os.path.abspath(self._find_cover(quux).name),
                             self.full_path("12345.jpg"))
        del(quux["labelid"])

    def test_regular(self):
        for fn in ["cover.png", "folder.jpg", "frontcover.jpg",
                   "front_folder_cover.gif", "jacket_cover.front.folder.jpeg"]:
            f = self.add_file(fn)
            self.failUnlessEqual(
                os.path.abspath(self._find_cover(quux).name), f)
        self.test_labelid() # labelid must work with other files present

    def test_file_encoding(self):
        if os.name == "nt":
            return

        f = self.add_file("\xff\xff\xff\xff - cover.jpg")
        self.assertTrue(isinstance(quux("album"), unicode))
        h = self._find_cover(quux)
        self.assertEqual(h.name, normalize_path(f))

    def test_intelligent(self):
        song = quux
        song["artist"] = "Q-Man"
        song["title"] = "First Q falls hardest"
        fns = ["Quuxly - back.jpg", "Quuxly.jpg", "q-man - quxxly.jpg",
                  "folder.jpeg", "Q-man - Quuxly (FRONT).jpg"]
        for fn in fns:
            f = self.add_file(fn)
            cover = self._find_cover(song)
            if cover:
                actual = os.path.abspath(cover.name)
                self.failUnlessEqual(actual, f)
            else:
                # Here, no cover is better than the back...
                self.failUnlessEqual(f, self.full_path("Quuxly - back.jpg"))

    def test_embedded_special_cover_words(self):
        """Tests that words incidentally containing embedded "special" words
        album keywords (e.g. cover, disc, back) don't trigger
        See Issue 818"""

        song = AudioFile({
            "~filename": fsnative(os.path.join(self.dir, u"asong.ogg")),
            "album": "foobar",
            "title": "Ode to Baz",
            "artist": "Q-Man",
        })
        data = [('back.jpg', False),
                ('discovery.jpg', False),
                ("Pharell - frontin'.jpg", False),
                ('nickelback - Curb.jpg', False),
                ('foobar.jpg', True),
                ('folder.jpg', True),  # Though this order is debatable
                ('Q-Man - foobar.jpg', True),
                ('Q-man - foobar (cover).jpg', True)]
        for fn, should_find in data:
            f = self.add_file(fn)
            cover = self._find_cover(song)
            if cover:
                actual = os.path.abspath(cover.name)
                self.failUnlessEqual(
                    actual, f, "\"%s\" should trump \"%s\"" % (f, actual))
            else:
                self.failIf(should_find, msg="Couldn't find %s for %s" %
                                             (f, song("~filename")))

    def add_file(self, fn):
        f = self.full_path(fn)
        open(f, "w").close()
        self.files.append(f)
        return f

    def test_multiple_people(self):
        song = AudioFile({
            "~filename": fsnative(os.path.join(self.dir, u"asong.ogg")),
            "album": "foobar",
            "title": "Ode to Baz",
            "performer": "The Performer",
            "artist": "The Composer\nThe Conductor",
            "composer": "The Composer",
        })
        for fn in ["foobar.jpg",
                   "The Performer - foobar.jpg",
                   "The Composer: The Performer - foobar.jpg",
                   "The Composer: The Conductor, The Performer - foobar.jpg"]:
            f = self.add_file(fn)
            cover = self._find_cover(song)
            self.failUnless(cover)
            actual = os.path.abspath(cover.name)
            self.failUnlessEqual(
                    actual, f, "\"%s\" should trump \"%s\"" % (f, actual))

    def test_get_thumbnail(self):
        self.assertTrue(self.manager.get_pixbuf(quux, 10, 10) is None)
        self.assertTrue(self.manager.get_pixbuf_many([quux], 10, 10) is None)
