# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.downloader import DownloadWindow
import quodlibet.config


class TDownloadWindow(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.win = DownloadWindow()

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        quodlibet.config.quit()
