# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from senf import fsnative

from tests import TestCase

from quodlibet.formats import AudioFile
from quodlibet.pattern import (FileFromPattern, XMLFromPattern, Pattern,
    XMLFromMarkupPattern, ArbitraryExtensionFileFromPattern)


class _TPattern(TestCase):

    def setUp(self):
        s1 = {'tracknumber': u'5/6', 'artist': u'Artist', 'title': u'Title5',
              '~filename': '/path/to/a.mp3', 'xmltest': u"<&>"}
        s2 = {'tracknumber': u'6', 'artist': u'Artist', 'title': u'Title6',
              '~filename': '/path/to/b.ogg', 'discnumber': u'2',
              'unislash': u"foo\uff0fbar"}
        s3 = {'title': u'test/subdir', 'genre': u'/\n/',
              '~filename': '/one/more/a.flac', 'version': u'Instrumental'}
        s4 = {'performer': u'a\nb', 'artist': u'foo\nbar'}
        s5 = {'tracknumber': u'7/1234', 'artist': u'Artist',
              'title': u'Title7', '~filename': '/path/to/e.mp3'}
        s6 = {'artist': u'Foo', 'albumartist': u'foo.bar', 'album': u'Best Of',
              '~filename': '/path/to/f.mp3', 'title': u'The.Final.Word'}
        s7 = {'artist': u'un élève français', '~filename': '/path/to/g.mp3',
              'albumartist': u'Lee "Scratch" Perry',
              'album': u"The 'only' way!", 'comment': u'Trouble|Strife'}
        s8 = {'tracknumber': u'7/8', 'artist': u'Artist1\n\nArtist3',
              'artistsort': u'SortA1\nSortA2',
              'album': u'Album5', 'albumsort': u'SortAlbum5',
              '~filename': '/path/to/g.mp3', 'xmltest': u"<&>"}

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
    AudioFile

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

    def test_conditional_number_dot_title(s):
        pat = Pattern('<tracknumber|<tracknumber>. ><title>')
        s.assertEquals(pat.format(s.a), '5/6. Title5')
        s.assertEquals(pat.format(s.b), '6. Title6')
        s.assertEquals(pat.format(s.c), 'test/subdir')

    def test_conditional_other_number_dot_title(s):
        pat = Pattern('<tracknumber|<tracknumber>|00>. <title>')
        s.assertEquals(pat.format(s.a), '5/6. Title5')
        s.assertEquals(pat.format(s.b), '6. Title6')
        s.assertEquals(pat.format(s.c), '00. test/subdir')

    def test_conditional_other_other(s):
        # FIXME: was <tracknumber|a|b|c>.. but we can't put <>| in the format
        # string since it would break the XML pattern formatter.
        s.assertEqual(Pattern('<tracknumber|a|b|c>').format(s.a), "")

    def test_conditional_genre(s):
        pat = Pattern('<genre|<genre>|music>')
        s.assertEquals(pat.format(s.a), 'music')
        s.assertEquals(pat.format(s.b), 'music')
        s.assertEquals(pat.format(s.c), '/, /')

    def test_conditional_unknown(s):
        pat = Pattern('<album|foo|bar>')
        s.assertEquals(pat.format(s.a), 'bar')

    def test_conditional_equals(s):
        pat = Pattern('<artist=Artist|matched|not matched>')
        s.assertEquals(pat.format(s.a), 'matched')
        pat = Pattern('<artist=Artistic|matched|not matched>')
        s.assertEquals(pat.format(s.a), 'not matched')

    def test_conditional_equals_unicode(s):
        pat = Pattern(u'<artist=Artist|matched|not matched>')
        s.assertEquals(pat.format(s.g), 'not matched')
        pat = Pattern(u'<artist=un élève français|matched|not matched>')
        s.assertEquals(pat.format(s.g), 'matched')

    def test_duplicate_query(self):
        pat = Pattern('<u=yes|<u=yes|x|y>|<u=yes|q|z>>')
        self.assertEqual(pat.format(AudioFile({"u": u"yes"})), "x")
        self.assertEqual(pat.format(AudioFile({"u": u"no"})), "z")

    def test_tag_query_escaping(s):
        pat = Pattern('<albumartist=Lee "Scratch" Perry|matched|not matched>')
        s.assertEquals(pat.format(s.g), 'matched')

    def test_tag_query_escaped_pipe(s):
        pat = Pattern(r'<albumartist=/Lee\|Bob/|matched|not matched>')
        s.assertEquals(pat.format(s.g), 'matched')
        pat = Pattern(r'<albumartist=\||matched|not matched>')
        s.assertEquals(pat.format(s.g), 'not matched')
        pat = Pattern(r'<comment=/Trouble\|Strife/|matched|not matched>')
        s.assertEquals(pat.format(s.g), 'matched')

    def test_tag_query_quoting(s):
        pat = Pattern('<album=The only way|matched|not matched>')
        s.assertEquals(pat.format(s.g), 'not matched')
        pat = Pattern("<album=\"The 'only' way!\"|matched|not matched>")
        s.assertEquals(pat.format(s.g), 'matched')

    def test_tag_query_regex(s):
        pat = Pattern("<album=/'only'/|matched|not matched>")
        s.assertEquals(pat.format(s.g), 'matched')
        pat = Pattern("<album=/The .+ way/|matched|not matched>")
        s.assertEquals(pat.format(s.g), 'matched')
        pat = Pattern("</The .+ way/|matched|not matched>")
        s.assertEquals(pat.format(s.g), 'not matched')

    def test_tag_internal(self):
        if os.name != "nt":
            pat = Pattern("<~filename='/path/to/a.mp3'|matched|not matched>")
            self.assertEquals(pat.format(self.a), 'matched')
            pat = Pattern(
                "<~filename=/\\/path\\/to\\/a.mp3/|matched|not matched>")
            self.assertEquals(pat.format(self.a), 'matched')
        else:
            pat = Pattern(
                r"<~filename='C:\\\path\\\to\\\a.mp3'|matched|not matched>")
            self.assertEquals(pat.format(self.a), 'matched')

    def test_tag_query_disallowed_free_text(s):
        pat = Pattern("<The only way|matched|not matched>")
        s.assertEquals(pat.format(s.g), 'not matched')

    def test_query_scope(self):
        pat = Pattern("<foo|<artist=Foo|x|y>|<artist=Foo|z|q>>")
        self.assertEqual(pat.format(self.f), "z")

    def test_query_numeric(self):
        pat = Pattern("<#(foo=42)|42|other>")
        self.assertEqual(pat.format(AudioFile()), "other")
        self.assertEqual(pat.format(AudioFile({"foo": "42"})), "42")

    def test_conditional_notfile(s):
        pat = Pattern('<tracknumber|<tracknumber>|00>')
        s.assertEquals(pat.format(s.a), '5/6')
        s.assertEquals(pat.format(s.b), '6')
        s.assertEquals(pat.format(s.c), '00')

    def test_conditional_subdir(s):
        pat = Pattern('/a<genre|/<genre>>/<title>')
        s.assertEquals(pat.format(s.a), '/a/Title5')
        s.assertEquals(pat.format(s.b), '/a/Title6')
        s.assertEquals(pat.format(s.c), '/a//, //test/subdir')

    def test_number_dot_title(s):
        pat = Pattern('<tracknumber>. <title>')
        s.assertEquals(pat.format(s.a), '5/6. Title5')
        s.assertEquals(pat.format(s.b), '6. Title6')
        s.assertEquals(pat.format(s.c), '. test/subdir')

    def test_recnumber_dot_title(s):
        pat = Pattern(r'\<<tracknumber>\>. <title>')
        s.assertEquals(pat.format(s.a), '<5/6>. Title5')
        s.assertEquals(pat.format(s.b), '<6>. Title6')
        s.assertEquals(pat.format(s.c), '<>. test/subdir')

    def test_generated(s):
        pat = Pattern('<~basename>')
        s.assertEquals(pat.format(s.a), os.path.basename(s.a["~filename"]))

    def test_generated_and_not_generated(s):
        pat = Pattern('<~basename> <title>')
        res = pat.format(s.a)
        s.assertEquals(
            res, os.path.basename(s.a["~filename"]) + " " + s.a["title"])

    def test_number_dot_title_dot(s):
        pat = Pattern('<tracknumber>. <title>.')
        s.assertEquals(pat.format(s.a), '5/6. Title5.')
        s.assertEquals(pat.format(s.b), '6. Title6.')
        s.assertEquals(pat.format(s.c), '. test/subdir.')

    def test_number_dot_genre(s):
        pat = Pattern('<tracknumber>. <genre>')
        s.assertEquals(pat.format(s.a), '5/6. ')
        s.assertEquals(pat.format(s.b), '6. ')
        s.assertEquals(pat.format(s.c), '. /, /')

    def test_unicode_with_int(s):
        song = AudioFile({"tracknumber": "5/6",
            "title": b"\xe3\x81\x99\xe3\x81\xbf\xe3\x82\x8c".decode('utf-8')})
        pat = Pattern('<~#track>. <title>')
        s.assertEquals(pat.format(song),
            b"5. \xe3\x81\x99\xe3\x81\xbf\xe3\x82\x8c".decode('utf-8'))


