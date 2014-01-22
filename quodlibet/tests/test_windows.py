# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR, skip

from quodlibet import windows


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
        self.assertEqual(d, u"C:\Windows\explorer.exe")
        self.assertTrue(isinstance(d, unicode))


if os.name != "nt":
    TWindows = skip(TWindows, "Wrong platform")
