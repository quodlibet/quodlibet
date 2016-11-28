# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.util.fifo import split_message


class Tsplit_message(TestCase):

    def test_main(self):
        func = lambda d: list(split_message(d))

        # no response format
        self.assertEqual(func(b""), [])
        self.assertEqual(func(b"foo"), [(b"foo", None)])
        self.assertEqual(func(b"foo\nbar"), [(b"foo", None), (b"bar", None)])

        # response format
        self.assertEqual(func(b"\x00a\x00/dev/null\x00"),
                         [(b"a", b"/dev/null")])
        self.assertEqual(func(b"\x00a\x00/dev/null\x00\x00b\x00/dev/foo\x00"),
                         [(b"a", b"/dev/null"), (b"b", b"/dev/foo")])

        # mixed
        self.assertEqual(func(b"foo\x00a\x00/dev\x00"),
                         [(b"foo", None), (b"a", b"/dev")])
        self.assertEqual(func(b"\x00a\x00/dev\x00foo"),
                         [(b"a", b"/dev"), (b"foo", None)])
        self.assertEqual(func(b"\x00a\x00/dev\x00foo\x00b\x00/arg\x00bla"),
                         [(b"a", b"/dev"), (b"foo", None), (b"b", b"/arg"),
                          (b"bla", None)])

        # inval
        self.assertRaises(ValueError, func, b"foo\x00bar")
