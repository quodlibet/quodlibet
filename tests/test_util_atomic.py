# Copyright 2013 Christoph Reiter, Dino Miniutti
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import stat
import shutil

from tests import TestCase, mkdtemp

from quodlibet.util.atomic import atomic_save


class Tatomic_save(TestCase):

    def setUp(self):
        self.dir = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_basic(self):
        filename = os.path.join(self.dir, "foo.txt")

        with open(filename, "wb") as fobj:
            fobj.write(b"nope")

        with atomic_save(filename, "wb") as fobj:
            fobj.write(b"foo")
            temp_name = fobj.name

        with open(filename, "rb") as fobj:
            self.assertEqual(fobj.read(), b"foo")

        self.assertFalse(os.path.exists(temp_name))
        self.assertEqual(os.listdir(self.dir), [os.path.basename(filename)])

    def test_non_exist(self):
        filename = os.path.join(self.dir, "foo.txt")

        with atomic_save(filename, "wb") as fobj:
            fobj.write(b"foo")
            temp_name = fobj.name

        with open(filename, "rb") as fobj:
            self.assertEqual(fobj.read(), b"foo")

        self.assertFalse(os.path.exists(temp_name))
        self.assertEqual(os.listdir(self.dir), [os.path.basename(filename)])

    def test_readonly(self):
        filename = os.path.join(self.dir, "foo.txt")

        with open(filename, "wb") as fobj:
            fobj.write(b"nope")

        dir_mode = os.stat(self.dir).st_mode
        file_mode = os.stat(filename).st_mode
        # setting directory permissions doesn't work under Windows, so make
        # the file read only, so the rename fails. On the other hand marking
        # the file read only doesn't make rename fail on unix, so make the
        # directory read only as well.
        os.chmod(filename, stat.S_IREAD)
        os.chmod(self.dir, stat.S_IREAD)
        try:
            with self.assertRaises(OSError):
                with atomic_save(filename, "wb") as fobj:
                    fobj.write(b"foo")
        finally:
            # restore permissions
            os.chmod(self.dir, dir_mode)
            os.chmod(filename, file_mode)

        with open(filename, "rb") as fobj:
            self.assertEqual(fobj.read(), b"nope")

        self.assertEqual(os.listdir(self.dir), [os.path.basename(filename)])

    def test_symbolic_link(self):
        filename = os.path.join(self.dir, "foo.txt")
        symlink = os.path.join(self.dir, "foo.link")

        os.symlink(filename, symlink)

        with open(filename, "wb") as fobj:
            fobj.write(b"nope")

        with atomic_save(symlink, "wb") as fobj:
            fobj.write(b"foo")
            temp_name = fobj.name

        with open(filename, "rb") as fobj:
            self.assertEqual(fobj.read(), b"foo")

        self.assertFalse(os.path.exists(temp_name))
        self.assertEqual(
            sorted(os.listdir(self.dir)),
            sorted([os.path.basename(filename), os.path.basename(symlink)]))
        self.assertTrue(os.path.islink(symlink))
