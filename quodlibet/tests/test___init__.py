# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add

import quodlibet
from quodlibet import config


class TQuodlibet(TestCase):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_first_session(self):
        self.assertTrue(quodlibet.is_first_session("quodlibet"))
        self.assertTrue(quodlibet.is_first_session("quodlibet"))
        quodlibet.finish_first_session("exfalso")
        self.assertTrue(quodlibet.is_first_session("quodlibet"))
        quodlibet.finish_first_session("quodlibet")
        self.assertFalse(quodlibet.is_first_session("quodlibet"))

add(TQuodlibet)
