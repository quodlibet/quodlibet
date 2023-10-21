# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


import os

from quodlibet.formats import AudioFile
from quodlibet.pattern import (FileFromPattern, XMLFromPattern, Pattern,
                               XMLFromMarkupPattern, ArbitraryExtensionFileFromPattern)
from senf import fsnative
from tests import TestCase


class _TPattern(TestCase):

    def setUp(self):
        s1 = {"tracknumber": u"5/6", "artist": u"Artist", "title": u"Title5",
              "~filename": "/path/to/a.mp3", "xmltest": u"<&>"}
        s2 = {"tracknumber": u"6", "artist": u"Artist", "title": u"Title6",
              "~filename": "/path/to/b.ogg", "discnumber": u"2",
              "unislash": u"foo\uff0fbar"}
        s3 = {"title": u"test/subdir", "genre": u"/\n/",
              "~filename": "/one/more/a.flac", "version": u"Instrumental"}
        s4 = {"performer": u"a\nb", "artist": u"foo\nbar"}
        s5 = {"tracknumber": u"7/1234", "artist": u"Artist",
              "title": u"Title7", "~filename": "/path/to/e.mp3"}
        s6 = {"artist": u"Foo", "albumartist": u"foo.bar", "album": u"Best Of",
              "~filename": "/path/to/f.mp3", "title": u"The.Final.Word"}
        s7 = {"artist": u"un élève français", "~filename": "/path/to/g.mp3",
              "albumartist": u'Lee "Scratch" Perry',
              "album": u"The 'only' way!", "comment": u"Trouble|Strife"}
        s8 = {"tracknumber": u"7/8", "artist": u"Artist1\n\nArtist3",
              "artistsort": u"SortA1\nSortA2",
              "album": u"Album5", "albumsort": u"SortAlbum5",
              "~filename": "/path/to/g.mp3", "xmltest": u"<&>"}

        if os.name == "nt":
            s1["~filename"] = u"C:\\path\\to\\a.mp3"
            s2["~filename"] = u"C:\\path\\to\\b.ogg"
            s3["~filename"] = u"C:\\one\\more\\a.flac"
            s4["~filename"] = u"C:\\path\\to\\a.mp3"
            s5["~filename"] = u"C:\\path\\to\\a.mp3"
            s6["~filename"] = u"C:\\path\\to\\f.mp3"
            s7["~filename"] = u"C:\\path\\to\\g.mp3"
            s8["~filename"] = u"C:\\path\\to\\h.mp3"

        self.a = AudioFile(s1)
        self.b = AudioFile(s2)
        self.c = AudioFile(s3)
        self.d = AudioFile(s4)
        self.e = AudioFile(s5)
        self.f = AudioFile(s6)
        self.g = AudioFile(s7)
        self.h = AudioFile(s8)


