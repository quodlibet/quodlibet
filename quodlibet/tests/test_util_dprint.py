# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase
from .helper import capture_output

from quodlibet.util.dprint import print_e


class Tdprint(TestCase):

    def test_basics(self):
        with capture_output() as (stdout, stderr):
            print_e(u"foo")
        assert u"foo" in stderr.getvalue()

    def test_any_object(self):
        with capture_output() as (stdout, stderr):
            print_e(42)
        assert u"42" in stderr.getvalue()
