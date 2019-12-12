# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

from senf import fsnative, path2fsn, environ

from tests import TestCase, get_data_path, mkstemp
from .helper import capture_output, get_temp_copy

from quodlibet import config
from quodlibet.formats import MusicFile
from quodlibet.operon.main import main as operon_main


def call(args):
    args = [path2fsn(a) for a in args]
    with capture_output() as (out, err):
        try:
            return_code = operon_main([path2fsn("operon.py")] + args)
        except SystemExit as e:
            return_code = e.code

    return (return_code, out.getvalue(), err.getvalue())


class TOperonBase(TestCase):
    def setUp(self):
        config.init()

        self.f = get_temp_copy(get_data_path('silence-44-s.ogg'))
        self.f2 = get_temp_copy(get_data_path('silence-44-s.mp3'))
        self.s = MusicFile(self.f)
        self.s2 = MusicFile(self.f2)

        fd, self.f3 = mkstemp(".mp3")
        os.write(fd, b"garbage")
        os.close(fd)

    def tearDown(self):
        os.unlink(self.f)
        os.unlink(self.f2)
        os.unlink(self.f3)
        config.quit()

    def check_true(self, args, so, se, **kwargs):
        """Assert success status code"""

        return self._check(args, True, so, se, **kwargs)

    def check_false(self, args, so, se, **kwargs):
        """Assert error status code"""

        return self._check(args, False, so, se, **kwargs)

    def _check(self, args, success, so, se):
        s, o, e = call(args)
        self.failUnlessEqual(s == 0, success, msg=repr((s, o, e)))
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
        for sub in ["help", "copy", "set", "clear",
                    "remove", "add", "list", "print", "info", "tags"]:
            self.check_true(["help", sub], True, False)

        self.check_true(["help", "-h"], True, False)
        self.check_true(["help", "--help"], True, False)
        self.check_false(["help", "--foobar"], False, True)
        self.check_true(["--verbose", "help", "help"], True, False)
        self.check_true(["-v", "help", "help"], True, False)
        self.check_false(["--foobar", "help", "help"], False, True)
        self.check_true(["--version"], True, False)


class TOperonAdd(TOperonBase):
    # add <tag> <value> <file> [<files>]

    def test_add_misc(self):
        self.check_false(["add"], False, True)
        self.check_false(["add", "tag"], False, True)
        self.check_false(["add", "tag", "value"], False, True)
        self.check_true(["add", "tag", "value", self.f], False, False)
        self.check_true(["add", "tag", "value", self.f, self.f], False, False)

    def test_add_check(self):
        keys = list(self.s.keys())
        self.check_true(["add", "foo", "bar", self.f], False, False)
        self.s.reload()
        self.failUnlessEqual(self.s["foo"], "bar")
        self.failUnlessEqual(len(keys) + 1, len(self.s.keys()))

        self.check_true(["-v", "add", "foo", "bar2", self.f], False, True)
        self.s.reload()
        self.failUnlessEqual(set(self.s.list("foo")), {"bar", "bar2"})

    def test_add_backlisted(self):
        self.check_false(["add", "playcount", "bar", self.f], False, True)

    def test_permissions(self):
        try:
            os.chmod(self.f, 0o000)
            self.check_false(["add", "foo", "bar", self.f, self.f],
                             False, True)
            os.chmod(self.f, 0o444)
            self.check_false(["add", "foo", "bar", self.f, self.f],
                             False, True)
        finally:
            os.chmod(self.f, 0o666)


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

    def test_print_invalid(self):
        # passing a song which can't be loaded results in fail
        self.check_false(["print", self.f3], False, True)

        # in case some fail and some don't, print the error messages for
        # the failed ones, the patterns for the working ones and return
        # an error status
        o, e = self.check_false(["print", self.f3, self.f2], True, True)
        self.assertTrue("Quod Libet Test Data" in o)

    def test_permissions(self):
        # doesn't prevent reading under wine..
        if os.name == "nt":
            return
        os.chmod(self.f, 0o000)
        self.check_false(["print", "-p", "<title>", self.f],
                         False, True)


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