class TPattern(_TPattern):
    from quodlibet.formats import AudioFile
    AudioFile  # noqa

    def test_numeric(self):
        pat = Pattern("<~#rating>")
        self.assertEqual(pat.format(self.a), "0.50")

    def test_space(self):
        pat = Pattern("a ")
        self.assertEqual(pat.format(self.a), "a ")
        pat = Pattern(" a")
        self.assertEqual(pat.format(self.a), " a")
        pat = Pattern("a\n\n")
        self.assertEqual(pat.format(self.a), "a\n\n")

    def test_escape(self):
        pat = Pattern("a \\<foo\\|bla\\>")
        self.assertEqual(pat.format(self.a), "a <foo|bla>")

        pat = Pattern(r"a\\<foo>")
        self.assertEqual(pat.format(self.a), "a\\")

    def test_query_like_tag(self):
        pat = Pattern("<t=v>")
        self.assertEqual(pat.format(AudioFile({"t=v": "foo"})), "foo")

    def test_conditional_number_dot_title(self):
        pat = Pattern("<tracknumber|<tracknumber>. ><title>")
        self.assertEquals(pat.format(self.a), "5/6. Title5")
        self.assertEquals(pat.format(self.b), "6. Title6")
        self.assertEquals(pat.format(self.c), "test/subdir")

    def test_conditional_other_number_dot_title(self):
        pat = Pattern("<tracknumber|<tracknumber>|00>. <title>")
        self.assertEquals(pat.format(self.a), "5/6. Title5")
        self.assertEquals(pat.format(self.b), "6. Title6")
        self.assertEquals(pat.format(self.c), "00. test/subdir")

    def test_conditional_other_other(self):
        # FIXME: was <tracknumber|a|b|c>.. but we can't put <>| in the format
        # string since it would break the XML pattern formatter.
        self.assertEqual(Pattern("<tracknumber|a|b|c>").format(self.a), "")

    def test_conditional_genre(self):
        pat = Pattern("<genre|<genre>|music>")
        self.assertEquals(pat.format(self.a), "music")
        self.assertEquals(pat.format(self.b), "music")
        self.assertEquals(pat.format(self.c), "/, /")

    def test_conditional_unknown(self):
        pat = Pattern("<album|foo|bar>")
        self.assertEquals(pat.format(self.a), "bar")

    def test_conditional_equals(self):
        pat = Pattern("<artist=Artist|matched|not matched>")
        self.assertEquals(pat.format(self.a), "matched")
        pat = Pattern("<artist=Artistic|matched|not matched>")
        self.assertEquals(pat.format(self.a), "not matched")

    def test_conditional_equals_unicode(self):
        pat = Pattern(u"<artist=Artist|matched|not matched>")
        self.assertEquals(pat.format(self.g), "not matched")
        pat = Pattern(u"<artist=un élève français|matched|not matched>")
        self.assertEquals(pat.format(self.g), "matched")

    def test_disjunction(self):
        pat = Pattern("<<composer>||<albumartist>>")
        self.assertEquals(pat.format(self.a), "")
        pat = Pattern("<<composer>||<artist>>")
        self.assertEquals(pat.format(self.a), "Artist")
        pat = Pattern("<<artist>||<albumartist>>")
        self.assertEquals(pat.format(self.a), "Artist")

    def test_disjunction_chain(self):
        pat = Pattern("<<composer>||<albumartist>||<artist>>")
        self.assertEquals(pat.format(self.a), "Artist")
        pat = Pattern("<<composer>||<albumartist>||no tag>")
        self.assertEquals(pat.format(self.a), "no tag")

    def test_disjunction_conjunction_nested(self):
        pat = Pattern("<<album|<albumartist>>||<artist>>")
        self.assertEquals(pat.format(self.a), "Artist")
        self.assertEquals(pat.format(self.f), "foo.bar")
        pat = Pattern("<<album|<composer>>||<artist>>")
        self.assertEquals(pat.format(self.f), "Foo")
        pat = Pattern("<<album|<albumartist>|text>||<artist>>")
        self.assertEquals(pat.format(self.a), "text")
        pat = Pattern("<<album>||<artist=x|<artist>|<title>>>")
        self.assertEquals(pat.format(self.a), "Title5")

    def test_duplicate_query(self):
        pat = Pattern("<u=yes|<u=yes|x|y>|<u=yes|q|z>>")
        self.assertEqual(pat.format(AudioFile({"u": u"yes"})), "x")
        self.assertEqual(pat.format(AudioFile({"u": u"no"})), "z")

    def test_tag_query_escaping(self):
        pat = Pattern('<albumartist=Lee "Scratch" Perry|matched|not matched>')
        self.assertEquals(pat.format(self.g), "matched")

    def test_tag_query_escaped_pipe(self):
        pat = Pattern(r"<albumartist=/Lee\|Bob/|matched|not matched>")
        self.assertEquals(pat.format(self.g), "matched")
        pat = Pattern(r"<albumartist=\||matched|not matched>")
        self.assertEquals(pat.format(self.g), "not matched")
        pat = Pattern(r"<comment=/Trouble\|Strife/|matched|not matched>")
        self.assertEquals(pat.format(self.g), "matched")

    def test_tag_query_quoting(self):
        pat = Pattern("<album=The only way|matched|not matched>")
        self.assertEquals(pat.format(self.g), "not matched")
        pat = Pattern("<album=\"The 'only' way!\"|matched|not matched>")
        self.assertEquals(pat.format(self.g), "matched")

    def test_tag_query_regex(self):
        pat = Pattern("<album=/'only'/|matched|not matched>")
        self.assertEquals(pat.format(self.g), "matched")
        pat = Pattern("<album=/The .+ way/|matched|not matched>")
        self.assertEquals(pat.format(self.g), "matched")
        pat = Pattern("</The .+ way/|matched|not matched>")
        self.assertEquals(pat.format(self.g), "not matched")

    def test_tag_internal(self):
        if os.name != "nt":
            pat = Pattern("<~filename='/path/to/a.mp3'|matched|not matched>")
            self.assertEquals(pat.format(self.a), "matched")
            pat = Pattern(
                "<~filename=/\\/path\\/to\\/a.mp3/|matched|not matched>")
            self.assertEquals(pat.format(self.a), "matched")
        else:
            pat = Pattern(
                r"<~filename='C:\\\path\\\to\\\a.mp3'|matched|not matched>")
            self.assertEquals(pat.format(self.a), "matched")

    def test_tag_query_disallowed_free_text(self):
        pat = Pattern("<The only way|matched|not matched>")
        self.assertEquals(pat.format(self.g), "not matched")

    def test_query_scope(self):
        pat = Pattern("<foo|<artist=Foo|x|y>|<artist=Foo|z|q>>")
        self.assertEqual(pat.format(self.f), "z")

    def test_query_numeric(self):
        pat = Pattern("<#(foo=42)|42|other>")
        self.assertEqual(pat.format(AudioFile()), "other")
        self.assertEqual(pat.format(AudioFile({"foo": "42"})), "42")

    def test_conditional_notfile(self):
        pat = Pattern("<tracknumber|<tracknumber>|00>")
        self.assertEquals(pat.format(self.a), "5/6")
        self.assertEquals(pat.format(self.b), "6")
        self.assertEquals(pat.format(self.c), "00")

    def test_conditional_subdir(self):
        pat = Pattern("/a<genre|/<genre>>/<title>")
        self.assertEquals(pat.format(self.a), "/a/Title5")
        self.assertEquals(pat.format(self.b), "/a/Title6")
        self.assertEquals(pat.format(self.c), "/a//, //test/subdir")

    def test_number_dot_title(self):
        pat = Pattern("<tracknumber>. <title>")
        self.assertEquals(pat.format(self.a), "5/6. Title5")
        self.assertEquals(pat.format(self.b), "6. Title6")
        self.assertEquals(pat.format(self.c), ". test/subdir")

    def test_recnumber_dot_title(self):
        pat = Pattern(r"\<<tracknumber>\>. <title>")
        self.assertEquals(pat.format(self.a), "<5/6>. Title5")
        self.assertEquals(pat.format(self.b), "<6>. Title6")
        self.assertEquals(pat.format(self.c), "<>. test/subdir")

    def test_generated(self):
        pat = Pattern("<~basename>")
        self.assertEquals(pat.format(self.a), os.path.basename(self.a["~filename"]))

    def test_generated_and_not_generated(self):
        pat = Pattern("<~basename> <title>")
        res = pat.format(self.a)
        self.assertEquals(
            res, os.path.basename(self.a["~filename"]) + " " + self.a["title"])

    def test_number_dot_title_dot(self):
        pat = Pattern("<tracknumber>. <title>.")
        self.assertEquals(pat.format(self.a), "5/6. Title5.")
        self.assertEquals(pat.format(self.b), "6. Title6.")
        self.assertEquals(pat.format(self.c), ". test/subdir.")

    def test_number_dot_genre(self):
        pat = Pattern("<tracknumber>. <genre>")
        self.assertEquals(pat.format(self.a), "5/6. ")
        self.assertEquals(pat.format(self.b), "6. ")
        self.assertEquals(pat.format(self.c), ". /, /")

    def test_unicode_with_int(self):
        song = AudioFile({"tracknumber": "5/6",
                          "title": b"\xe3\x81\x99\xe3\x81\xbf\xe3\x82\x8c".decode(
                              "utf-8")})
        pat = Pattern("<~#track>. <title>")
        self.assertEquals(pat.format(song),
                          b"5. \xe3\x81\x99\xe3\x81\xbf\xe3\x82\x8c".decode("utf-8"))

    def test_json(self):
        pat = Pattern("<~json>")
        if os.name != "nt":
            self.assertEquals(pat.format(self.a),
                              '{"artist": "Artist", "title": "Title5", "tracknumber": '
                              '"5/6",'
                              ' "xmltest": "<&>", "~filename": "/path/to/a.mp3"}')
        else:
            self.assertEquals(pat.format(self.a),
                              '{"artist": "Artist", "title": "Title5", "tracknumber": '
                              '"5/6",'
                              ' "xmltest": "<&>", "~filename": '
                              '"C:\\\\path\\\\to\\\\a.mp3"}')


