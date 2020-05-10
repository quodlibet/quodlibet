# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
import unittest

from senf import uri2fsn, fsn2uri, fsnative, environ

from quodlibet.util.path import iscommand, limit_path, \
    get_home_dir, uri_is_valid, ishidden, uri2gsturi
from quodlibet.util import print_d

from . import TestCase


is_win = os.name == "nt"
path_set = bool(environ.get('PATH', False))


def test_uri2gsturi():
    assert uri2gsturi("file:///foo/bar") == "file:///foo/bar"
    if is_win:
        assert uri2gsturi("file://foo/bar") == "file:////foo/bar"
    assert uri2gsturi("https://foo.bar.org") == "https://foo.bar.org"


class Tishidden(TestCase):

    def test_main(self):
        assert ishidden(fsnative(u"."))
        assert ishidden(fsnative(u"foo/.bar"))
        assert not ishidden(fsnative(u".foo/bar"))
        assert not ishidden(fsnative(u"foo"))


class Turi(TestCase):

    def test_uri2fsn(self):
        if os.name != "nt":
            path = uri2fsn("file:///home/piman/cr%21azy")
            self.assertTrue(isinstance(path, fsnative))
            self.assertEqual(path, fsnative(u"/home/piman/cr!azy"))
        else:
            path = uri2fsn("file:///C:/foo")
            self.assertTrue(isinstance(path, fsnative))
            self.assertEqual(path, fsnative(u"C:\\foo"))

    def test_uri2fsn_invalid(self):
        self.assertRaises(ValueError, uri2fsn, "http://example.com")

    def test_path_as_uri(self):
        if os.name != "nt":
            self.assertRaises(ValueError, uri2fsn, "/foo")
        else:
            self.assertRaises(ValueError, uri2fsn, u"C:\\foo")

    def test_fsn2uri(self):
        if os.name != "nt":
            uri = fsn2uri(fsnative(u"/öäü.txt"))
            self.assertEqual(uri, u"file:///%C3%B6%C3%A4%C3%BC.txt")
        else:
            uri = fsn2uri(fsnative(u"C:\\öäü.txt"))
            self.assertEqual(
                uri, "file:///C:/%C3%B6%C3%A4%C3%BC.txt")
            self.assertEqual(
                fsn2uri(u"C:\\SomeDir\xe4"), "file:///C:/SomeDir%C3%A4")

    def test_roundtrip(self):
        if os.name == "nt":
            paths = [u"C:\\öäü.txt"]
        else:
            paths = [u"/öäü.txt", u"/a/foo/bar", u"/a/b/foo/bar"]

        for source in paths:
            path = uri2fsn(fsn2uri(fsnative(source)))
            self.assertTrue(isinstance(path, fsnative))
            self.assertEqual(path, fsnative(source))

    def test_win_unc_path(self):
        if os.name == "nt":
            self.assertEqual(
                fsn2uri(u"\\\\server\\share\\path"),
                u"file://server/share/path")

    def test_uri_is_valid(self):
        self.assertTrue(uri_is_valid(u"file:///foo"))
        self.assertTrue(uri_is_valid(u"file:///C:/foo"))
        self.assertTrue(uri_is_valid(u"http://www.example.com"))

        self.assertFalse(uri_is_valid(u"/bla"))
        self.assertFalse(uri_is_valid(u"test"))
        self.assertFalse(uri_is_valid(u""))

        assert not uri_is_valid(u"file:///öäü")
        assert not uri_is_valid(u"file:///öäü".encode("utf-8"))


class Tget_x_dir(TestCase):

    def test_get_home_dir(self):
        self.assertTrue(isinstance(get_home_dir(), fsnative))
        self.assertTrue(os.path.isabs(get_home_dir()))


class Tlimit_path(TestCase):

    def test_main(self):
        if os.name == "nt":
            path = u'C:\\foobar\\ä%s\\%s' % ("x" * 300, "x" * 300)
            path = limit_path(path)
            self.failUnlessEqual(len(path), 3 + 6 + 1 + 255 + 1 + 255)
        else:
            path = '/foobar/ä%s/%s' % ("x" * 300, "x" * 300)
            path = limit_path(path)
            self.failUnlessEqual(len(path), 1 + 6 + 1 + 255 + 1 + 255)

        path = fsnative(u"foo%s.ext" % (u"x" * 300))
        new = limit_path(path, ellipsis=False)
        self.assertTrue(isinstance(new, fsnative))
        self.assertEqual(len(new), 255)
        self.assertTrue(new.endswith(fsnative(u"xx.ext")))

        new = limit_path(path)
        self.assertTrue(isinstance(new, fsnative))
        self.assertEqual(len(new), 255)
        self.assertTrue(new.endswith(fsnative(u"...ext")))

        self.assertTrue(isinstance(limit_path(fsnative()), fsnative))
        self.assertEqual(limit_path(fsnative()), fsnative())


class Tiscommand(TestCase):

    @unittest.skipIf(is_win, "Unix only")
    def test_unix(self):
        self.failUnless(iscommand("ls"))
        self.failUnless(iscommand(shutil.which("ls")))
        self.failUnless(iscommand("whoami"))

    def test_both(self):
        self.failIf(iscommand("zzzzzzzzz"))
        self.failIf(iscommand("/bin/zzzzzzzzz"))
        self.failIf(iscommand(""))
        self.failIf(iscommand("/bin"))
        self.failIf(iscommand("X11"))

    @unittest.skipUnless(path_set, "Can only test with a valid $PATH")
    @unittest.skipIf(is_win, "needs porting")
    def test_looks_in_path(self):
        path_dirs = set(environ['PATH'].split(os.path.pathsep))
        dirs = path_dirs - set(os.defpath.split(os.path.pathsep))
        for d in dirs:
            if os.path.isdir(d):
                for file_path in sorted(os.listdir(d)):
                    p = os.path.join(d, file_path)
                    if os.path.isfile(p) and os.access(p, os.X_OK):
                        print_d("Testing %s" % p)
                        self.failUnless(iscommand(p), msg=p)
                        return
