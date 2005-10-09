from unittest import TestCase
from tests import registerCase
from pattern import FileFromPattern, XMLFromPattern, Pattern

import os

class _TPattern(TestCase):
    from formats._audio import AudioFile

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

class TPattern(_TPattern):
    from formats._audio import AudioFile

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
        s.assertEqual(Pattern('<tracknumber|a|b|c>').format(s.a),
                      "<tracknumber|a|b|c>")

    def test_conditional_genre(s):
        pat = Pattern('<genre|<genre>|music>')
        s.assertEquals(pat.format(s.a), 'music')
        s.assertEquals(pat.format(s.b), 'music')
        s.assertEquals(pat.format(s.c), '/, /')

    def test_conditional_unknown(s):
        pat = Pattern('<album|foo|bar>')
        s.assertEquals(pat.format(s.a), 'bar')

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
        pat = Pattern('\<<tracknumber>\>. <title>')
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
        song = s.AudioFile({"tracknumber": "5/6",
            "title": "\xe3\x81\x99\xe3\x81\xbf\xe3\x82\x8c".decode('utf-8')})
        pat = Pattern('<~#track>. <title>')
        s.assertEquals(pat.format(song),
            "5. \xe3\x81\x99\xe3\x81\xbf\xe3\x82\x8c".decode('utf-8'))

class TFileFromPattern(_TPattern):
    def test_escape_slash(s):
        fpat = FileFromPattern('<~filename>')
        pat = Pattern('<~filename>')
        s.assertEquals(fpat.format(s.a), "_path_to_a.mp3")
        s.assertEquals(pat.format(s.a), "/path/to/a.mp3")

    def test_specialcase_anti_ext(s):
        p1 = FileFromPattern('<~filename>')
        p2 = FileFromPattern('<~dirname>_<~basename>')
        s.assertEquals(p1.format(s.a), p2.format(s.a))
        s.assertEquals(p1.format(s.a), '_path_to_a.mp3')
        s.assertEquals(p1.format(s.b), p2.format(s.b))
        s.assertEquals(p1.format(s.b), '_path_to_b.ogg')
        s.assertEquals(p1.format(s.c), p2.format(s.c))
        s.assertEquals(p1.format(s.c), '_one_more_a.flac')

    def test_number_dot_title_dot(s):
        pat = FileFromPattern('<tracknumber>. <title>.')
        s.assertEquals(pat.format(s.a), '05. Title5..mp3')
        s.assertEquals(pat.format(s.b), '06. Title6..ogg')
        s.assertEquals(pat.format(s.c), '. test_subdir..flac')

    def test_raw_slash_preservation(s):
        pat = FileFromPattern('/a/b/<genre>')
        s.assertEquals(pat.format(s.a), '/a/b/.mp3')
        s.assertEquals(pat.format(s.b), '/a/b/.ogg')
        s.assertEquals(pat.format(s.c), '/a/b/_, _.flac')

    def test_directory_rooting(s):
        s.assertRaises(ValueError, FileFromPattern, 'a/<b>')
        FileFromPattern('/<a>/<b>')

class TXMLFromPattern(_TPattern):
    def test_markup_passthrough(s):
        pat = XMLFromPattern(r'\<b\>&lt;<title>&gt;\</b\>')
        s.assertEquals(pat.format(s.a), '<b>&lt;Title5&gt;</b>')
        s.assertEquals(pat.format(s.b), '<b>&lt;Title6&gt;</b>')
        s.assertEquals(pat.format(s.c), '<b>&lt;test/subdir&gt;</b>')

    def test_cond_markup(s):
        pat = XMLFromPattern(r'<title|\<b\><title> woo\</b\>>')
        s.assertEquals(pat.format(s.a), '<b>Title5 woo</b>')

registerCase(TPattern)
registerCase(TFileFromPattern)
registerCase(TXMLFromPattern)
