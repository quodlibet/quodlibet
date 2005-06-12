from unittest import TestCase, makeSuite
from tests import registerCase

import __builtin__
__builtin__.__dict__['_'] = lambda a: a

import util
from util import re_esc, encode, decode, mkdir, iscommand
from util import find_subtitle, split_album, split_title, split_value
from util import PatternFromFile, FileFromPattern
from util import format_time_long as f_t_l

import os

class FSTests(TestCase):
    def test_mkdir(self):
        self.failUnless(not os.path.isdir("nonext"))
        mkdir("nonext/test/test2/test3")
        self.failUnless(os.path.isdir("nonext/test/test2/test3"))
        self.failUnless(os.path.isdir("nonext/test/test2"))
        os.rmdir("nonext/test/test2/test3")
        os.rmdir("nonext/test/test2")
        os.rmdir("nonext/test")
        mkdir("nonext/test/foo")
        self.failUnless(os.path.isdir("nonext/test/foo"))
        os.rmdir("nonext/test/foo")
        os.rmdir("nonext/test")
        mkdir("nonext")
        os.rmdir("nonext")
        self.failUnless(not os.path.isdir("nonext"))

    def test_iscommand(self):
        self.failUnless(iscommand("ls"))
        self.failUnless(iscommand("/bin/ls"))
        self.failIf(iscommand("/bin/asdfjkl"))
        self.failIf(iscommand("asdfjkl"))
        self.failIf(iscommand(""))

    def test_mtime(self):
        self.failUnlessEqual(util.mtime("."), os.path.getmtime("."))
        self.failUnlessEqual(util.mtime("doesnotexist"), 0)

    def test_fscoding(self):
        import locale
        if locale.getpreferredencoding() != "UTF-8":
            print "WARNING: Skipping fscoding test."
        else:
            try:
                self.failUnlessEqual(util.fscoding(), "utf-8")
                import os
                os.environ["CHARSET"] = "ascii"
                self.failUnlessEqual(util.fscoding(), "ascii")
            finally:
                del(os.environ["CHARSET"])

    def test_unexpand(self):
        d = os.path.expanduser("~")
        self.failUnlessEqual(util.unexpand(d), "~")
        self.failUnlessEqual(util.unexpand(d + "/"), "~/")
        self.failUnlessEqual(util.unexpand(d + "foobar/"), d + "foobar/")
        self.failUnlessEqual(util.unexpand(os.path.join(d, "la/la")),"~/la/la")

