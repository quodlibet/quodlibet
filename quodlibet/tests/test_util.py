from tests import TestCase, add

import sys
import os
import re

from quodlibet import util
from quodlibet.util import format_time_long as f_t_l

class Tmkdir(TestCase):
    def test_exists(self):
        util.mkdir(".")

    def test_notdirectory(self):
        self.failUnlessRaises(OSError, util.mkdir, __file__)

    def test_manydeep(self):
        self.failUnless(not os.path.isdir("nonext"))
        util.mkdir("nonext/test/test2/test3")
        try:
            self.failUnless(os.path.isdir("nonext/test/test2/test3"))
        finally:
            os.rmdir("nonext/test/test2/test3")
            os.rmdir("nonext/test/test2")
            os.rmdir("nonext/test")
            os.rmdir("nonext")
add(Tmkdir)

class Tiscommand(TestCase):
    def test_ispartial(self): self.failUnless(util.iscommand("ls"))
    def test_isfull(self): self.failUnless(util.iscommand("/bin/ls"))
    def test_notpartial(self): self.failIf(util.iscommand("zzzzzzzzz"))
    def test_notfull(self): self.failIf(util.iscommand("/bin/zzzzzzzzz"))
    def test_empty(self): self.failIf(util.iscommand(""))
    def test_symlink(self): self.failUnless(util.iscommand("pidof"))
    def test_dir(self): self.failIf(util.iscommand("/bin"))
    def test_dir_in_path(self): self.failIf(util.iscommand("X11"))
add(Tiscommand)

class Tmtime(TestCase):
    def test_equal(self):
        self.failUnlessEqual(util.mtime("."), os.path.getmtime("."))
    def test_bad(self):
        self.failIf(os.path.exists("/dev/doesnotexist"))
        self.failUnlessEqual(util.mtime("/dev/doesnotexist"), 0)
add(Tmtime)

class Tunexpand(TestCase):
    d = os.path.expanduser("~")

    def test_base(self):
        self.failUnlessEqual(util.unexpand(self.d), "~")
    def test_base_trailing(self):
        self.failUnlessEqual(util.unexpand(self.d + "/"), "~/")
    def test_noprefix(self):
        self.failUnlessEqual(
            util.unexpand(self.d + "foobar/"), self.d + "foobar/")
    def test_subfile(self):
        self.failUnlessEqual(
            util.unexpand(os.path.join(self.d, "la/la")), "~/la/la")
add(Tunexpand)

class Tformat_rating(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.format_rating(0), "")

    def test_full(self):
        self.failUnlessEqual(
            len(util.format_rating(1)), int(1/util.RATING_PRECISION))
    def test_rating(self):
        for i in range(0, int(1/util.RATING_PRECISION+1)):
            self.failUnlessEqual(
                i, len(util.format_rating(i * util.RATING_PRECISION)))

    def test_bogus(self):
        max_length = int(1 / util.RATING_PRECISION)
        self.failUnlessEqual(len(util.format_rating(2**32-1)), max_length)

        self.failUnlessEqual(len(util.format_rating(-4.2)), 0)

add(Tformat_rating)

class Tescape(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.escape(""), "")

    def test_roundtrip(self):
        for s in ["foo&amp;", "<&>", "&", "&amp;", "<&testing&amp;>amp;"]:
            esc = util.escape(s)
            self.failIfEqual(s, esc)
            self.failUnlessEqual(s, util.unescape(esc))
add(Tescape)

class Tunescape(Tescape):
    def test_empty(self):
        self.failUnlessEqual(util.unescape(""), "")
add(Tunescape)

class Tre_esc(TestCase):
    def test_empty(self):
        self.failUnlessEqual(re.escape(""), "")

    def test_safe(self):
        self.failUnlessEqual(re.escape("fo o"), "fo o")

    def test_unsafe(self):
        self.failUnlessEqual(re.escape("!bar"), r"\!bar")

    def test_many_unsafe(self):
        self.failUnlessEqual(
            re.escape("*quux#argh?woo"), r"\*quux\#argh\?woo")
add(Tre_esc)

class Tsplit_scan_dirs(TestCase):
    def test_basic(self):
        if sys.platform == "win32":
            res = util.split_scan_dirs(r":Z:\foo:C:/windows:")
            self.assertEquals(res, [r"Z:\foo", "C:/windows"])
        else:
            res = util.split_scan_dirs(":/home/user/Music:/opt/party:")
            self.assertEquals(res, ["/home/user/Music", "/opt/party"])
add(Tsplit_scan_dirs)

