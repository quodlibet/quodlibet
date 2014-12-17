import os
import unittest
from tests import TestCase

from quodlibet.util.path import pathname2url_win32, iscommand

is_win = os.name == "nt"
path_set = bool(os.environ.get('PATH', False))


class Tpathname2url(TestCase):
    def test_win(self):
        cases = {
            r"c:\abc\def": "/c:/abc/def",
            r"C:\a b\c.txt": "/C:/a%20b/c.txt",
            r"\\xy\z.txt": "xy/z.txt",
            r"C:\a:b\c:d": "/C:/a%3Ab/c%3Ad"
            }
        p2u = pathname2url_win32
        for inp, should in cases.iteritems():
            self.failUnlessEqual(p2u(inp), should)


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
