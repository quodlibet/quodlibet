# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import subprocess
import imp
import shutil
import contextlib
import StringIO
import sys

from tests import TestCase, add, DATA_DIR, mkstemp

import quodlibet
from quodlibet import config
from quodlibet.formats import MusicFile


@contextlib.contextmanager
def capture_output():
    err = StringIO.StringIO()
    out = StringIO.StringIO()
    old_err = sys.stderr
    old_out = sys.stdout
    sys.stderr = err
    sys.stdout = out

    yield (out, err)

    sys.stderr = old_err
    sys.stdout = old_out


def call(args=None):
    path = os.path.join(os.path.dirname(quodlibet.__path__[0]), "operon.py")
    mod = imp.load_source("operon", path)

    with capture_output() as (out, err):
        try:
            return_code = mod.run(["operon.py"] + args)
        except SystemExit, e:
            return_code = e.code

    return (return_code, out.getvalue(), err.getvalue())


class TOperonBase(TestCase):
    def setUp(self):
        config.init()
        self.f = mkstemp(".ogg")[1]
        self.f2 = mkstemp(".mp3")[1]
        shutil.copy(os.path.join(DATA_DIR, 'silence-44-s.ogg'), self.f)
        shutil.copy(os.path.join(DATA_DIR, 'silence-44-s.mp3'), self.f2)
        self.s = MusicFile(self.f)
        self.s2 = MusicFile(self.f2)

    def tearDown(self):
        os.unlink(self.f)
        os.unlink(self.f2)
        config.quit()

    def check_true(self, args, so, se, **kwargs):
        return self._check(args, True, so, se, **kwargs)

    def check_false(self, args, so, se, **kwargs):
        return self._check(args, False, so, se, **kwargs)

    def _check(self, args, success, so, se):
        s, o, e = call(args)
        self.failUnlessEqual(s == 0, success, msg=repr(s))
        self.failUnlessEqual(bool(o), so, msg=repr(o))
        self.failUnlessEqual(bool(e), se, msg=repr(e))
        return o, e


class TOperonMain(TOperonBase):
    # [--version] [--help] [--verbose] <command> [<args>]

    def test_main(self):
        self.check_false([], False, True)
        self.check_true(["help"], True, False)
        self.check_false(["help", "foobar"], False, True)

        # TODO: "image-extract", "rename", "fill", "fill-tracknumber", "edit"
        # "load"
        for sub in ["help", "dump", "copy", "set", "clear",
                    "remove", "add", "list", "print", "info", "tags"]:
            self.check_true(["help", sub], True, False)

        self.check_true(["help", "-h"], True, False)
        self.check_true(["help", "--help"], True, False)
        self.check_false(["help", "--foobar"], False, True)
        self.check_true(["--verbose", "help", "help"], True, False)
        self.check_true(["-v", "help", "help"], True, False)
        self.check_false(["--foobar", "help", "help"], False, True)
        self.check_true(["--version"], True, False)
add(TOperonMain)


class TOperonAdd(TOperonBase):
    # add <tag> <value> <file> [<files>]

    def test_add_misc(self):
        self.check_false(["add"], False, True)
        self.check_false(["add", "tag"], False, True)
        self.check_false(["add", "tag", "value"], False, True)
        self.check_true(["add", "tag", "value", self.f], False, False)
        self.check_true(["add", "tag", "value", self.f, self.f], False, False)

    def test_add_check(self):
        keys = self.s.keys()
        self.check_true(["add", "foo", "bar", self.f], False, False)
        self.s.reload()
        self.failUnlessEqual(self.s["foo"], "bar")
        self.failUnlessEqual(len(keys) + 1, len(self.s.keys()))

        self.check_true(["-v", "add", "foo", "bar2", self.f], False, True)
        self.s.reload()
        self.failUnlessEqual(set(self.s.list("foo")), set(["bar", "bar2"]))

    def test_add_backlisted(self):
        self.check_false(["add", "playcount", "bar", self.f], False, True)

    def test_permissions(self):
        os.chmod(self.f, 0000)
        self.check_false(["add", "foo", "bar", self.f, self.f],
                         False, True)
        os.chmod(self.f, 0444)
        self.check_false(["add", "foo", "bar", self.f, self.f], False, True)
add(TOperonAdd)


