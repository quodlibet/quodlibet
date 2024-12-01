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
        assert isinstance(is_unity(), bool)
        assert isinstance(is_windows(), bool)
        assert isinstance(is_osx(), bool)

    def test_constrains(self):
        if is_windows():
            assert not is_osx()

        if is_osx():
            assert not is_windows()
