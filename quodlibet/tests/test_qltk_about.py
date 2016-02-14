# -*- coding: utf-8 -*-
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