class Tdecode(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.decode(""), "")
    def test_safe(self):
        self.failUnlessEqual(util.decode("foo!"), "foo!")
    def test_invalid(self):
        self.failUnlessEqual(
            util.decode("fo\xde"), u'fo\ufffd [Invalid Encoding]')
add(Tdecode)

class Tencode(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.encode(""), "")
    def test_unicode(self):
        self.failUnlessEqual(util.encode(u"abcde"), "abcde")
add(Tencode)

class Tcapitalize(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.capitalize(""), "")

    def test_firstword(self):
        self.failUnlessEqual(util.capitalize("aa b"), "Aa b")

    def test_preserve(self):
        self.failUnlessEqual(util.capitalize("aa B"), "Aa B")

    def test_nonalphabet(self):
        self.failUnlessEqual(util.capitalize("!aa B"), "!aa B")
add(Tcapitalize)

class Tsplit_value(TestCase):
    def test_single(self):
        self.failUnlessEqual(util.split_value("a b"), ["a b"])

    def test_double(self):
        self.failUnlessEqual(util.split_value("a, b"), ["a", "b"])

    def test_custom_splitter(self):
        self.failUnlessEqual(util.split_value("a b", [" "]), ["a", "b"])

    def test_two_splitters(self):
        self.failUnlessEqual(
            util.split_value("a, b and c", [",", "and"]), ["a", "b and c"])

    def test_no_splitters(self):
        self.failUnlessEqual(util.split_value("a b", []), ["a b"])

    def test_wordboundry(self):
        self.failUnlessEqual(
            util.split_value("Andromeda and the Band", ["and"]),
            ["Andromeda", "the Band"])

    def test_unicode_wordboundry(self):
        val = '\xe3\x81\x82&\xe3\x81\x84'.decode('utf-8')
        self.failUnlessEqual(util.split_value(val), val.split("&"))
add(Tsplit_value)

class Thuman_sort(TestCase):
    def smaller(self, x, y):
        return util.human_sort_key(x) < util.human_sort_key(y)

    def test_human(self):
        self.failUnlessEqual(self.smaller(u"2", u"15"), True)
        self.failUnlessEqual(self.smaller(u" 2", u"15 "), True)
        self.failUnlessEqual(self.smaller(u"a2 g", u"a 2z"), True)
        self.failUnlessEqual(self.smaller(u"a2zz", u"a2.1z"), True)

        self.failUnlessEqual(self.smaller(u"42o", u"42\xf6"), True)
        self.failUnlessEqual(self.smaller(u"42\xf6", u"42p"), True)

        self.failUnlessEqual(self.smaller(u"bbb", u"zzz3"), True)

    def test_false(self):
        # album browser needs that to sort albums without artist/title
        # to the bottom
        self.failIf(util.human_sort_key(""))

    def test_white(self):
        self.failUnlessEqual(
            util.human_sort_key(u"  3foo    bar6 42.8"),
            util.human_sort_key(u"3 foo bar6  42.8  "))
        self.failUnlessEqual(64.0 in util.human_sort_key(u"64. 8"), True)


add(Thuman_sort)

class Tformat_time(TestCase):
    def test_seconds(self):
        self.failUnlessEqual(util.format_time(0), "0:00")
        self.failUnlessEqual(util.format_time(59), "0:59")

    def test_minutes(self):
        self.failUnlessEqual(util.format_time(60), "1:00")
        self.failUnlessEqual(util.format_time(60*59+59), "59:59")

    def test_hourss(self):
        self.failUnlessEqual(util.format_time(60*60), "1:00:00")
        self.failUnlessEqual(util.format_time(60*60+60*59+59), "1:59:59")

    def test_negative(self):
        self.failUnlessEqual(util.format_time(-124), "-2:04")
add(Tformat_time)

class Tparse_time(TestCase):
    def test_invalid(self):
        self.failUnlessEqual(util.parse_time("not a time"), 0)

    def test_except(self):
        self.failUnlessRaises(ValueError, util.parse_time, "not a time", None)

    def test_empty(self):
        self.failUnlessEqual(util.parse_time(""), 0)

    def test_roundtrip(self):
        # The values are the ones tested for Tformat_time, so we know they
        # will be formatted correctly. They're also representative of
        # all the major patterns.
        for i in [0, 59, 60, 60*59+59, 60*60, 60*60+60*59+59]:
            self.failUnlessEqual(util.parse_time(util.format_time(i)), i)

    def test_negative(self):
        self.failUnlessEqual(util.parse_time("-2:04"), -124)
add(Tparse_time)

