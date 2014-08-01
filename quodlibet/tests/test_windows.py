# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR, skipUnless

from quodlibet.util.path import normalize_path
from quodlibet import windows


@skipUnless(os.name == "nt", "Wrong platform", warn=False)
class TWindows(TestCase):

    def test_dir_funcs(self):
        d = windows.get_personal_dir()
        self.assertTrue(d is None or isinstance(d, unicode))

        d = windows.get_appdate_dir()
        self.assertTrue(d is None or isinstance(d, unicode))

        d = windows.get_desktop_dir()
        self.assertTrue(d is None or isinstance(d, unicode))

        d = windows.get_music_dir()
        self.assertTrue(d is None or isinstance(d, unicode))

        d = windows.get_profile_dir()
        self.assertTrue(d is None or isinstance(d, unicode))

        d = windows.get_links_dir()
        self.assertTrue(d is None or isinstance(d, unicode))

    def test_get_link_target(self):
        path = os.path.join(DATA_DIR, "test.lnk")
        d = windows.get_link_target(path)
        self.assertEqual(
            normalize_path(d), normalize_path(u"C:\Windows\explorer.exe"))
        self.assertTrue(isinstance(d, unicode))

    def test_environ(self):
        env = windows.WindowsEnviron()
        len_ = len(env)
        env[u"FOO"] = u"bar"
        self.assertEqual(len(env), len_ + 1)
        self.assertEqual(env.get(u"FOO"), u"bar")
        self.assertTrue("FOO" in repr(env))
        self.assertEqual(len(list(env)), len(env))
        del env[u"FOO"]

    def test_environ_ascii(self):
        env = windows.WindowsEnviron()
        env["FOO"] = u"bar"
        env["FOO"]
        del env["FOO"]
