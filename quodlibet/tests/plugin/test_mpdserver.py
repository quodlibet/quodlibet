# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.


from tests.plugin import PluginTestCase


class TMPDServer(PluginTestCase):

    def setUp(self):
        self.mpd_server = self.modules["mpd_server"]

    def test_parse_command(self):
        parse = self.mpd_server.parse_command

        self.assertEqual(parse("foo bar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\tbar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\t bar"), ("foo", ["bar"]))
        self.assertEqual(parse("foo\t bar quux"), ("foo", ["bar", "quux"]))
        self.assertEqual(
            parse("foo\t bar \"q 2\" x"), ("foo", ["bar", "q 2", "x"]))
        self.assertEqual(parse("foo 'bar  quux'"), ("foo", ["'bar", "quux'"]))
        self.assertEqual(
            parse("foo \xc3\xb6\xc3\xa4\xc3\xbc"), ("foo", [u"\xf6\xe4\xfc"]))
