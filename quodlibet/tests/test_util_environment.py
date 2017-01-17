# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.util import is_unity, is_windows, is_osx, is_py2exe, \
    is_py2exe_console, is_py2exe_window


class TUtilEnvironment(TestCase):

    def test_all(self):
        self.assertTrue(isinstance(is_unity(), bool))
        self.assertTrue(isinstance(is_windows(), bool))
        self.assertTrue(isinstance(is_osx(), bool))
        self.assertTrue(isinstance(is_py2exe(), bool))
        self.assertTrue(isinstance(is_py2exe_console(), bool))
        self.assertTrue(isinstance(is_py2exe_window(), bool))

    def test_constrains(self):
        if is_py2exe():
            self.assertEqual(is_py2exe_console(), not is_py2exe_window())
            self.assertTrue(is_windows())

        if is_windows():
            self.assertFalse(is_osx())

        if is_osx():
            self.assertFalse(is_windows())