class Tformat_size(TestCase):
    def t_dict(self, d):
        map(self.failUnlessEqual, map(util.format_size, d.keys()), d.values())

    def test_bytes(self):
        self.t_dict({ 0: "0 B", 1: "1 B", 1023: "1023 B" })

    def test_kbytes(self):
        self.t_dict({ 1024: "1.00 KB", 1536: "1.50 KB",
                      10240: "10 KB", 15360: "15 KB" })

    def test_mbytes(self):
        self.t_dict({ 1024*1024: "1.00 MB", 1024*1536: "1.50 MB",
                      1024*10240: "10.0 MB", 1024*15360: "15.0 MB",
                      123456*1024: "121 MB", 765432*1024: "747 MB"})

    def test_gbytes(self):
        self.t_dict({ 1024*1024*1024: "1.0 GB", 1024*1024*1536: "1.5 GB",
                      1024*1024*10240: "10.0 GB", 1024*1024*15360: "15.0 GB"})
add(Tformat_size)

class Tsplit_title(TestCase):
    def test_trailing(self):
        self.failUnlessEqual(util.split_title("foo ~"), ("foo ~", []))
    def test_prefixed(self):
        self.failUnlessEqual(util.split_title("~foo "), ("~foo ", []))
    def test_prefix_and_trailing(self):
        self.failUnlessEqual(util.split_title("~foo ~"), ("~foo ~", []))
    def test_prefix_and_version(self):
        self.failUnlessEqual(util.split_title("~foo ~bar~"), ("~foo", ["bar"]))
    def test_simple(self):
        self.failUnlessEqual(util.split_title("foo (baz)"), ("foo", ["baz"]))
    def test_two_versions(self):
        self.failUnlessEqual(
            util.split_title("foo [b, c]"), ("foo", ["b", "c"]))
    def test_custom_splitter(self):
        self.failUnlessEqual(
            util.split_title("foo [b c]", " "), ("foo", ["b", "c"]))
add(Tsplit_title)

class Tsplit_album(TestCase):
    def test_album_looks_like_disc(self):
        self.failUnlessEqual(
            util.split_album("disk 2"), ("disk 2", None))

    def test_basic_disc(self):
        self.failUnlessEqual(
            util.split_album("foo disc 1/2"), ("foo", "1/2"))

    def test_looks_like_disc_but_isnt(self):
        self.failUnlessEqual(
            util.split_album("disc foo disc"), ("disc foo disc", None))

    def test_disc_album_and_disc(self):
        self.failUnlessEqual(
            util.split_album("disc foo disc 1"), ("disc foo", "1"))

    def test_weird_disc(self):
        self.failUnlessEqual(
            util.split_album("foo ~disk 3~"), ("foo", "3"))

    def test_weird_not_disc(self):
        self.failUnlessEqual(
            util.split_album("foo ~crazy 3~"), ("foo ~crazy 3~", None))
add(Tsplit_album)

class Tsplit_people(TestCase):
    def test_parened_person(self):
        self.failUnlessEqual(util.split_people("foo (bar)"), ("foo", ["bar"]))
    def test_with_person(self):
        self.failUnlessEqual(
            util.split_people("foo (With bar)"), ("foo", ["bar"]))
    def test_with_with_person(self):
        self.failUnlessEqual(
            util.split_people("foo (with with bar)"), ("foo", ["with bar"]))
    def test_featuring_two_people(self):
        self.failUnlessEqual(
            util.split_people("foo featuring bar, qx"), ("foo", ["bar", "qx"]))
    def test_featuring_person_bracketed(self):
        self.failUnlessEqual(
            util.split_people("foo (Ft. bar)"), ("foo", ["bar"]))
        self.failUnlessEqual(
            util.split_people("foo(feat barman)"), ("foo", ["barman"]))
    def test_originally_by(self):
        self.failUnlessEqual(
            util.split_people("title (originally by artist)"),
            ("title", ["artist"]))
        self.failUnlessEqual(
            util.split_people("title [originally by artist & artist2]"),
            ("title", ["artist", "artist2"]))
    def test_cover(self):
        self.failUnlessEqual(
            util.split_people("Pyscho Killer [Talking Heads Cover]"),
            ("Pyscho Killer", ["Talking Heads"]))



add(Tsplit_people)

class Ttag(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.tag(""), "Invalid tag")

    def test_basic(self):
        self.failUnlessEqual(util.tag("title"), "Title")

    def test_basic_nocap(self):
        self.failUnlessEqual(util.tag("title", False), "title")

    def test_internal(self):
        self.failUnlessEqual(util.tag("~year"), "Year")

    def test_numeric(self):
        self.failUnlessEqual(util.tag("~#year"), "Year")

    def test_two(self):
        self.failUnlessEqual(util.tag("title~version"), "Title / Version")

    def test_two_nocap(self):
        self.failUnlessEqual(
            util.tag("title~version", False), "title / version")

    def test_precap_handling(self):
        self.failUnlessEqual(util.tag("labelid"), "Label ID")
        self.failUnlessEqual(util.tag("labelid", False), "label ID")
