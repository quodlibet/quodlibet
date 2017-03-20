# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.qltk.scanbox import ScanBox

from . import TestCase


class TScanBox(TestCase):

    def test_main(self):
        ScanBox().destroy()
