# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from senf import fsnative

from quodlibet.qltk.scanbox import ScanBox, get_init_select_dir

from . import TestCase


class TScanBox(TestCase):

    def test_main(self):
        ScanBox().destroy()

    def test_get_init_select_dir(self):
        assert isinstance(get_init_select_dir(), fsnative)