class TOperonCopy(TOperonBase):
    # [--dry-run] [--ignore-errors] <source> <dest>

    def test_misc(self):
        self.check_false(["copy"], False, True)
        self.check_true(["copy", "-h"], True, False)
        self.check_false(["copy", "foo"], False, True)
        self.check_true(["copy", self.f, self.f2], False, False)
        self.check_true(["-v", "copy", self.f, self.f2], False, True)

    def test_simple(self):
        for key in self.s2.realkeys():
            del self.s2[key]
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
        for key in self.s2.realkeys():
            del self.s2[key]
        self.s2.write()
        self.s2.reload()
        self.check_true(["copy", "--dry-run", self.f, self.f2], False, True)
        self.s2.reload()
        self.failIf(self.s2.realkeys())


class TOperonEdit(TOperonBase):
    # [--dry-run] <file>

    def test_misc(self):
        self.check_false(["edit"], False, True)
        self.check_true(["edit", "-h"], True, False)
        self.check_false(["edit", "foo", "bar"], False, True)

    def test_nonexist_editor(self):
        editor = fsnative(u"/this/path/does/not/exist/hopefully")
        environ["VISUAL"] = editor
        e = self.check_false(["edit", self.f], False, True)[1]
        self.assertTrue(editor in e)

    def test_no_edit(self):
        if os.name == "nt":
            return

        os.environ["VISUAL"] = "touch -t 197001010101"
        realitems = lambda s: [(k, s[k]) for k in s.realkeys()]
        old_items = realitems(self.s)
        self.check_true(["edit", self.f], False, False)
        self.s.reload()
        self.assertEqual(sorted(old_items), sorted(realitems(self.s)))

    def test_mtime(self):
        if os.name == "nt":
            return

        os.environ["VISUAL"] = "true"
        self.check_false(["edit", self.f], False, True)
        os.environ["VISUAL"] = "false"
        self.check_false(["edit", self.f], False, True)

    def test_dry_run(self):
        if os.name == "nt" or sys.platform == "darwin":
            return

        realitems = lambda s: [(k, s[k]) for k in s.realkeys()]

        os.environ["VISUAL"] = "truncate -s 0"
        old_items = realitems(self.s)
        os.utime(self.f, (42, 42))
        e = self.check_true(["edit", "--dry-run", self.f], False, True)[1]

        # log all removals
        for key in self.s.realkeys():
            self.assertTrue(key in e)

        # nothing should have changed
        self.s.reload()
        self.assertEqual(sorted(old_items), sorted(realitems(self.s)))

    def test_remove_all(self):
        if os.name == "nt" or sys.platform == "darwin":
            return

        os.environ["VISUAL"] = "truncate -s 0"
        os.utime(self.f, (42, 42))
        self.check_true(["edit", self.f], False, False)

        # all should be gone
        self.s.reload()
        self.assertFalse(self.s.realkeys())


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

    def test_output(self):
        o, e = self.check_true(["tags"], True, False)
        assert not e
        assert "tracknumber" in o
        assert "replaygain_album_gain" not in o

        o, e = self.check_true(["tags", "-a"], True, False)
        assert not e
        assert "tracknumber" in o
        assert "replaygain_album_gain" in o


class TOperonImageExtract(TOperonBase):
    # [--dry-run] [--primary] [-d <destination>] <file> [<files>]

    def setUp(self):
        super(TOperonImageExtract, self).setUp()

        self.fcover = get_temp_copy(get_data_path('test-2.wma'))
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
            self.assertEqual(h.read(), image.read())

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
            self.assertEqual(h.read(), image.read())


