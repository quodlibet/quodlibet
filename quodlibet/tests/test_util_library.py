# -*- coding: utf-8 -*-
# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from senf import fsnative

from quodlibet import config
from quodlibet.util.library import split_scan_dirs, set_scan_dirs

from tests import TestCase

ON_WINDOWS = sys.platform == "win32"

STANDARD_PATH = fsnative(u"/home/user/Music")
OTHER_PATH = fsnative(u"/opt/party")
GVFS_PATH = fsnative(u"/run/user/12345/gvfs/smb-share"
                      ":server=12.23.34.45,share=/foo/bar/baz/path")
GVFS_PATH_ESCAPED = fsnative(u"/run/user/12345/gvfs/smb-share"
                              "\:server=12.23.34.45,share=/foo/bar/baz/path")


class Tsplit_scan_dirs(TestCase):
    def test_basic(self):
        if ON_WINDOWS:
            res = split_scan_dirs(r":Z:\foo:C:/windows:")
            self.assertEquals(res, [r"Z:\foo", "C:/windows"])
        else:
            res = split_scan_dirs(":%s:%s:" % (STANDARD_PATH, OTHER_PATH))
            self.assertEquals(res, [STANDARD_PATH, OTHER_PATH])

    def test_colon_paths(self):
        if not ON_WINDOWS:
            res = split_scan_dirs(
                ":%s:%s" % (STANDARD_PATH, GVFS_PATH_ESCAPED))
            self.assertEquals(res, [STANDARD_PATH, GVFS_PATH])


class Tset_scan_dirs(TestCase):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

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
        expected = GVFS_PATH if ON_WINDOWS else GVFS_PATH_ESCAPED
        self.assertEqual(self.scan_dirs, "%s:%s" % (STANDARD_PATH, expected))
