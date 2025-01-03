# Copyright 2013 Christoph Reiter
#           2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import pytest

from tests import TestCase, get_data_path, skipUnless

from quodlibet.util.path import normalize_path
from quodlibet.util import is_wine
from quodlibet.util import windows


@skipUnless(os.name == "nt", "Wrong platform")
class TWindows(TestCase):
    def test_dir_funcs(self):
        d = windows.get_personal_dir()
        assert d is None or isinstance(d, str)

        d = windows.get_appdata_dir()
        assert d is None or isinstance(d, str)

        d = windows.get_desktop_dir()
        assert d is None or isinstance(d, str)

        d = windows.get_music_dir()
        assert d is None or isinstance(d, str)

        d = windows.get_profile_dir()
        assert d is None or isinstance(d, str)

        d = windows.get_links_dir()
        assert d is None or isinstance(d, str)

    def test_get_link_target(self):
        path = get_data_path("test.lnk")
        d = windows.get_link_target(path)
        assert isinstance(d, str)
        assert normalize_path(d) == normalize_path("C:\\Windows\\explorer.exe")

    def test_get_link_target_unicode(self):
        path = get_data_path("test2.lnk")
        d = windows.get_link_target(path)
        assert isinstance(d, str)
        if is_wine():
            # wine doesn't support unicode paths here...
            assert os.path.basename(d) == "\xe1??.txt"
        else:
            assert os.path.basename(d) == "\xe1\U00016826.txt"

    def test_get_link_target_non_exist(self):
        with pytest.raises(WindowsError):
            windows.get_link_target("nopenope.lnk")