class StringTests(TestCase):
    def test_to(self):
        self.assertEqual(type(util.to("foo")), str)
        self.assertEqual(type(util.to(u"foo")), str)
        self.assertEqual(util.to("foo"), "foo")
        self.assertEqual(util.to(u"foo"), "foo")

    def test_rating(self):
        self.failUnlessEqual(util.format_rating(0), "")
        for i in range(1, 5):
            self.failUnlessEqual(i, len(util.format_rating(i)))
        self.failUnlessEqual(util.format_rating(2.5), util.format_rating(2))

    def test_escape(self):
        for s in ["foo&amp;", "<&>", "&", "&amp;", "<&testing&amp;>amp;"]:
            esc = util.escape(s)
            self.failIfEqual(s, esc)
            self.failUnlessEqual(s, util.unescape(esc))
        self.failUnlessEqual(util.escape(""), "")

    def test_re_esc(self):
        self.failUnlessEqual(re_esc(""), "")
        self.failUnlessEqual(re_esc("fo o"), "fo o")
        self.failUnlessEqual(re_esc("!bar"), "\\!bar")
        self.failUnlessEqual(re_esc("*quux#argh?woo"), "\\*quux\\#argh\\?woo")

    def test_unicode(self):
        self.failUnlessEqual(decode(""), "")
        self.failUnlessEqual(decode("foo!"), "foo!")
        self.failUnlessEqual(decode("fo\xde"), u'fo\ufffd [Invalid Encoding]')
        self.failUnlessEqual(encode(u"abcde"), "abcde")

    def test_capitalize(self):
        self.failUnlessEqual(util.capitalize(""), "")
        self.failUnlessEqual(util.capitalize("aa b"), "Aa b")
        self.failUnlessEqual(util.capitalize("aa B"), "Aa B")
        self.failUnlessEqual(util.capitalize("!aa B"), "!aa B")

    def test_title(self):
        self.failUnlessEqual(util.title(""), "")
        self.failUnlessEqual(util.title("foobar"), "Foobar")
        self.failUnlessEqual(util.title("fooBar"), "FooBar")
        self.failUnlessEqual(util.title("foo bar"), "Foo Bar")
        self.failUnlessEqual(util.title("foo 1bar"), "Foo 1bar")
        self.failUnlessEqual(util.title("foo 1  bar"), "Foo 1  Bar")

    def test_split(self):
        self.failUnlessEqual(split_value("a b"), ["a b"])
        self.failUnlessEqual(split_value("a, b"), ["a", "b"])
        self.failUnlessEqual(split_value("a, b; c"), ["a", "b", "c"])
        self.failUnlessEqual(split_value("a b", " "), ["a", "b"])
        self.failUnlessEqual(split_value("a b", ""), ["a b"])

    def test_subtitle(self):
        # these tests shouldn't be necessary; we're really only
        # interested in split_foo.
        self.failUnlessEqual(find_subtitle("foo"), ("foo", None))
        self.failUnlessEqual(find_subtitle("foo (baz)"), ("foo", "baz"))
        self.failUnlessEqual(find_subtitle("foo (baz]"), ("foo (baz]", None))
        self.failUnlessEqual(find_subtitle("foo [baz]"), ("foo", "baz"))
        self.failUnlessEqual(find_subtitle("foo ~baz~"), ("foo", "baz"))
        self.failUnlessEqual(find_subtitle(
            u"a\u301cb\u301c".encode('utf-8')), ("a", "b"))

    def test_split_title(self):
        self.failUnlessEqual(split_title("foo ~"), ("foo ~", []))
        self.failUnlessEqual(split_title("~foo "), ("~foo ", []))
        self.failUnlessEqual(split_title("~foo ~"), ("~foo ~", []))
        self.failUnlessEqual(split_title("~foo ~bar~"), ("~foo", ["bar"]))
        self.failUnlessEqual(split_title("foo (baz)"), ("foo", ["baz"]))
        self.failUnlessEqual(split_title("foo [b, c]"), ("foo", ["b", "c"]))
        self.failUnlessEqual(split_title("foo [b c]", " "), ("foo",["b", "c"]))

    def test_split_album(self):
        self.failUnlessEqual(split_album("disk 2"), ("disk 2", None))
        self.failUnlessEqual(split_album("foo disc 1/2"), ("foo", "1/2"))
        self.failUnlessEqual(
            split_album("disc foo disc"), ("disc foo disc", None))
        self.failUnlessEqual(
            split_album("disc foo disc 1"), ("disc foo", "1"))
        
        self.failUnlessEqual(split_album("foo ~disk 3~"), ("foo", "3"))
        self.failUnlessEqual(
            split_album("foo ~crazy 3~"), ("foo ~crazy 3~", None))

    def test_split_people(self):
        self.failUnlessEqual(util.split_people("foo (bar)"), ("foo", ["bar"]))
        self.failUnlessEqual(
            util.split_people("foo (with bar)"), ("foo", ["bar"]))
        self.failUnlessEqual(
            util.split_people("foo (with with bar)"), ("foo", ["with bar"]))
        self.failUnlessEqual(
            util.split_people("foo featuring bar, qx"), ("foo", ["bar", "qx"]))

    def test_size(self):
        for k, v in {
            0: "0B", 1: "1B", 1023: "1023B",
            1024: "1.00KB", 1536: "1.50KB",
            10240: "10KB", 15360: "15KB",
            1024*1024: "1.00MB", 1024*1536: "1.50MB",
            1024*10240: "10.0MB", 1024*15360: "15.0MB"
            }.items(): self.failUnlessEqual(util.format_size(k), v)

    def test_time(self):
        self.failUnlessEqual(util.parse_time("not a time"), 0)
        # check via round-tripping
        for i in range(0, 60*60*3, 137):
            self.failUnlessEqual(util.parse_time(util.format_time(i)), i)

class TBPTests(TestCase):
    def setUp(self):
        self.f1 = '/path/Artist/Album/01 - Title.mp3'
        self.f2 = '/path/Artist - Album/01. Title.mp3'
        self.f3 = '/path/01 - Artist - Title.mp3'
        self.b1 = '/path/01 - Title'
        self.b2 = '/path/01 - Artist - Title'
        self.nomatch = {}

    def test_empty(self):
        pat = PatternFromFile('')
        self.assertEquals(pat.match(self.f1), self.nomatch)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), self.nomatch)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_tracktitle(self):
        tracktitle = {'tracknumber': '01', 'title': 'Title' }
        btracktitle = {'tracknumber': '01', 'title': 'Artist - Title' }
        pat = PatternFromFile('<tracknumber> - <title>')
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
        pat = PatternFromFile('<album>/<tracknumber> - <title>')
        self.assertEquals(pat.match(self.f1), albumtracktitle)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), balbumtracktitle)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_all(self):
        all = {'tracknumber': '01', 'title': 'Title',
               'album': 'Album', 'artist': 'Artist' }
        pat = PatternFromFile('<artist>/<album>/<tracknumber> - <title>')
        self.assertEquals(pat.match(self.f1), all)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), self.nomatch)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

    def test_post(self):
        btracktitle = {'tracknumber': '01', 'title': 'Titl' }
        vbtracktitle = {'tracknumber': '01', 'title': 'Artist - Titl' }
        pat = PatternFromFile('<tracknumber> - <title>e')
        self.assertEquals(pat.match(self.f1), btracktitle)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), vbtracktitle)
        self.assertEquals(pat.match(self.b1), btracktitle)
        self.assertEquals(pat.match(self.b2), vbtracktitle)

    def test_nofakes(self):
        pat = PatternFromFile('<~#track> - <title>')
        self.assertEquals(pat.match(self.f1), self.nomatch)
        self.assertEquals(pat.match(self.f2), self.nomatch)
        self.assertEquals(pat.match(self.f3), self.nomatch)
        self.assertEquals(pat.match(self.b1), self.nomatch)
        self.assertEquals(pat.match(self.b2), self.nomatch)