class _TFileFromPattern(_TPattern):
    def _create(self, string):
        return FileFromPattern(string)

    def test_escape_slash(self):
        fpat = self._create("<~filename>")
        self.assertTrue(fpat.format(self.a).endswith("_path_to_a.mp3"))

        pat = Pattern("<~filename>")
        if os.name != "nt":
            self.assertTrue(pat.format(self.a).startswith("/path/to/a"))
        else:
            self.assertTrue(pat.format(self.a).startswith("C:\\path\\to\\a"))

        if os.name != "nt":
            wpat = self._create(r'\\<artist>\\ "<title>')
            self.assertTrue(
                wpat.format(self.a).startswith(r'\Artist\ "Title5'))
        else:
            # FIXME..
            pass

    def test_directory_rooting(self):
        if os.name == "nt":
            self.assertRaises(ValueError, FileFromPattern, "a\\<b>")
            self.assertRaises(ValueError, FileFromPattern, "<a>\\<b>")
            self._create("C:\\<a>\\<b>")

        else:
            self.assertRaises(ValueError, FileFromPattern, "a/<b>")
            self.assertRaises(ValueError, FileFromPattern, "<a>/<b>")
            self._create("/<a>/<b>")

    def test_backslash_conversion_win32(self):
        if os.name == "nt":
            pat = self._create(r"Z:\<artist>\<title>")
            self.assertTrue(pat.format(self.a).startswith(r"Z:\Artist\Title5"))

    def test_raw_slash_preservation(self):
        if os.name == "nt":
            pat = self._create("C:\\a\\b\\<genre>")
            self.assertTrue(pat.format(self.a).startswith("C:\\a\\b\\"))
            self.assertTrue(pat.format(self.b).startswith("C:\\a\\b\\"))
            self.assertTrue(pat.format(self.c).startswith("C:\\a\\b\\_, _"))

        else:
            pat = self._create("/a/b/<genre>")
            self.assertTrue(pat.format(self.a).startswith("/a/b/"))
            self.assertTrue(pat.format(self.b).startswith("/a/b/"))
            self.assertTrue(pat.format(self.c).startswith("/a/b/_, _"))

    def test_specialcase_anti_ext(self):
        p1 = self._create("<~filename>")
        p2 = self._create("<~dirname>_<~basename>")
        self.assertEquals(p1.format(self.a), p2.format(self.a))
        self.assertTrue(p1.format(self.a).endswith("_path_to_a.mp3"))
        self.assertEquals(p1.format(self.b), p2.format(self.b))
        self.assertTrue(p1.format(self.b).endswith("_path_to_b.ogg"))
        self.assertEquals(p1.format(self.c), p2.format(self.c))
        self.assertTrue(p1.format(self.c).endswith("_one_more_a.flac"))

    def test_long_filename(self):
        if os.name == "nt":
            a = AudioFile({"title": "x" * 300, "~filename": u"C:\\f.mp3"})
            path = self._create(u"C:\\foobar\\ä<title>\\<title>").format(a)
            assert isinstance(path, fsnative)
            self.failUnlessEqual(len(path), 3 + 6 + 1 + 255 + 1 + 255)
            path = self._create(u"äüö<title><title>").format(a)
            assert isinstance(path, fsnative)
            self.failUnlessEqual(len(path), 255)
        else:
            a = AudioFile({"title": "x" * 300, "~filename": "/f.mp3"})
            path = self._create(u"/foobar/ä<title>/<title>").format(a)
            assert isinstance(path, fsnative)
            self.failUnlessEqual(len(path), 1 + 6 + 1 + 255 + 1 + 255)
            path = self._create(u"äüö<title><title>").format(a)
            assert isinstance(path, fsnative)
            self.failUnlessEqual(len(path), 255)


