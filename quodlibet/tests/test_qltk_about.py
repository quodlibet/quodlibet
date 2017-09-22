# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import app
from quodlibet.qltk.about import AboutDialog
from tests import TestCase, init_fake_app, destroy_fake_app


class TAboutDialog(TestCase):

    def setUp(self):
        init_fake_app()

    def tearDown(self):
        destroy_fake_app()

    def test_ctr(self):
        AboutDialog(None, app).destroy()
