# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from quodlibet.formats._audio import AudioFile
from tests.plugin import PluginTestCase


class TMPDServer(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["mpd_server"]

    def test_parse_command(self):
        parse = self.mod.main.parse_command

        self.assertEqual(parse("foo bar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\tbar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\t bar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\t bar quux"), ("foo", ["bar", "quux"]))
        self.assertEqual(
            parse("foo\t bar \"q 2\" x"), ("foo", ["bar", "q 2", "x"]))
        self.assertEqual(parse("foo 'bar  quux'"), ("foo", ["'bar", "quux'"]))
        self.assertEqual(
            parse("foo \xc3\xb6\xc3\xa4\xc3\xbc"), ("foo", [u"\xf6\xe4\xfc"]))

    def test_format_tags(self):
        format_tags = self.mod.main.format_tags

        def getline(key, value):
            song = AudioFile({"~filename": "/dev/null"})
            song.sanitize()
            song[key] = value
            lines = format_tags(song).splitlines()
            if not lines:
                return ""
            if len(lines) == 1:
                return lines[0]
            # hackery since title defaults to the filename..
            for l in lines:
                if not l.startswith("Title"):
                    return l

        self.assertEqual(getline("artist", "foo"), "Artist: foo")
        self.assertEqual(getline("genre", "foo\nbar"), "Genre: foo, bar")
        self.assertEqual(getline("artistsort", "foo"), "ArtistSort: foo")
        self.assertEqual(getline("tracknumber", "2/3"), "Track: 2")
        self.assertEqual(getline("discnumber", "2/3"), "Disc: 2")
        self.assertEqual(getline("date", "2009-03-04"), "Date: 2009")
