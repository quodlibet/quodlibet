# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

import os

from senf import fsnative

from quodlibet.util.tagsfrompath import TagsFromPattern


class TTagsFromPattern(TestCase):

    def setUp(self):
        if os.name == "nt":
            self.f1 = u"C:\\path\\Artist\\Album\\01 - Title.mp3"
            self.f2 = u"C:\\path\\Artist - Album\\01. Title.mp3"
            self.f3 = u"C:\\path\\01 - Artist - Title.mp3"
            self.b1 = u"C:\\path\\01 - Title"
            self.b2 = u"C:\\path\\01 - Artist - Title"

        else:
            self.f1 = "/path/Artist/Album/01 - Title.mp3"
            self.f2 = "/path/Artist - Album/01. Title.mp3"
            self.f3 = "/path/01 - Artist - Title.mp3"
            self.b1 = "/path/01 - Title"
            self.b2 = "/path/01 - Artist - Title"
        self.nomatch = {}

    def test_songtypes(self):
        from quodlibet import formats
        pat = TagsFromPattern("<tracknumber>. <title>")
        tracktitle = {"tracknumber": "01", "title": "Title"}
        for ext, kind in formats.loaders.items():
            f = formats._audio.AudioFile()
            if not isinstance(kind, type):
                continue
            f.__class__ = kind
            if os.name == "nt":
                f["~filename"] = u"C:\\path\\Artist - Album\\01. Title" + ext
            else:
                f["~filename"] = "/path/Artist - Album/01. Title" + ext
            self.assertEquals(pat.match(f), tracktitle, ext)

    def test_skip(self):
        if os.name == "nt":
            pat = TagsFromPattern("<path>\\<~>\\<~>\\<tracknumber> - <title>")
        else:
            pat = TagsFromPattern("<path>/<~>/<~>/<tracknumber> - <title>")
        self.failUnlessEqual(len(pat.headers), 3)
        song = pat.match({"~filename": self.f1})
        self.failUnlessEqual(song.get("path"), "path")
        self.failUnlessEqual(song.get("title"), "Title")
        self.failIf(song.get("album"))
        self.failIf(song.get("artist"))

    def test_dict(self):
        tracktitle = {"tracknumber": "01", "title": "Title"}
        pat = TagsFromPattern("<tracknumber> - <title>")
        self.assertEquals(pat.match({"~filename": self.f1}), tracktitle)

    def test_nongreedy(self):
        pat = TagsFromPattern("<artist> - <title>")
        dic = pat.match_path(
            fsnative(u"Prefuse 73 - The End of Biters - International.ogg"))
        self.assertEquals(dic["artist"], "Prefuse 73")
        self.assertEquals(dic["title"], "The End of Biters - International")

    def test_empty(self):
        pat = TagsFromPattern("")
        self.assertEquals(pat.match_path(self.f1), self.nomatch)
        self.assertEquals(pat.match_path(self.f2), self.nomatch)
        self.assertEquals(pat.match_path(self.f3), self.nomatch)
        self.assertEquals(pat.match_path(self.b1), self.nomatch)
        self.assertEquals(pat.match_path(self.b2), self.nomatch)

    def test_tracktitle(self):
        tracktitle = {"tracknumber": "01", "title": "Title"}
        btracktitle = {"tracknumber": "01", "title": "Artist - Title"}
        pat = TagsFromPattern("<tracknumber> - <title>")
        self.assertEquals(pat.match_path(self.f1), tracktitle)
        self.assertEquals(pat.match_path(self.f2), self.nomatch)
        self.assertEquals(pat.match_path(self.f3), btracktitle)
        self.assertEquals(pat.match_path(self.b1), self.nomatch)
        self.assertEquals(pat.match_path(self.b2), self.nomatch)

    def test_path(self):
        albumtracktitle = {"tracknumber": "01", "title": "Title",
                           "album": "Album"}
        balbumtracktitle = {"tracknumber": "01", "title": "Artist - Title",
                            "album": "path"}
        if os.name == "nt":
            pat = TagsFromPattern("<album>\\<tracknumber> - <title>")
        else:
            pat = TagsFromPattern("<album>/<tracknumber> - <title>")
        self.assertEquals(pat.match_path(self.f1), albumtracktitle)
        self.assertEquals(pat.match_path(self.f2), self.nomatch)
        self.assertEquals(pat.match_path(self.f3), balbumtracktitle)
        self.assertEquals(pat.match_path(self.b1), self.nomatch)
        self.assertEquals(pat.match_path(self.b2), self.nomatch)

    def test_all(self):
        all = {"tracknumber": "01", "title": "Title",
               "album": "Album", "artist": "Artist"}
        if os.name == "nt":
            pat = TagsFromPattern("<artist>\\<album>\\<tracknumber> - <title>")
        else:
            pat = TagsFromPattern("<artist>/<album>/<tracknumber> - <title>")
        self.assertEquals(pat.match_path(self.f1), all)
        self.assertEquals(pat.match_path(self.f2), self.nomatch)
        self.assertEquals(pat.match_path(self.f3), self.nomatch)
        self.assertEquals(pat.match_path(self.b1), self.nomatch)
        self.assertEquals(pat.match_path(self.b2), self.nomatch)

    def test_post(self):
        btracktitle = {"tracknumber": "01", "title": "Titl"}
        vbtracktitle = {"tracknumber": "01", "title": "Artist - Titl"}
        pat = TagsFromPattern("<tracknumber> - <title>e")
        self.assertEquals(pat.match_path(self.f1), btracktitle)
        self.assertEquals(pat.match_path(self.f2), self.nomatch)
        self.assertEquals(pat.match_path(self.f3), vbtracktitle)
        self.assertEquals(pat.match_path(self.b1), btracktitle)
        self.assertEquals(pat.match_path(self.b2), vbtracktitle)

    def test_nofakes(self):
        pat = TagsFromPattern("<~#track> - <title>")
        self.assertEquals(pat.match_path(self.f1), self.nomatch)
        self.assertEquals(pat.match_path(self.f2), self.nomatch)
        self.assertEquals(pat.match_path(self.f3), self.nomatch)
        self.assertEquals(pat.match_path(self.b1), self.nomatch)
        self.assertEquals(pat.match_path(self.b2), self.nomatch)

    def test_disctrack(self):
        pat = TagsFromPattern("<discnumber><tracknumber>. <title>")
        self.assertEquals(pat.match_path(fsnative(u"101. T1.ogg")),
                          {"discnumber": "1", "tracknumber": "01", "title": "T1"})
        self.assertEquals(pat.match_path(fsnative(u"1318. T18.ogg")),
                          {"discnumber": "13", "tracknumber": "18", "title": "T18"})
        self.assertEquals(pat.match_path(fsnative(u"24. T4.ogg")),
                          {"discnumber": "2", "tracknumber": "4", "title": "T4"})
