from tests import TestCase, add

from quodlibet.qltk.tagsfrompath import TagsFromPattern
from quodlibet.qltk.tagsfrompath import TitleCase, SplitTag, UnderscoresToSpaces
import quodlibet.config

class FilterTestCase(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.c = self.Kind()
    def tearDown(self):
        self.c.destroy()
        quodlibet.config.quit()

class TTitleCase(FilterTestCase):
    Kind = TitleCase
    def test_simple(self):
        self.failUnlessEqual(self.c.filter("title", "foo bar"), "Foo Bar")
    def test_apostrophe(self):
        self.failUnlessEqual(self.c.filter("title", "IT's"), "IT's")

add(TTitleCase)

class TSplitTag(FilterTestCase):
    Kind = SplitTag
    def test_simple(self):
        self.failUnlessEqual(self.c.filter("title", "foo & bar"), "foo\nbar")
add(TSplitTag)

class TUnderscoresToSpaces(FilterTestCase):
    Kind = UnderscoresToSpaces
    def test_simple(self):
        self.failUnlessEqual(self.c.filter("titke", "foo_bar"), "foo bar")
add(TUnderscoresToSpaces)

class TTagsFromPattern(TestCase):
    def setUp(self):
        self.f1 = '/path/Artist/Album/01 - Title.mp3'
        self.f2 = '/path/Artist - Album/01. Title.mp3'
        self.f3 = '/path/01 - Artist - Title.mp3'
        self.b1 = '/path/01 - Title'
        self.b2 = '/path/01 - Artist - Title'
        self.nomatch = {}

    def test_songtypes(self):
        from quodlibet import formats
        pat = TagsFromPattern('<tracknumber>. <title>')
        tracktitle = {'tracknumber': '01', 'title': 'Title' }
        for ext, kind in formats._infos.iteritems():
            f = formats._audio.AudioFile()
            if not isinstance(kind, type):
                continue
            f.__class__ = kind
            f["~filename"] = '/path/Artist - Album/01. Title' + ext
            self.assertEquals(pat.match(f), tracktitle, ext)

    def test_skip(self):
        pat = TagsFromPattern('<path>/<~>/<~>/<tracknumber> - <title>')
        self.failUnlessEqual(len(pat.headers), 3)
        song = pat.match({"~filename":self.f1})
        self.failUnlessEqual(song.get("path"), "path")
        self.failUnlessEqual(song.get("title"), "Title")
        self.failIf(song.get("album"))
        self.failIf(song.get("artist"))

    def test_dict(self):
        tracktitle = {'tracknumber': '01', 'title': 'Title' }
        pat = TagsFromPattern('<tracknumber> - <title>')
        self.assertEquals(pat.match({"~filename":self.f1}), tracktitle)

    def test_nongreedy(self):
        pat = TagsFromPattern('<artist> - <title>')
        dic = pat.match("Prefuse 73 - The End of Biters - International.ogg")
        self.assertEquals(dic["artist"], "Prefuse 73")
        self.assertEquals(dic["title"], "The End of Biters - International")

    def test_empty(self):
        pat = TagsFromPattern('')
        self.assertEquals(pat.match(self.f1), self.nomatch)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), self.nomatch)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_tracktitle(self):
        tracktitle = {'tracknumber': '01', 'title': 'Title' }
        btracktitle = {'tracknumber': '01', 'title': 'Artist - Title' }
        pat = TagsFromPattern('<tracknumber> - <title>')
        self.assertEquals(pat.match(self.f1), tracktitle)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), btracktitle)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_path(self):
        albumtracktitle = {'tracknumber': '01', 'title': 'Title',
                           'album': 'Album' }
        balbumtracktitle = {'tracknumber': '01', 'title': 'Artist - Title',
                            'album': 'path' }
        pat = TagsFromPattern('<album>/<tracknumber> - <title>')
        self.assertEquals(pat.match(self.f1), albumtracktitle)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), balbumtracktitle)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_all(self):
        all = {'tracknumber': '01', 'title': 'Title',
               'album': 'Album', 'artist': 'Artist' }
        pat = TagsFromPattern('<artist>/<album>/<tracknumber> - <title>')
        self.assertEquals(pat.match(self.f1), all)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), self.nomatch)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_post(self):
        btracktitle = {'tracknumber': '01', 'title': 'Titl' }
        vbtracktitle = {'tracknumber': '01', 'title': 'Artist - Titl' }
        pat = TagsFromPattern('<tracknumber> - <title>e')
        self.assertEquals(pat.match(self.f1), btracktitle)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), vbtracktitle)
        self.assertEquals(pat.match(self.b1), btracktitle)
        self.assertEquals(pat.match(self.b2), vbtracktitle)

    def test_nofakes(self):
        pat = TagsFromPattern('<~#track> - <title>')
        self.assertEquals(pat.match(self.f1), self.nomatch)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), self.nomatch)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_disctrack(self):
        pat = TagsFromPattern('<discnumber><tracknumber>. <title>')
        self.assertEquals(pat.match('101. T1.ogg'),
            dict(discnumber='1', tracknumber='01', title='T1'))
        self.assertEquals(pat.match('1318. T18.ogg'),
            dict(discnumber='13', tracknumber='18', title='T18'))
        self.assertEquals(pat.match('24. T4.ogg'),
            dict(discnumber='2', tracknumber='4', title='T4'))
add(TTagsFromPattern)