class _TFileFromPattern(_TPattern):
    def _create(self, string):
        return FileFromPattern(string)

    def test_escape_slash(s):
        fpat = s._create('<~filename>')
        s.assertTrue(fpat.format(s.a).endswith("_path_to_a.mp3"))

        pat = Pattern('<~filename>')
        if os.name != "nt":
            s.assertTrue(pat.format(s.a).startswith("/path/to/a"))
        else:
            s.assertTrue(pat.format(s.a).startswith("C:\\path\\to\\a"))

        if os.name != "nt":
            wpat = s._create(r'\\<artist>\\ "<title>')
            s.assertTrue(
                wpat.format(s.a).startswith(r'\Artist\ "Title5'))
        else:
            # FIXME..
            pass

    def test_directory_rooting(s):
        if os.name == "nt":
            s.assertRaises(ValueError, FileFromPattern, 'a\\<b>')
            s.assertRaises(ValueError, FileFromPattern, '<a>\\<b>')
            s._create('C:\\<a>\\<b>')

        else:
            s.assertRaises(ValueError, FileFromPattern, 'a/<b>')
            s.assertRaises(ValueError, FileFromPattern, '<a>/<b>')
            s._create('/<a>/<b>')

    def test_backslash_conversion_win32(s):
        if os.name == 'nt':
            pat = s._create(r'Z:\<artist>\<title>')
            s.assertTrue(pat.format(s.a).startswith(r'Z:\Artist\Title5'))

    def test_raw_slash_preservation(s):
        if os.name == "nt":
            pat = s._create('C:\\a\\b\\<genre>')
            s.assertTrue(pat.format(s.a).startswith('C:\\a\\b\\'))
            s.assertTrue(pat.format(s.b).startswith('C:\\a\\b\\'))
            s.assertTrue(pat.format(s.c).startswith('C:\\a\\b\\_, _'))

        else:
            pat = s._create('/a/b/<genre>')
            s.assertTrue(pat.format(s.a).startswith('/a/b/'))
            s.assertTrue(pat.format(s.b).startswith('/a/b/'))
            s.assertTrue(pat.format(s.c).startswith('/a/b/_, _'))

    def test_specialcase_anti_ext(s):
        p1 = s._create('<~filename>')
        p2 = s._create('<~dirname>_<~basename>')
        s.assertEquals(p1.format(s.a), p2.format(s.a))
        s.assertTrue(p1.format(s.a).endswith('_path_to_a.mp3'))
        s.assertEquals(p1.format(s.b), p2.format(s.b))
        s.assertTrue(p1.format(s.b).endswith('_path_to_b.ogg'))
        s.assertEquals(p1.format(s.c), p2.format(s.c))
        s.assertTrue(p1.format(s.c).endswith('_one_more_a.flac'))

    def test_long_filename(s):
        if os.name == "nt":
            a = AudioFile({"title": "x" * 300, "~filename": u"C:\\f.mp3"})
            path = s._create(u'C:\\foobar\\ä<title>\\<title>').format(a)
            assert isinstance(path, fsnative)
            s.failUnlessEqual(len(path), 3 + 6 + 1 + 255 + 1 + 255)
            path = s._create(u'äüö<title><title>').format(a)
            assert isinstance(path, fsnative)
            s.failUnlessEqual(len(path), 255)
        else:
            a = AudioFile({"title": "x" * 300, "~filename": "/f.mp3"})
            path = s._create(u'/foobar/ä<title>/<title>').format(a)
            assert isinstance(path, fsnative)
            s.failUnlessEqual(len(path), 1 + 6 + 1 + 255 + 1 + 255)
            path = s._create(u'äüö<title><title>').format(a)
            assert isinstance(path, fsnative)
            s.failUnlessEqual(len(path), 255)