class NBPTests(TestCase):
    from formats.audio import AudioFile

    def setUp(self):
        s1 = { 'tracknumber': '5/6', 'artist':'Artist', 'title':'Title5',
               '~filename':'/path/to/a.mp3' }
        s2 = { 'tracknumber': '6', 'artist':'Artist', 'title':'Title6',
               '~filename': '/path/to/b.ogg', 'discnumber':'2' }
        s3 = { 'title': 'test/subdir', 'genre':'/\n/',
               '~filename':'/one/more/a.flac', 'version': 'Instrumental'}
        self.a = self.AudioFile(s1)
        self.b = self.AudioFile(s2)
        self.c = self.AudioFile(s3)

    def test_conditional_number_dot_title(s):
        pat = FileFromPattern('<tracknumber|<tracknumber>. ><title>')
        s.assertEquals(pat.match(s.a), '05. Title5.mp3')
        s.assertEquals(pat.match(s.b), '06. Title6.ogg')
        s.assertEquals(pat.match(s.c), 'test_subdir.flac')

    def test_conditional_other_number_dot_title(s):
        pat = FileFromPattern('<tracknumber|<tracknumber>|00>. <title>')
        s.assertEquals(pat.match(s.a), '05. Title5.mp3')
        s.assertEquals(pat.match(s.b), '06. Title6.ogg')
        s.assertEquals(pat.match(s.c), '00. test_subdir.flac')

    def test_escape_slash(s):
        fpat = FileFromPattern('<~filename>', filename=True)
        pat = FileFromPattern('<~filename>', filename=False)
        s.assertEquals(fpat.match(s.a), "_path_to_a.mp3.mp3")
        s.assertEquals(pat.match(s.a), "/path/to/a.mp3")

    def test_conditional_other_other(s):
        s.assertRaises(ValueError, FileFromPattern, '<tracknumber|a|b|c>')

    def test_wacky_recursion_attempt(s):
        pat = FileFromPattern('<tracknumber|<genre|<genre> <tracknumber>|<tracknumber>>|<artist>>')
        s.assertEquals(pat.match(s.a), '<tracknumber|05|Artist>.mp3')
        s.assertEquals(pat.match(s.b), '<tracknumber|06|Artist>.ogg')
        s.assertEquals(pat.match(s.c), '<tracknumber|_, _ |Unknown>.flac')

    def test_conditional_genre(s):
        pat = FileFromPattern('<genre|<genre>|music>')
        s.assertEquals(pat.match(s.a), 'music.mp3')
        s.assertEquals(pat.match(s.b), 'music.ogg')
        s.assertEquals(pat.match(s.c), '_, _.flac')

    def test_conditional_unknown(s):
        pat = FileFromPattern('<album|foo|bar>')
        s.assertEquals(pat.match(s.a), 'bar.mp3')

    def test_conditional_notfile(s):
        pat = FileFromPattern('<tracknumber|<tracknumber>|00>', filename=False)
        s.assertEquals(pat.match(s.a), '5/6')
        s.assertEquals(pat.match(s.b), '6')
        s.assertEquals(pat.match(s.c), '00')

    def test_conditional_subdir(s):
        pat = FileFromPattern('/a<genre|/<genre>>/<title>')
        s.assertEquals(pat.match(s.a), '/a/Title5.mp3')
        s.assertEquals(pat.match(s.b), '/a/Title6.ogg')
        s.assertEquals(pat.match(s.c), '/a/_, _/test_subdir.flac')

    def test_number_dot_title(s):
        pat = FileFromPattern('<tracknumber>. <title>')
        s.assertEquals(pat.match(s.a), '05. Title5.mp3')
        s.assertEquals(pat.match(s.b), '06. Title6.ogg')
        s.assertEquals(pat.match(s.c), '. test_subdir.flac')

    def test_recnumber_dot_title(s):
        pat = FileFromPattern('<<tracknumber>>. <title>')
        s.assertEquals(pat.match(s.a), '<05>. Title5.mp3')
        s.assertEquals(pat.match(s.b), '<06>. Title6.ogg')
        s.assertEquals(pat.match(s.c), '<>. test_subdir.flac')

    def test_generated(s):
        pat = FileFromPattern('<~basename>', filename=False)
        s.assertEquals(pat.match(s.a), os.path.basename(s.a["~filename"]))

    def test_generated_and_not_generated(s):
        pat = FileFromPattern('<~basename> <title>', filename=False)
        res = pat.match(s.a)
        s.assertEquals(
            res, os.path.basename(s.a["~filename"]) + " " + s.a["title"])

    def test_number_dot_title_dot(s):
        pat = FileFromPattern('<tracknumber>. <title>.')
        s.assertEquals(pat.match(s.a), '05. Title5..mp3')
        s.assertEquals(pat.match(s.b), '06. Title6..ogg')
        s.assertEquals(pat.match(s.c), '. test_subdir..flac')

    def test_number_dot_title_dot_hardext(s):
        pat = FileFromPattern('<tracknumber>. <title>.flac')
        s.assertEquals(pat.match(s.a), '05. Title5.flac')
        s.assertEquals(pat.match(s.b), '06. Title6.flac')
        s.assertEquals(pat.match(s.c), '. test_subdir.flac')

    def test_number_dot_genre(s):
        pat = FileFromPattern('<tracknumber>. <genre>')
        s.assertEquals(pat.match(s.a), '05. .mp3')
        s.assertEquals(pat.match(s.b), '06. .ogg')
        s.assertEquals(pat.match(s.c), '. _, _.flac')

    def test_raw_slash_preservation(s):
        pat = FileFromPattern('/a/b/<genre>')
        s.assertEquals(pat.match(s.a), '/a/b/.mp3')
        s.assertEquals(pat.match(s.b), '/a/b/.ogg')
        s.assertEquals(pat.match(s.c), '/a/b/_, _.flac')

    def test_invalid_tilde(s):
        pat = FileFromPattern('<~#track>. <genre> mu')
        s.assertEquals(pat.match(s.a), '<~#track>.  mu.mp3')
        s.assertEquals(pat.match(s.b), '<~#track>.  mu.ogg')
        s.assertEquals(pat.match(s.c), '<~#track>. _, _ mu.flac')

    def test_fake_and_joiner_tilde(s):
        pat = FileFromPattern('<~a><discnumber~tracknumber>. <title~version>')
        s.assertEquals(pat.match(s.a), '<~a>05. Title5.mp3')
        s.assertEquals(pat.match(s.b), '<~a>2 - 06. Title6.ogg')
        s.assertEquals(pat.match(s.c), '<~a>. test_subdir - Instrumental.flac')

    def test_directory_rooting(s):
        s.assertRaises(ValueError, FileFromPattern, '<a>/<b>')
        FileFromPattern('/<a>/<b>')