class TFileFromPattern(_TFileFromPattern):
    def _create(self, string):
        return FileFromPattern(string)

    def test_type(self):
        pat = self._create("")
        self.assertTrue(isinstance(pat.format(self.a), fsnative))
        pat = self._create("<title>")
        self.assertTrue(isinstance(pat.format(self.a), fsnative))

    def test_number_dot_title_dot(self):
        pat = self._create("<tracknumber>. <title>.")
        self.assertEquals(pat.format(self.a), "05. Title5..mp3")
        self.assertEquals(pat.format(self.b), "06. Title6..ogg")
        self.assertEquals(pat.format(self.c), ". test_subdir..flac")

    def test_tracknumber_decimals(self):
        pat = self._create("<tracknumber>. <title>")
        self.assertEquals(pat.format(self.a), "05. Title5.mp3")
        self.assertEquals(pat.format(self.e), "0007. Title7.mp3")

    def test_ext_case_preservation(self):
        x = AudioFile({"~filename": fsnative(u"/tmp/Xx.Flac"), "title": "Xx"})
        # If pattern has a particular ext, preserve case of ext
        p1 = self._create("<~basename>")
        self.assertEquals(p1.format(x), "Xx.Flac")
        p2 = self._create("<title>.FLAC")
        self.assertEquals(p2.format(x), "Xx.FLAC")
        # If pattern doesn't have a particular ext, lowercase ext
        p3 = self._create("<title>")
        self.assertEquals(p3.format(x), "Xx.flac")


