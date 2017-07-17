# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util import is_unity, is_windows, is_osx


class TUtilEnvironment(TestCase):

    def test_all(self):
        self.assertTrue(isinstance(is_unity(), bool))
        self.assertTrue(isinstance(is_windows(), bool))
        self.assertTrue(isinstance(is_osx(), bool))

    def test_constrains(self):
        if is_windows():
            self.assertFalse(is_osx())

        if is_osx():
            self.assertFalse(is_windows())