class FormatTimeTests(TestCase):
    def test_second(s):
        s.assertEquals(f_t_l(1).split(", ")[0], _("1 second"))
    def test_seconds(s):
        s.assertEquals(f_t_l(2).split(", ")[0], _("%d seconds")%2)
    def test_notminutes(s):
        s.assertEquals(f_t_l(59).split(", ")[0], _("%d seconds")%59)
    def test_minute(s):
        s.assertEquals(f_t_l(60), _("1 minute"))
    def test_minutes(s):
        s.assertEquals(f_t_l(120).split(", ")[0], _("%d minutes")%2)
    def test_nothours(s):
        s.assertEquals(f_t_l(3599).split(", ")[0], _("%d minutes")%59)
    def test_hour(s):
        s.assertEquals(f_t_l(3600), _("1 hour"))
    def test_hours(s):
        s.assertEquals(f_t_l(7200), _("%d hours")%2)
    def test_notdays(s):
        s.assertEquals(f_t_l(86399).split(", ")[0], _("%d hours")%23)
    def test_seconds_dropped(s):
        s.assertEquals(len(f_t_l(3601).split(", ")), 2)
    def test_day(s):
        s.assertEquals(f_t_l(86400), _("1 day"))
    def test_days(s):
        s.assertEquals(f_t_l(172800).split(", ")[0], _("%d days")%2)
    def test_notyears(s):
        s.assertEquals(f_t_l(31535999).split(", ")[0], _("%d days")%364)
    def test_year(s):
        s.assertEquals(f_t_l(31536000), _("1 year"))
    def test_years(s):
        s.assertEquals(f_t_l(63072000).split(", ")[0], _("%d years")%2)
    def test_drop_zero(s):
        s.assertEquals(f_t_l(3601), ", ".join([_("1 hour"), _("1 second")]))

registerCase(FSTests)
registerCase(StringTests)
registerCase(TBPTests)
registerCase(NBPTests)
registerCase(FormatTimeTests)