class TArbitraryExtensionFileFromPattern(_TFileFromPattern):
    def _create(self, string):
        return ArbitraryExtensionFileFromPattern(string)

    def test_number_dot_title_dot(self):
        pat = self._create("<tracknumber>. <title>.")
        if os.name == "nt":
            # Can't have Windows names ending with dot
            self.assertEquals(pat.format(self.a), "05. Title5_")
            self.assertEquals(pat.format(self.b), "06. Title6_")
            self.assertEquals(pat.format(self.c), ". test_subdir_")
        else:
            self.assertEquals(pat.format(self.a), "05. Title5.")
            self.assertEquals(pat.format(self.b), "06. Title6.")
            self.assertEquals(pat.format(self.c), ". test_subdir.")

    def test_tracknumber_decimals(self):
        pat = self._create("<tracknumber>. <title>")
        self.assertEquals(pat.format(self.a), "05. Title5")
        self.assertEquals(pat.format(self.e), "0007. Title7")

    def test_constant_albumart_example(self):
        pat = self._create("folder.jpg")
        self.assertEquals(pat.format(self.a), "folder.jpg")

    def test_extra_dots(self):
        pat = self._create("<artist~album>.png")
        self.assertEquals(pat.format(self.f), "Foo - Best Of.png")
        pat = self._create("<albumartist~title>.png")
        self.assertEquals(pat.format(self.f), "foo.bar - The.Final.Word.png")


class TXMLFromPattern(_TPattern):
    def test_markup_passthrough(self):
        pat = XMLFromPattern(r"\<b\>&lt;<title>&gt;\</b\>")
        self.assertEquals(pat.format(self.a), "<b>&lt;Title5&gt;</b>")
        self.assertEquals(pat.format(self.b), "<b>&lt;Title6&gt;</b>")
        self.assertEquals(pat.format(self.c), "<b>&lt;test/subdir&gt;</b>")

    def test_escape(self):
        pat = XMLFromPattern(r"\<b\>&lt;<xmltest>&gt;\</b\>")
        self.assertEquals(pat.format(self.a), "<b>&lt;&lt;&amp;&gt;&gt;</b>")

    def test_cond_markup(self):
        pat = XMLFromPattern(r"<title|\<b\><title> woo\</b\>>")
        self.assertEquals(pat.format(self.a), "<b>Title5 woo</b>")


