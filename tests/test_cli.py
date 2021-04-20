# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from .helper import capture_output
from quodlibet import cli
from tests import TestCase


class Tcli(TestCase):

    def test_process_no_arguments_works(self):
        with capture_output() as (out, err):
            cli.process_arguments(["myprog"])
            self.assertFalse(out.getvalue())
            self.assertFalse(err.getvalue())

    def test_process_arguments_errors_on_invalid_opt(self):
        with self.assertRaises(SystemExit):
            with capture_output():
                cli.process_arguments(["myprog", "--wrong-thing"])
