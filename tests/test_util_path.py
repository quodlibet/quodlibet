# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
import unittest

from senf import uri2fsn, fsn2uri, fsnative

from quodlibet.util.path import iscommand, limit_path, \
    get_home_dir, uri_is_valid, is_hidden, uri2gsturi
from quodlibet.util import print_d

from . import TestCase, skipIf

is_win = os.name == "nt"
path_set = bool(os.environ.get("PATH", False))


def test_uri2gsturi():
    assert uri2gsturi("file:///foo/bar") == "file:///foo/bar"
    if is_win:
        assert uri2gsturi("file://foo/bar") == "file:////foo/bar"
    assert uri2gsturi("https://foo.bar.org") == "https://foo.bar.org"


class Tishidden(TestCase):

    @skipIf(is_win, "unix-like hidden")
    def test_leading_dot(self):
        assert is_hidden(fsnative("."))
        assert is_hidden(fsnative("foo/.bar"))

    def test_normal_names_not_hidden(self):
        assert not is_hidden(fsnative("foo"))
        assert not is_hidden(fsnative(".foo/bar"))

    def test_multiple_dots(self):
        assert not is_hidden(fsnative("...and Justice For All.flac"))


class Turi(TestCase):

    def test_uri2fsn(self):
        if os.name != "nt":
            path = uri2fsn("file:///home/piman/cr%21azy")
            assert isinstance(path, fsnative)
            self.assertEqual(path, fsnative("/home/piman/cr!azy"))
        else:
            path = uri2fsn("file:///C:/foo")
            assert isinstance(path, fsnative)
            self.assertEqual(path, fsnative("C:\\foo"))

    def test_uri2fsn_invalid(self):
        self.assertRaises(ValueError, uri2fsn, "http://example.com")

    def test_path_as_uri(self):
        if os.name != "nt":
            self.assertRaises(ValueError, uri2fsn, "/foo")
        else:
            self.assertRaises(ValueError, uri2fsn, "C:\\foo")

    def test_fsn2uri(self):
        if os.name != "nt":
            uri = fsn2uri(fsnative("/öäü.txt"))
            self.assertEqual(uri, "file:///%C3%B6%C3%A4%C3%BC.txt")
        else:
            uri = fsn2uri(fsnative("C:\\öäü.txt"))
            self.assertEqual(
                uri, "file:///C:/%C3%B6%C3%A4%C3%BC.txt")
            self.assertEqual(
                fsn2uri("C:\\SomeDir\xe4"), "file:///C:/SomeDir%C3%A4")

    def test_roundtrip(self):
        if os.name == "nt":
            paths = ["C:\\öäü.txt"]
        else:
            paths = ["/öäü.txt", "/a/foo/bar", "/a/b/foo/bar"]

        for source in paths:
            path = uri2fsn(fsn2uri(fsnative(source)))
            assert isinstance(path, fsnative)
            self.assertEqual(path, fsnative(source))

    def test_win_unc_path(self):
        if os.name == "nt":
            self.assertEqual(
                fsn2uri("\\\\server\\share\\path"),
                "file://server/share/path")

    def test_uri_is_valid(self):
        assert uri_is_valid("file:///foo")
        assert uri_is_valid("file:///C:/foo")
        assert uri_is_valid("http://www.example.com")

        assert not uri_is_valid("/bla")
        assert not uri_is_valid("test")
        assert not uri_is_valid("")

        assert not uri_is_valid("file:///öäü")
        assert not uri_is_valid("file:///öäü".encode())


class Tget_x_dir(TestCase):

    def test_get_home_dir(self):
        assert isinstance(get_home_dir(), fsnative)
        assert os.path.isabs(get_home_dir())


class Tlimit_path(TestCase):

    def test_main(self):
        if os.name == "nt":
            path = "C:\\foobar\\ä{}\\{}".format("x" * 300, "x" * 300)
            path = limit_path(path)
            self.assertEqual(len(path), 3 + 6 + 1 + 255 + 1 + 255)
        else:
            path = "/foobar/ä{}/{}".format("x" * 300, "x" * 300)
            path = limit_path(path)
            self.assertEqual(len(path), 1 + 6 + 1 + 255 + 1 + 255)

        path = fsnative("foo%s.ext" % ("x" * 300))
        new = limit_path(path, ellipsis=False)
        assert isinstance(new, fsnative)
        self.assertEqual(len(new), 255)
        assert new.endswith(fsnative("xx.ext"))

        new = limit_path(path)
        assert isinstance(new, fsnative)
        self.assertEqual(len(new), 255)
        assert new.endswith(fsnative("...ext"))

        assert isinstance(limit_path(fsnative()), fsnative)
        self.assertEqual(limit_path(fsnative()), fsnative())


class Tiscommand(TestCase):

    @unittest.skipIf(is_win, "Unix only")
    def test_unix(self):
        assert iscommand("ls")
        assert iscommand(shutil.which("ls"))
        assert iscommand("whoami")

    def test_both(self):
        assert not iscommand("zzzzzzzzz")
        assert not iscommand("/bin/zzzzzzzzz")
        assert not iscommand("")
        assert not iscommand("/bin")
        assert not iscommand("X11")

    @unittest.skipUnless(path_set, "Can only test with a valid $PATH")
    @unittest.skipIf(is_win, "needs porting")
    def test_looks_in_path(self):
        path_dirs = set(os.environ["PATH"].split(os.path.pathsep))
        dirs = path_dirs - set(os.defpath.split(os.path.pathsep))
        for d in dirs:
            if os.path.isdir(d):
                for file_path in sorted(os.listdir(d)):
                    p = os.path.join(d, file_path)
                    if os.path.isfile(p) and os.access(p, os.X_OK):
                        print_d("Testing %s" % p)
                        assert iscommand(p), p
                        return