class TOperonPrint(TOperonBase):
    # [-p <pattern>] <file> [<files>]

    def test_print(self):
        self.check_false(["print"], False, True)
        o, e = self.check_true(["print", self.f], True, False)
        self.failUnlessEqual(o.splitlines()[0],
            "piman, jzig - Quod Libet Test Data - 02/10 - Silence")

        o, e = self.check_true(["print", "-p", "<title>", self.f], True, False)
        self.failUnlessEqual(o.splitlines()[0], "Silence")

        o, e = self.check_true(["print", "-p", "<title>", self.f, self.f],
                               True, False)
        self.failUnlessEqual(o.splitlines(), ["Silence", "Silence"])

    def test_permissions(self):
        os.chmod(self.f, 0000)
        self.check_false(["print", "-p", "<title>", self.f],
                         False, True)
add(TOperonPrint)


class TOperonRemove(TOperonBase):
    # [--dry-run] <tag> [-e <pattern> | <value>] <file> [<files>]

    def test_error(self):
        self.check_false(["remove"], False, True)
        self.check_false(["remove", "tag", "value"], False, True)

    def test_remove(self):
        self.s["test"] = "foo\nbar\nfoo"
        self.s.write()

        self.check_true(["remove", "tag", "value", self.f], False, False)

        self.check_true(["remove", "test", "foo", self.f], False, False)
        self.s.reload()
        self.failUnlessEqual(self.s["test"], "bar")

        self.check_true(["-v", "remove", "test", "xxx", self.f, self.f],
                        False, True)

        self.s.reload()
        self.failUnlessEqual(self.s["test"], "bar")

    def test_dry_run(self):
        self.s["test"] = "foo\nbar\nfoo"
        self.s.write()
        self.check_true(["remove", "--dry-run", "test", "foo", self.f],
                        False, True)
        self.s.reload()
        self.failUnlessEqual(len(self.s.list("test")), 3)

    def test_pattern(self):
        self.s["test"] = "fao\nbar\nfoo"
        self.s.write()
        self.check_true(["remove", "test", "-e", "f[ao]o", self.f],
                        False, False)
        self.s.reload()
        self.failUnlessEqual(self.s.list("test"), ["bar"])

        self.check_true(["-v", "remove", "test", "-e", ".*", self.f],
                        False, True)
        self.s.reload()
        self.failIf(self.s.list("test"))

add(TOperonRemove)


class TOperonClear(TOperonBase):
    # [--dry-run] [-a | -e <pattern> | <tag>] <file> [<files>]

    def test_misc(self):
        self.check_false(["clear"], False, True)
        self.check_false(["clear", self.f], False, True)
        self.check_true(["clear", "-a", self.f], False, False)
        self.check_false(["-v", "clear", "-e", self.f], False, True)
        self.check_true(["-v", "clear", "-e", "xx", self.f], False, True)
        self.check_true(["clear", "-e", "xx", self.f], False, False)
        self.check_false(["clear", "-e", "x", "-a", self.f], False, True)

    def _test_all(self):
        self.check(["clear", "-a", self.f], True, output=False)
        self.s.reload()
        self.failIf(self.s.realkeys())
        self.check(["clear", "-a", self.f, self.f], True, output=False)

    def _test_all_dry_run(self):
        old_len = len(self.s.realkeys())
        self.failUnless(old_len)
        self.check(["clear", "-a", "--dry-run", self.f], True)
        self.s.reload()
        self.failUnlessEqual(len(self.s.realkeys()), old_len)

    def _test_pattern(self):
        old_len = len(self.s.realkeys())
        self.check(["clear", "-e", "a.*", self.f], True, output=False)
        self.s.reload()
        self.failUnlessEqual(len(self.s.realkeys()), old_len - 2)

    def _test_simple(self):
        old_len = len(self.s.realkeys())
        self.check(["clear", "a.*", self.f], True, output=False)
        self.s.reload()
        self.failUnlessEqual(len(self.s.realkeys()), old_len)

        self.check(["clear", "--dry-run", "artist", self.f], True)
        self.s.reload()
        self.failUnlessEqual(len(self.s.realkeys()), old_len)

        self.check(["clear", "artist", self.f], True, output=False)
        self.s.reload()
        self.failUnlessEqual(len(self.s.realkeys()), old_len - 1)
add(TOperonClear)