class TXMLFromMarkupPattern(_TPattern):

    def _test_markup(self, text):
        from gi.repository import Pango
        Pango.parse_markup(text, -1, "\x00")

    def test_convenience(self):
        pat = XMLFromMarkupPattern(r"[b]foo[/b]")
        self.assertEquals(pat.format(self.a), "<b>foo</b>")
        self._test_markup(pat.format(self.a))

        pat = XMLFromMarkupPattern("[small ]foo[/small \t]")
        self.assertEquals(pat.format(self.a), "<small >foo</small \t>")
        self._test_markup(pat.format(self.a))

    def test_link(self):
        pat = XMLFromMarkupPattern(r'[a href=""]foo[/a]')
        self.assertEquals(pat.format(self.a), '<a href="">foo</a>')

    def test_convenience_invalid(self):
        pat = XMLFromMarkupPattern(r'[b foo="1"]')
        self.assertEquals(pat.format(self.a), '[b foo="1"]')
        self._test_markup(pat.format(self.a))

    def test_span(self):
        pat = XMLFromMarkupPattern(r"[span]foo[/span]")
        self.assertEquals(pat.format(self.a), "<span>foo</span>")
        self._test_markup(pat.format(self.a))

        pat = XMLFromMarkupPattern(r'[span  weight="bold"]foo[/span]')
        self.assertEquals(pat.format(self.a), '<span  weight="bold">foo</span>')
        self._test_markup(pat.format(self.a))

    def test_escape(self):
        pat = XMLFromMarkupPattern(r"\[b]")
        self.assertEquals(pat.format(self.a), "[b]")
        self._test_markup(pat.format(self.a))

        pat = XMLFromMarkupPattern(r"\\\\[b]\\\\[/b]")
        self.assertEquals(pat.format(self.a), r"\\<b>\\</b>")
        self._test_markup(pat.format(self.a))


class TRealTags(TestCase):
    def test_empty(self):
        self.failUnlessEqual(Pattern("").tags, [])

    def test_both(self):
        pat = "<foo|<~bar~fuu> - <fa>|<bar>>"
        self.failUnlessEqual(Pattern(pat).tags, ["bar", "fuu", "fa"])

        pat = "<foo|<~bar~fuu> - <fa>|<quux>>"
        self.failUnlessEqual(Pattern(pat).tags, ["bar", "fuu", "fa", "quux"])