class TFileFromPattern(_TFileFromPattern):
    def _create(self, string):
        return FileFromPattern(string)

    def test_type(self):
        pat = self._create('')
        self.assertTrue(isinstance(pat.format(self.a), fsnative))
        pat = self._create('<title>')
        self.assertTrue(isinstance(pat.format(self.a), fsnative))

    def test_number_dot_title_dot(s):
        pat = s._create('<tracknumber>. <title>.')
        s.assertEquals(pat.format(s.a), '05. Title5..mp3')
        s.assertEquals(pat.format(s.b), '06. Title6..ogg')
        s.assertEquals(pat.format(s.c), '. test_subdir..flac')

    def test_tracknumber_decimals(s):
        pat = s._create('<tracknumber>. <title>')
        s.assertEquals(pat.format(s.a), '05. Title5.mp3')
        s.assertEquals(pat.format(s.e), '0007. Title7.mp3')

    def test_ext_case_preservation(s):
        x = AudioFile({'~filename': fsnative(u'/tmp/Xx.Flac'), 'title': 'Xx'})
        # If pattern has a particular ext, preserve case of ext
        p1 = s._create('<~basename>')
        s.assertEquals(p1.format(x), 'Xx.Flac')
        p2 = s._create('<title>.FLAC')
        s.assertEquals(p2.format(x), 'Xx.FLAC')
        # If pattern doesn't have a particular ext, lowercase ext
        p3 = s._create('<title>')
        s.assertEquals(p3.format(x), 'Xx.flac')


