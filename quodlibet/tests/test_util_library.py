# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from senf import fsnative, expanduser

from quodlibet import config
from quodlibet.util.library import split_scan_dirs, set_scan_dirs, \
    get_exclude_dirs, get_scan_dirs
from quodlibet.util import is_windows
from quodlibet.util.path import get_home_dir, unexpand

from tests import TestCase


STANDARD_PATH = fsnative(u"/home/user/Music")
OTHER_PATH = fsnative(u"/opt/party")
GVFS_PATH = fsnative(u"/run/user/12345/gvfs/smb-share"
                      ":server=12.23.34.45,share=/foo/bar/baz/path")
GVFS_PATH_ESCAPED = fsnative(u"/run/user/12345/gvfs/smb-share"
                              "\\:server=12.23.34.45,share=/foo/bar/baz/path")


class Tlibrary_utils(TestCase):

    def test_basic(self):
        if is_windows():
            res = split_scan_dirs(u":Z:\\foo:C:/windows:")
            self.assertEquals(res, [u"Z:\\foo", u"C:/windows"])
        else:
            res = split_scan_dirs(":%s:%s:" % (STANDARD_PATH, OTHER_PATH))
            self.assertEquals(res, [STANDARD_PATH, OTHER_PATH])

    def test_colon_paths(self):
        if not is_windows():
            res = split_scan_dirs(
                ":%s:%s" % (STANDARD_PATH, GVFS_PATH_ESCAPED))
            self.assertEquals(res, [STANDARD_PATH, GVFS_PATH])

    def test_get_exclude_dirs(self):
        some_path = os.path.join(unexpand(get_home_dir()), "foo")
        config.set('library', 'exclude', some_path)
        assert expanduser(some_path) in get_exclude_dirs()

        assert all([isinstance(p, fsnative) for p in get_exclude_dirs()])

    def test_get_scan_dirs(self):
        some_path = os.path.join(unexpand(get_home_dir()), "foo")
        config.set('settings', 'scan', some_path)
        assert expanduser(some_path) in get_scan_dirs()

        assert all([isinstance(p, fsnative) for p in get_scan_dirs()])


class Tset_scan_dirs(TestCase):

    @property
    def scan_dirs(self):
        return config.get('settings', 'scan')

    def test_set_scan_dirs_empty(self):
        set_scan_dirs([])
        self.assertEqual(self.scan_dirs, "")

    def test_set_scan_dirs_single(self):
        set_scan_dirs([STANDARD_PATH])
        self.assertEqual(self.scan_dirs, STANDARD_PATH)

    def test_set_scan_dirs_multiple(self):
        set_scan_dirs([OTHER_PATH, STANDARD_PATH])
        self.assertEqual(self.scan_dirs,
                         "%s:%s" % (OTHER_PATH, STANDARD_PATH))

    def test_set_scan_dirs_colons(self):
        set_scan_dirs([STANDARD_PATH, GVFS_PATH])
        expected = GVFS_PATH if is_windows() else GVFS_PATH_ESCAPED
        self.assertEqual(self.scan_dirs, "%s:%s" % (STANDARD_PATH, expected))
