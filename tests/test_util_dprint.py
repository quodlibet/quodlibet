# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

from tests import TestCase
from .helper import capture_output

from quodlibet.util.dprint import print_e, format_exception_only, print_exc


class Tdprint(TestCase):
    def test_basics(self):
        with capture_output() as (stdout, stderr):
            print_e("foo")
        assert "foo" in stderr.getvalue()

    def test_any_object(self):
        with capture_output() as (stdout, stderr):
            print_e(42)
        assert "42" in stderr.getvalue()

    def test_format_exception_only(self):
        try:
            raise Exception
        except Exception:
            result = format_exception_only(*sys.exc_info()[:2])
            assert all(isinstance(l, str) for l in result)

    def test_no_stack(self):
        with capture_output():
            print_exc((None, None, None))
