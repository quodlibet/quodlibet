# -*- coding: utf-8 -*-
import os
import unittest
from tests import TestCase

from quodlibet.util.path import pathname2url_win32, iscommand, limit_path, \
    fsnative, is_fsnative, get_home_dir

is_win = os.name == "nt"
path_set = bool(os.environ.get('PATH', False))


class Tpathname2url(TestCase):
    def test_win(self):
        cases = {
            r"c:\abc\def": "/c:/abc/def",
            r"C:\a b\c.txt": "/C:/a%20b/c.txt",
            r"\\xy\z.txt": "//xy/z.txt",
            r"C:\a:b\c:d": "/C:/a%3Ab/c%3Ad",
            r"\\server\share\foo": "//server/share/foo",
            }
        p2u = pathname2url_win32
        for inp, should in cases.iteritems():
            self.failUnlessEqual(p2u(inp), should)


class Tget_x_dir(TestCase):

    def test_get_home_dir(self):
        self.assertTrue(is_fsnative(get_home_dir()))
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
        self.assertTrue(is_fsnative(new))
        self.assertEqual(len(new), 255)
        self.assertTrue(new.endswith(fsnative(u"xx.ext")))

        new = limit_path(path)
        self.assertTrue(is_fsnative(new))
        self.assertEqual(len(new), 255)
        self.assertTrue(new.endswith(fsnative(u"...ext")))

        self.assertTrue(is_fsnative(limit_path(fsnative())))
        self.assertEqual(limit_path(fsnative()), fsnative())


class Tiscommand(TestCase):

    @unittest.skipIf(is_win, "Unix only")
    def test_unix(self):
        self.failUnless(iscommand("ls"))
        self.failUnless(iscommand("/bin/ls"))
        self.failUnless(iscommand("pidof"))

    def test_both(self):
        self.failIf(iscommand("zzzzzzzzz"))
        self.failIf(iscommand("/bin/zzzzzzzzz"))
        self.failIf(iscommand(""))
        self.failIf(iscommand("/bin"))
        self.failIf(iscommand("X11"))

    @unittest.skipUnless(path_set, "Can only test with a valid $PATH")
    def test_looks_in_path(self):
        path_dirs = set(os.environ['PATH'].split(os.path.pathsep))
        dirs = path_dirs - set(os.defpath.split(os.path.pathsep))
        for d in dirs:
            if os.path.isdir(d):
                for file_path in os.listdir(d):
                    if os.access(os.path.join(d, file_path), os.X_OK):
                        print_d("Testing %s" % file_path)
                        self.failUnless(iscommand(file_path))
                        return