class TArbitraryExtensionFileFromPattern(_TFileFromPattern):
    def _create(self, string):
        return ArbitraryExtensionFileFromPattern(string)

    def test_number_dot_title_dot(s):
        pat = s._create('<tracknumber>. <title>.')
        if os.name == 'nt':
            # Can't have Windows names ending with dot
            s.assertEquals(pat.format(s.a), '05. Title5_')
            s.assertEquals(pat.format(s.b), '06. Title6_')
            s.assertEquals(pat.format(s.c), '. test_subdir_')
        else:
            s.assertEquals(pat.format(s.a), '05. Title5.')
            s.assertEquals(pat.format(s.b), '06. Title6.')
            s.assertEquals(pat.format(s.c), '. test_subdir.')

    def test_tracknumber_decimals(s):
        pat = s._create('<tracknumber>. <title>')
        s.assertEquals(pat.format(s.a), '05. Title5')
        s.assertEquals(pat.format(s.e), '0007. Title7')

    def test_constant_albumart_example(s):
        pat = s._create("folder.jpg")
        s.assertEquals(pat.format(s.a), 'folder.jpg')

    def test_extra_dots(s):
        pat = s._create("<artist~album>.png")
        s.assertEquals(pat.format(s.f), 'Foo - Best Of.png')
        pat = s._create("<albumartist~title>.png")
        s.assertEquals(pat.format(s.f), 'foo.bar - The.Final.Word.png')


class TXMLFromPattern(_TPattern):
    def test_markup_passthrough(s):
        pat = XMLFromPattern(r'\<b\>&lt;<title>&gt;\</b\>')
        s.assertEquals(pat.format(s.a), '<b>&lt;Title5&gt;</b>')
        s.assertEquals(pat.format(s.b), '<b>&lt;Title6&gt;</b>')
        s.assertEquals(pat.format(s.c), '<b>&lt;test/subdir&gt;</b>')

    def test_escape(s):
        pat = XMLFromPattern(r'\<b\>&lt;<xmltest>&gt;\</b\>')
        s.assertEquals(pat.format(s.a), '<b>&lt;&lt;&amp;&gt;&gt;</b>')

    def test_cond_markup(s):
        pat = XMLFromPattern(r'<title|\<b\><title> woo\</b\>>')
        s.assertEquals(pat.format(s.a), '<b>Title5 woo</b>')


