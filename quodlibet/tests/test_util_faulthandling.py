# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase
from .helper import temp_filename

from quodlibet.util import faulthandling


class Tfaulthandling(TestCase):

    def test_basic(self):
        with temp_filename() as filename:
            faulthandling.enable(filename)
            assert faulthandling.check_and_clear_error() is None
            faulthandling.disable()