class TOperonSet(TOperonBase):
    # [--dry-run] <tag> <value> <file> [<files>]

    def test_misc(self):
        self.check_false(["set"], False, True)
        self.check_true(["set", "-h"], True, False)
        self.check_false(["set", "tag", "value"], False, True)
        self.check_true(["set", "tag", "value", self.f], False, False)
        self.check_true(["set", "tag", "value", self.f, self.f], False, False)
        self.check_true(["set", "--dry-run", "tag", "value", self.f],
                        False, False)

    def test_simple(self):
        self.check_true(["set", "foo", "bar", self.f], False, False)
        self.s.reload()
        self.failUnlessEqual(self.s["foo"], "bar")

        self.check_true(["set", "--dry-run", "foo", "x", self.f], False, False)
        self.s.reload()
        self.failUnlessEqual(self.s["foo"], "bar")

    def test_replace(self):
        self.failIfEqual(self.s["artist"], "foobar")
        self.check_true(["set", "artist", "foobar", self.f], False, False)
        self.s.reload()
        self.failUnlessEqual(self.s["artist"], "foobar")
add(TOperonSet)


class TOperonDump(TOperonBase):
    def test_misc(self):
        self.check_true(["dump", "-h"], True, False)
        self.check_false(["dump"], False, True)
        self.check_true(["dump", self.f], True, False)
        self.check_true(["-v", "dump", self.f], True, True)
        self.check_false(["dump", self.f, self.f], False, True)

    def test_output(self):
        o, e = self.check_true(["dump", self.f], True, False)
        internal = filter(lambda x: x.startswith("~"), o.splitlines())
        self.failIf(internal)
add(TOperonDump)


class TOperonCopy(TOperonBase):
    # [--dry-run] [--ignore-errors] <source> <dest>

    def test_misc(self):
        self.check_false(["copy"], False, True)
        self.check_true(["copy", "-h"], True, False)
        self.check_false(["copy", "foo"], False, True)
        self.check_true(["copy", self.f, self.f2], False, False)
        self.check_true(["-v", "copy", self.f, self.f2], False, True)

    def test_simple(self):
        map(self.s2.__delitem__, self.s2.realkeys())
        self.s2.write()
        self.s2.reload()
        self.failIf(self.s2.realkeys())
        self.check_true(["copy", self.f, self.f2], False, False)
        self.s2.reload()
        self.failUnless(self.s2.realkeys())

    def test_not_changable(self):
        self.s2["rating"] = "foo"
        self.s2.write()
        self.check_false(["copy", self.f2, self.f], False, True)
        self.check_true(["copy", "--ignore-errors", self.f2, self.f],
                        False, False)

    def test_add(self):
        self.failUnlessEqual(len(self.s2.list("genre")), 1)
        self.check_true(["copy", self.f, self.f2], False, False)
        self.s2.reload()
        self.failUnlessEqual(len(self.s2.list("genre")), 2)

    def test_dry_run(self):
        map(self.s2.__delitem__, self.s2.realkeys())
        self.s2.write()
        self.s2.reload()
        self.check_true(["copy", "--dry-run", self.f, self.f2], False, True)
        self.s2.reload()
        self.failIf(self.s2.realkeys())
add(TOperonCopy)


class TOperonInfo(TOperonBase):
    # [-t] [-c <c1>,<c2>...] <file>

    def test_misc(self):
        self.check_false(["info"], False, True)
        self.check_true(["info", self.f], True, False)
        self.check_false(["info", self.f, self.f2], False, True)
        self.check_true(["info", "-h"], True, False)

    def test_normal(self):
        self.check_true(["info", "-cdesc", self.f], True, False)
        self.check_true(["info", "-cvalue", self.f], True, False)
        self.check_true(["info", "-cdesc,value", self.f], True, False)
        self.check_true(["info", "-cvalue, desc", self.f], True, False)
        self.check_false(["info", "-cfoo", self.f], False, True)

    def test_terse(self):
        self.check_true(["info", "-t", self.f], True, False)
        self.check_true(["info", "-t", "-cdesc", self.f], True, False)
        self.check_true(["info", "-t", "-cvalue", self.f], True, False)
        self.check_true(["info", "-t", "-cdesc,value", self.f], True, False)
        self.check_true(["info", "-t", "-cvalue, desc", self.f], True, False)
        self.check_false(["info", "-t", "-cfoo", self.f], False, True)
add(TOperonInfo)


