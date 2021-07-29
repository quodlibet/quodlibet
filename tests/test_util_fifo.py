# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from unittest import mock

from gi.repository import GLib
from quodlibet import print_d
from quodlibet.util import is_windows
from tests import TestCase, skipIf

from quodlibet.util.fifo import split_message, FIFO, fifo_exists, write_fifo
from tests.helper import temp_filename


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


@skipIf(is_windows(), "not on Windows")
class TFIFO(TestCase):

    def test_creation_destruction(self):

        def cb(bs, _):
            print_d(bs)

        with temp_filename() as fn:
            fifo = FIFO(fn, cb)
            self.failIf(fifo_exists(fifo._path))
            fifo.open()
            self.failUnless(fifo_exists(fifo._path))
        # Should *not* error if file is gone
        fifo.destroy()

    def test_unwriteable_location(self):
        fifo = FIFO("/dev/not-here", None)
        fifo.open()
        with self.assertRaises(OSError):
            write_fifo(fifo._path, "foobar".encode())
        fifo.destroy()

    def test_empty_read(self):
        result = []

        with temp_filename() as f, mock.patch.object(FIFO, "open") as m_open:
            fifo = FIFO(f, result.append)
            source = mock.Mock()
            source.read.return_value = b""
            assert fifo._process(source, GLib.IO_IN) is False
            assert m_open.mock_calls == [mock.call(ignore_lock=True)]
            assert result == []

    def test_glib_err_read(self):
        result = []

        with temp_filename() as f, mock.patch.object(FIFO, "open") as m_open:
            fifo = FIFO(f, result.append)
            source = mock.Mock()
            assert fifo._process(source, GLib.IO_ERR) is False
            assert m_open.mock_calls == [mock.call(ignore_lock=True)]
            assert result == []

    def test_oserror_read(self):
        result = []

        with temp_filename() as f, mock.patch.object(FIFO, "open") as m_open:
            fifo = FIFO(f, result.append)
            source = mock.Mock()
            source.read.side_effect = OSError
            assert fifo._process(source, GLib.IO_IN) is False
            assert m_open.mock_calls == [mock.call(ignore_lock=True)]
            assert result == []

    def test_successful_read(self):
        result = []

        with temp_filename() as f, mock.patch.object(FIFO, "open") as m_open:
            fifo = FIFO(f, result.append)
            source = mock.Mock()
            source.read.return_value = b"foo"
            assert fifo._process(source, GLib.IO_IN) is True
            assert m_open.mock_calls == []
            assert result == [b"foo"]
