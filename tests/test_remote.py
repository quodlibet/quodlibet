# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from senf import fsn2bytes, bytes2fsn

from . import TestCase, skipIf
from .helper import temp_filename

from quodlibet.remote import QuodLibetUnixRemote
from quodlibet.util import is_windows


class Mock:
    def __init__(self, resp=None):
        self.lines = []
        self.resp = resp

    def handle_line(self, app, line):
        self.lines.append(line)
        return self.resp


@skipIf(is_windows(), "unix only")
class TUnixRemote(TestCase):

    def test_fifo(self):
        mock = Mock()
        remote = QuodLibetUnixRemote(None, mock)
        remote._callback(b"foo\n")
        remote._callback(b"bar\nbaz")
        self.assertEqual(
            mock.lines, [bytes2fsn(b, None) for b in [b"foo", b"bar", b"baz"]])

    def test_response(self):
        with temp_filename() as fn:
            mock = Mock(resp=bytes2fsn(b"resp", None))
            remote = QuodLibetUnixRemote(None, mock)
            remote._callback(b"\x00foo\x00" + fsn2bytes(fn, None) + b"\x00")
            self.assertEqual(mock.lines, [bytes2fsn(b"foo", None)])
            with open(fn, "rb") as h:
                self.assertEqual(h.read(), b"resp")