class TOperonList(TOperonBase):
    # [-t] [-c <c1>,<c2>...] <file>

    def test_misc(self):
        self.check_true(["list", "-h"], True, False)
        self.check_false(["list"], False, True)
        self.check_true(["list", self.f], True, False)
        self.check_false(["list", self.f, self.f2], False, True)

    def test_normal(self):
        self.check_true(["list", "-cdesc", self.f], True, False)
        self.check_true(["list", "-cvalue,tag", self.f], True, False)
        self.check_true(["list", "-cdesc,value", self.f], True, False)
        self.check_true(["list", "-cvalue, desc", self.f], True, False)
        self.check_false(["list", "-cfoo", self.f], False, True)

    def test_terse(self):
        self.check_true(["list", "-t", self.f], True, False)
        self.check_true(["list", "-t", "-cdesc", self.f], True, False)
        self.check_true(["list", "-t", "-cvalue,tag", self.f], True, False)
        self.check_true(["list", "-t", "-cdesc,value", self.f], True, False)
        self.check_true(["list", "-t", "-cvalue, desc", self.f], True, False)
        self.check_false(["list", "-t", "-cfoo", self.f], False, True)

    def test_terse_escape(self):
        self.s["foobar"] = "a:bc\\:"
        self.s.write()
        d = self.check_true(["list", "-t", "-cvalue", self.f], True, False)[0]
        lines = d.splitlines()
        self.assertTrue("a\\:bc\\\\\\:" in lines)
add(TOperonList)


class TOperonTags(TOperonBase):
    # [-t] [-c <c1>,<c2>...]

    def test_misc(self):
        self.check_true(["tags", "-h"], True, False)
        self.check_false(["tags", self.f], False, True)
        self.check_false(["tags", self.f, self.f2], False, True)

    def test_normal(self):
        self.check_true(["tags", "-cdesc"], True, False)
        self.check_true(["tags", "-ctag"], True, False)
        self.check_true(["tags", "-ctag, desc"], True, False)
        self.check_false(["tags", "-cfoo"], False, True)

    def test_terse(self):
        self.check_true(["tags", "-t"], True, False)
        self.check_true(["tags", "-t", "-cdesc"], True, False)
        self.check_true(["tags", "-t", "-cdesc,tag"], True, False)
        self.check_true(["tags", "-t", "-ctag, desc"], True, False)
        self.check_false(["tags", "-t", "-cfoo"], False, True)
add(TOperonTags)


class TOperonImageExtract(TOperonBase):
    # [--dry-run] [--primary] [-d <destination>] <file> [<files>]

    def setUp(self):
        super(TOperonImageExtract, self).setUp()

        self.fcover = mkstemp(".wma")[1]
        shutil.copy(os.path.join(DATA_DIR, 'test-2.wma'), self.fcover)
        self.cover = MusicFile(self.fcover)

    def tearDown(self):
        os.unlink(self.fcover)

        super(TOperonImageExtract, self).tearDown()

    def test_misc(self):
        self.check_true(["image-extract", "-h"], True, False)
        self.check_true(["image-extract", self.f], False, False)
        self.check_true(["image-extract", self.f, self.f2], False, False)
        self.check_false(["image-extract"], False, True)

    def test_extract_all(self):
        target_dir = os.path.dirname(self.fcover)
        self.check_true(["image-extract", "-d", target_dir, self.fcover],
                        False, False)

        self.assertEqual(len(self.cover.get_images()), 1)
        image = self.cover.get_primary_image()

        name = os.path.splitext(os.path.basename(self.fcover))[0]

        expected = "%s-00.%s" % (name, image.extensions[0])
        expected_path = os.path.join(target_dir, expected)

        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "rb") as h:
            self.assertEqual(h.read(), image.file.read())

    def test_extract_primary(self):
        target_dir = os.path.dirname(self.fcover)
        self.check_true(
            ["image-extract", "-d", target_dir, "--primary", self.fcover],
            False, False)

        self.assertEqual(len(self.cover.get_images()), 1)
        image = self.cover.get_primary_image()

        name = os.path.splitext(os.path.basename(self.fcover))[0]

        expected = "%s.%s" % (name, image.extensions[0])
        expected_path = os.path.join(target_dir, expected)

        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "rb") as h:
            self.assertEqual(h.read(), image.file.read())

add(TOperonImageExtract)