class TPatternFormatList(_TPattern):

    def test_numeric(self):
        pat = Pattern("<~#rating>")
        self.assertEqual(pat.format_list(self.a), {("0.50", "0.50")})

    def test_empty(self):
        pat = Pattern("<nopenope>")
        self.assertEqual(pat.format_list(self.a), {("", "")})

    def test_same(self):
        pat = Pattern("<~basename> <title>")
        self.failUnlessEqual(pat.format_list(self.a),
                             {(pat.format(self.a), pat.format(self.a))})
        pat = Pattern("/a<genre|/<genre>>/<title>")
        self.failUnlessEqual(pat.format_list(self.a),
                             {(pat.format(self.a), pat.format(self.a))})

    def test_same2(self):
        fpat = FileFromPattern("<~filename>")
        pat = Pattern("<~filename>")
        self.assertEquals(fpat.format_list(self.a),
                          {(fpat.format(self.a), fpat.format(self.a))})
        self.assertEquals(pat.format_list(self.a),
                          {(pat.format(self.a), pat.format(self.a))})

    def test_tied(self):
        pat = Pattern("<genre>")
        self.failUnlessEqual(pat.format_list(self.c), {("/", "/")})
        pat = Pattern("<performer>")
        self.failUnlessEqual(pat.format_list(self.d), {("a", "a"), ("b", "b")})
        pat = Pattern("<performer><performer>")
        self.failUnlessEqual(set(pat.format_list(self.d)),
                             {("aa", "aa"), ("ab", "ab"),
                              ("ba", "ba"), ("bb", "bb")})
        pat = Pattern("<~performer~artist>")
        self.failUnlessEqual(pat.format_list(self.d),
                             {("a", "a"), ("b", "b"),
                              ("bar", "bar"), ("foo", "foo")})
        pat = Pattern("<performer~artist>")
        self.failUnlessEqual(pat.format_list(self.d),
                             {("a", "a"), ("b", "b"),
                              ("bar", "bar"), ("foo", "foo")})
        pat = Pattern("<artist|<artist>.|<performer>>")
        self.failUnlessEqual(pat.format_list(self.d),
                             {("foo.", "foo."), ("bar.", "bar.")})
        pat = Pattern("<artist|<artist|<artist>.|<performer>>>")
        self.failUnlessEqual(pat.format_list(self.d),
                             {("foo.", "foo."), ("bar.", "bar.")})

    def test_sort(self):
        pat = Pattern("<album>")
        self.failUnlessEqual(pat.format_list(self.f),
                             {(u"Best Of", u"Best Of")})
        pat = Pattern("<album>")
        self.failUnlessEqual(pat.format_list(self.h), {(u"Album5", u"SortAlbum5")})
        pat = Pattern("<artist>")
        self.failUnlessEqual(pat.format_list(self.h), {(u"Artist1", u"SortA1"),
                                                       (u"Artist3", u"Artist3")})
        pat = Pattern("<artist> x")
        self.failUnlessEqual(pat.format_list(self.h), {(u"Artist1 x", u"SortA1 x"),
                                                       (u"Artist3 x", u"Artist3 x")})

    def test_sort_tied(self):
        pat = Pattern("<~artist~album>")
        self.failUnlessEqual(pat.format_list(self.h), {(u"Artist1", u"SortA1"),
                                                       (u"Artist3", u"Artist3"),
                                                       (u"Album5", u"SortAlbum5")})
        pat = Pattern("<~album~artist>")
        self.failUnlessEqual(pat.format_list(self.h), {(u"Artist1", u"SortA1"),
                                                       (u"Artist3", u"Artist3"),
                                                       (u"Album5", u"SortAlbum5")})
        pat = Pattern("<~artist~artist>")
        self.failUnlessEqual(pat.format_list(self.h), {(u"Artist1", u"SortA1"),
                                                       (u"Artist3", u"Artist3")})

    def test_sort_combine(self):
        pat = Pattern("<album> <artist>")
        self.failUnlessEqual(pat.format_list(self.h),
                             {(u"Album5 Artist1", u"SortAlbum5 SortA1"),
                              (u"Album5 Artist3", u"SortAlbum5 Artist3")})
        pat = Pattern("x <artist> <album>")
        self.failUnlessEqual(pat.format_list(self.h),
                             {(u"x Artist1 Album5", u"x SortA1 SortAlbum5"),
                              (u"x Artist3 Album5", u"x Artist3 SortAlbum5")})
        pat = Pattern(" <artist> <album> xx")
        self.failUnlessEqual(pat.format_list(self.h),
                             {(u" Artist1 Album5 xx", u" SortA1 SortAlbum5 xx"),
                              (u" Artist3 Album5 xx", u" Artist3 SortAlbum5 xx")})
        pat = Pattern("<album> <tracknumber> <artist>")
        self.failUnlessEqual(pat.format_list(self.h),
                             {(u"Album5 7/8 Artist1", u"SortAlbum5 7/8 SortA1"),
                              (u"Album5 7/8 Artist3", u"SortAlbum5 7/8 Artist3")})
        pat = Pattern("<tracknumber> <album> <artist>")
        self.failUnlessEqual(pat.format_list(self.h),
                             {(u"7/8 Album5 Artist1", u"7/8 SortAlbum5 SortA1"),
                              (u"7/8 Album5 Artist3", u"7/8 SortAlbum5 Artist3")})

    def test_sort_multiply(self):
        pat = Pattern("<artist> <artist>")
        self.failUnlessEqual(pat.format_list(self.h),
                             {(u"Artist1 Artist1", u"SortA1 SortA1"),
                              (u"Artist3 Artist1", u"Artist3 SortA1"),
                              (u"Artist1 Artist3", u"SortA1 Artist3"),
                              (u"Artist3 Artist3", u"Artist3 Artist3")})

    def test_missing_value(self):
        pat = Pattern("<genre> - <artist>")
        self.assertEqual(pat.format_list(self.a),
                         {(" - Artist", " - Artist")})
        pat = Pattern("")
        self.assertEqual(pat.format_list(self.a), {("", "")})

    def test_string(self):
        pat = Pattern("display")
        self.assertEqual(pat.format_list(self.a), {("display", "display")})