add(Ttag)

class Ttagsplit(TestCase):
    def test_single_tag(self):
        self.failUnlessEqual(util.tagsplit("foo"), ["foo"])
    def test_synth_tag(self):
        self.failUnlessEqual(util.tagsplit("~foo"), ["~foo"])
    def test_two_tags(self):
        self.failUnlessEqual(util.tagsplit("foo~bar"), ["foo", "bar"])
    def test_two_prefix(self):
        self.failUnlessEqual(util.tagsplit("~foo~bar"), ["foo", "bar"])
    def test_synth(self):
        self.failUnlessEqual(util.tagsplit("~foo~~bar"), ["foo", "~bar"])
    def test_numeric(self):
        self.failUnlessEqual(util.tagsplit("~#bar"), ["~#bar"])
    def test_two_numeric(self):
        self.failUnlessEqual(util.tagsplit("~#foo~~#bar"), ["~#foo", "~#bar"])
    def test_two_synth_start(self):
        self.failUnlessEqual(
            util.tagsplit("~~people~album"), ["~people", "album"])
add(Ttagsplit)

class Tpattern(TestCase):
    def test_empty(self):
        self.failUnlessEqual(util.pattern(""), "")
    def test_basic(self):
        self.failUnlessEqual(util.pattern("<title>"), "Title")
    def test_basic_nocap(self):
        self.failUnlessEqual(util.pattern("<title>", False), "title")
    def test_internal(self):
        self.failUnlessEqual(util.pattern("<~plays>"), "Plays")
    def test_tied(self):
        self.failUnlessEqual(util.pattern("<~title~album>"), "Title - Album")
    def test_unknown(self):
        self.failUnlessEqual(util.pattern("<foobarbaz>"), "Foobarbaz")
    def test_condition(self):
        self.failUnlessEqual(util.pattern("<~year|<~year> - <album>|<album>>"),
                             "Year - Album")
    def test_escape(self):
        self.failUnlessEqual(util.pattern("\<i\><&>\</i\>", esc=True),
                            "<i>&amp;</i>")
    def test_invalid(self):
        self.failUnlessEqual(util.pattern("<date"), "")
        util.pattern("<d\\")

add(Tpattern)

class Tformat_time_long(TestCase):
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
add(Tformat_time_long)

class Tspawn(TestCase):
    def test_simple(self):
        self.failUnless(util.spawn(["ls", "."], stdout=True))

    def test_invalid(self):
        import gobject
        self.failUnlessRaises(gobject.GError, util.spawn, ["not a command"])

    def test_types(self):
        self.failUnlessRaises(TypeError, util.spawn, [u"ls"])

    def test_get_output(self):
        fileobj = util.spawn(["echo", "'$1'", '"$2"', ">3"], stdout=True)
        self.failUnlessEqual(fileobj.read().split(), ["'$1'", '"$2"', ">3"])
add(Tspawn)

class Txdg_dirs(TestCase):
    def test_system_data_dirs(self):
        os.environ["XDG_DATA_DIRS"] = "/xyz"
        self.failUnlessEqual(util.xdg_get_system_data_dirs()[0], "/xyz")
        del os.environ["XDG_DATA_DIRS"]
        dirs = util.xdg_get_system_data_dirs()
        self.failUnlessEqual(dirs[0], "/usr/local/share/")
        self.failUnlessEqual(dirs[1], "/usr/share/")

    def test_data_home(self):
        os.environ["XDG_DATA_HOME"] = "/xyz"
        self.failUnlessEqual(util.xdg_get_data_home(), "/xyz")
        del os.environ["XDG_DATA_HOME"]
        should = os.path.join(os.path.expanduser("~"), ".local", "share")
        self.failUnlessEqual(util.xdg_get_data_home(), should)
add(Txdg_dirs)

class Tpathname2url(TestCase):
    def test_win(self):
        cases = {
            r"c:\abc\def" : "/c:/abc/def",
            r"C:\a b\c.txt": "/C:/a%20b/c.txt",
            r"\\xy\z.txt": "xy/z.txt",
            r"C:\a:b\c:d": "/C:/a%3Ab/c%3Ad"
            }
        p2u = util.pathname2url_win32
        for inp, should in cases.iteritems():
            self.failUnlessEqual(p2u(inp), should)
add(Tpathname2url)