class TOperonImageSet(TOperonBase):
    # <image-file> <file> [<files>]

    def setUp(self):
        super(TOperonImageSet, self).setUp()
        from gi.repository import GdkPixbuf

        h, self.filename = mkstemp(".png")
        os.close(h)
        wide = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 150, 10)
        wide.savev(self.filename, "png", [], [])

        self.fcover = get_temp_copy(get_data_path('test-2.wma'))
        self.cover = MusicFile(self.fcover)

        self.fcover2 = get_temp_copy(get_data_path('test-2.wma'))
        self.cover2 = MusicFile(self.fcover2)

    def tearDown(self):
        os.unlink(self.fcover)
        os.unlink(self.filename)
        super(TOperonImageSet, self).tearDown()

    def test_misc(self):
        self.check_true(["image-set", "-h"], True, False)
        self.check_false(["image-set", self.fcover], False, True)
        self.check_false(["image-set"], False, True)
        self.check_false(["image-set", self.filename], False, True)

    def test_not_supported(self):
        path = get_data_path('test.mid')
        out, err = self.check_false(
            ["image-set", self.filename, path], False, True)
        self.assertTrue("supported" in err)

    def test_set(self):
        self.check_true(["image-set", self.filename, self.fcover],
                        False, False)
        self.check_true(["-v", "image-set", self.filename, self.fcover],
                        False, True)

        self.cover.reload()
        images = self.cover.get_images()
        self.assertEqual(len(images), 1)

        with open(self.filename, "rb") as h:
            self.assertEqual(h.read(), images[0].read())

    def test_set_two(self):
        self.check_true(
            ["image-set", self.filename, self.fcover, self.fcover2],
            False, False)

        with open(self.filename, "rb") as h:
            image_data = h.read()

        for audio in [self.cover, self.cover2]:
            audio.reload()
            image = audio.get_images()[0]
            self.assertEqual(image.read(), image_data)


class TOperonImageClear(TOperonBase):
    # <image-file> <file> [<files>]

    def setUp(self):
        super(TOperonImageClear, self).setUp()
        self.fcover = get_temp_copy(get_data_path('test-2.wma'))
        self.cover = MusicFile(self.fcover)

    def tearDown(self):
        os.unlink(self.fcover)
        super(TOperonImageClear, self).tearDown()

    def test_misc(self):
        self.check_true(["image-clear", "-h"], True, False)
        self.check_true(["image-clear", self.fcover], False, False)
        self.check_false(["image-clear"], False, True)

    def test_not_supported(self):
        path = get_data_path('test.mid')
        out, err = self.check_false(["image-clear", path], False, True)
        self.assertTrue("supported" in err)

    def test_clear(self):
        images = self.cover.get_images()
        self.assertEqual(len(images), 1)

        self.check_true(["image-clear", self.fcover], False, False)

        self.cover.reload()
        images = self.cover.get_images()
        self.assertEqual(len(images), 0)


class TOperonFill(TOperonBase):
    # [--dry-run] <pattern> <file> [<files>]

    def test_misc(self):
        self.check_true(["fill", "-h"], True, False)
        self.check_false(["fill", self.f], False, True)
        self.check_true(["fill", "foo", self.f2], False, False)
        self.check_true(["fill", "foo", self.f, self.f2], False, False)

    def test_apply(self):
        basename = self.s("~basename")
        self.check_true(["fill", "<title>", self.f], False, False)
        self.s.reload()
        self.assertEqual(self.s("title"), os.path.splitext(basename)[0])

    def test_apply_no_match(self):
        old_title = self.s("title")
        self.check_true(
            ["fill", "<tracknumber>. <title>", self.f], False, False)
        self.s.reload()
        self.assertEqual(self.s("title"), old_title)

    def test_preview(self):
        o, e = self.check_true(
            ["fill", "--dry-run", "<title>", self.f], True, False)

        self.assertTrue("title" in o)
        self.assertTrue(self.s("~basename") in o)

    def test_preview_no_match(self):
        o, e = self.check_true(
            ["fill", "--dry-run", "<tracknumber>. <title>", self.f],
            True, False)

        self.assertTrue("title" in o)
        self.assertTrue(self.s("~basename") in o)