class TXMLFromMarkupPattern(_TPattern):

    def _test_markup(self, text):
        from gi.repository import Pango
        Pango.parse_markup(text, -1, "\x00")

    def test_convenience(s):
        pat = XMLFromMarkupPattern(r'[b]foo[/b]')
        s.assertEquals(pat.format(s.a), '<b>foo</b>')
        s._test_markup(pat.format(s.a))

        pat = XMLFromMarkupPattern('[small ]foo[/small \t]')
        s.assertEquals(pat.format(s.a), '<small >foo</small \t>')
        s._test_markup(pat.format(s.a))

    def test_link(s):
        pat = XMLFromMarkupPattern(r'[a href=""]foo[/a]')
        s.assertEquals(pat.format(s.a), '<a href="">foo</a>')

    def test_convenience_invalid(s):
        pat = XMLFromMarkupPattern(r'[b foo="1"]')
        s.assertEquals(pat.format(s.a), '[b foo="1"]')
        s._test_markup(pat.format(s.a))

    def test_span(s):
        pat = XMLFromMarkupPattern(r'[span]foo[/span]')
        s.assertEquals(pat.format(s.a), '<span>foo</span>')
        s._test_markup(pat.format(s.a))

        pat = XMLFromMarkupPattern(r'[span  weight="bold"]foo[/span]')
        s.assertEquals(pat.format(s.a), '<span  weight="bold">foo</span>')
        s._test_markup(pat.format(s.a))

    def test_escape(s):
        pat = XMLFromMarkupPattern(r'\[b]')
        s.assertEquals(pat.format(s.a), '[b]')
        s._test_markup(pat.format(s.a))

        pat = XMLFromMarkupPattern(r'\\\\[b]\\\\[/b]')
        s.assertEquals(pat.format(s.a), r'\\<b>\\</b>')
        s._test_markup(pat.format(s.a))


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

    def test_same(s):
        pat = Pattern('<~basename> <title>')
        s.failUnlessEqual(pat.format_list(s.a),
                          {(pat.format(s.a), pat.format(s.a))})
        pat = Pattern('/a<genre|/<genre>>/<title>')
        s.failUnlessEqual(pat.format_list(s.a),
                          {(pat.format(s.a), pat.format(s.a))})

    def test_same2(s):
        fpat = FileFromPattern('<~filename>')
        pat = Pattern('<~filename>')
        s.assertEquals(fpat.format_list(s.a),
                       {(fpat.format(s.a), fpat.format(s.a))})
        s.assertEquals(pat.format_list(s.a),
                       {(pat.format(s.a), pat.format(s.a))})

    def test_tied(s):
        pat = Pattern('<genre>')
        s.failUnlessEqual(pat.format_list(s.c), {('/', '/')})
        pat = Pattern('<performer>')
        s.failUnlessEqual(pat.format_list(s.d), {('a', 'a'), ('b', 'b')})
        pat = Pattern('<performer><performer>')
        s.failUnlessEqual(set(pat.format_list(s.d)),
                          {('aa', 'aa'), ('ab', 'ab'),
                           ('ba', 'ba'), ('bb', 'bb')})
        pat = Pattern('<~performer~artist>')
        s.failUnlessEqual(pat.format_list(s.d),
                          {('a', 'a'), ('b', 'b'),
                           ('bar', 'bar'), ('foo', 'foo')})
        pat = Pattern('<performer~artist>')
        s.failUnlessEqual(pat.format_list(s.d),
                          {('a', 'a'), ('b', 'b'),
                           ('bar', 'bar'), ('foo', 'foo')})
        pat = Pattern('<artist|<artist>.|<performer>>')
        s.failUnlessEqual(pat.format_list(s.d),
                          {('foo.', 'foo.'), ('bar.', 'bar.')})
        pat = Pattern('<artist|<artist|<artist>.|<performer>>>')
        s.failUnlessEqual(pat.format_list(s.d),
                          {('foo.', 'foo.'), ('bar.', 'bar.')})

    def test_sort(s):
        pat = Pattern('<album>')
        s.failUnlessEqual(pat.format_list(s.f),
                          {(u'Best Of', u'Best Of')})
        pat = Pattern('<album>')
        s.failUnlessEqual(pat.format_list(s.h), {(u'Album5', u'SortAlbum5')})
        pat = Pattern('<artist>')
        s.failUnlessEqual(pat.format_list(s.h), {(u'Artist1', u'SortA1'),
                                                 (u'', u'SortA2'),
                                                 (u'Artist3', u'Artist3')})
        pat = Pattern('<artist> x')
        s.failUnlessEqual(pat.format_list(s.h), {(u'Artist1 x', u'SortA1 x'),
                                                 (u' x', u'SortA2 x'),
                                                 (u'Artist3 x', u'Artist3 x')})

    def test_sort_tied(s):
        pat = Pattern('<~artist~album>')
        s.failUnlessEqual(pat.format_list(s.h), {(u'Artist1', u'SortA1'),
                                                 (u'', u'SortA2'),
                                                 (u'Artist3', u'Artist3'),
                                                 (u'Album5', u'SortAlbum5')})
        pat = Pattern('<~album~artist>')
        s.failUnlessEqual(pat.format_list(s.h), {(u'Artist1', u'SortA1'),
                                                 (u'', u'SortA2'),
                                                 (u'Artist3', u'Artist3'),
                                                 (u'Album5', u'SortAlbum5')})
        pat = Pattern('<~artist~artist>')
        s.failUnlessEqual(pat.format_list(s.h), {(u'Artist1', u'SortA1'),
                                                 (u'', u'SortA2'),
                                                 (u'Artist3', u'Artist3')})

    def test_sort_combine(s):
        pat = Pattern('<album> <artist>')
        s.failUnlessEqual(pat.format_list(s.h),
                          {(u'Album5 Artist1', u'SortAlbum5 SortA1'),
                           (u'Album5 ', u'SortAlbum5 SortA2'),
                           (u'Album5 Artist3', u'SortAlbum5 Artist3')})
        pat = Pattern('x <artist> <album>')
        s.failUnlessEqual(pat.format_list(s.h),
                          {(u'x Artist1 Album5', u'x SortA1 SortAlbum5'),
                           (u'x  Album5', u'x SortA2 SortAlbum5'),
                           (u'x Artist3 Album5', u'x Artist3 SortAlbum5')})
        pat = Pattern(' <artist> <album> xx')
        s.failUnlessEqual(pat.format_list(s.h),
                          {(u' Artist1 Album5 xx', u' SortA1 SortAlbum5 xx'),
                           (u'  Album5 xx', u' SortA2 SortAlbum5 xx'),
                           (u' Artist3 Album5 xx', u' Artist3 SortAlbum5 xx')})
        pat = Pattern('<album> <tracknumber> <artist>')
        s.failUnlessEqual(pat.format_list(s.h),
                          {(u'Album5 7/8 Artist1', u'SortAlbum5 7/8 SortA1'),
                           (u'Album5 7/8 ', u'SortAlbum5 7/8 SortA2'),
                           (u'Album5 7/8 Artist3', u'SortAlbum5 7/8 Artist3')})
        pat = Pattern('<tracknumber> <album> <artist>')
        s.failUnlessEqual(pat.format_list(s.h),
                          {(u'7/8 Album5 Artist1', u'7/8 SortAlbum5 SortA1'),
                           (u'7/8 Album5 ', u'7/8 SortAlbum5 SortA2'),
                           (u'7/8 Album5 Artist3', u'7/8 SortAlbum5 Artist3')})

    def test_sort_multiply(s):
        pat = Pattern('<artist> <artist>')
        s.failUnlessEqual(pat.format_list(s.h),
                          {(u'Artist1 Artist1', u'SortA1 SortA1'),
                           (u' Artist1', u'SortA2 SortA1'),
                           (u'Artist3 Artist1', u'Artist3 SortA1'),
                           (u'Artist1 ', u'SortA1 SortA2'),
                           (u' ', u'SortA2 SortA2'),
                           (u'Artist3 ', u'Artist3 SortA2'),
                           (u'Artist1 Artist3', u'SortA1 Artist3'),
                           (u' Artist3', u'SortA2 Artist3'),
                           (u'Artist3 Artist3', u'Artist3 Artist3')})

    def test_missing_value(self):
        pat = Pattern('<genre> - <artist>')
        self.assertEqual(pat.format_list(self.a),
                         {(" - Artist", " - Artist")})
        pat = Pattern('')
        self.assertEqual(pat.format_list(self.a), {("", "")})

    def test_string(s):
        pat = Pattern('display')
        s.assertEqual(pat.format_list(s.a), {("display", "display")})
