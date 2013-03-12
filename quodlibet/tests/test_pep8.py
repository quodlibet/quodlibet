# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import subprocess
import unittest

from tests import TestCase, add

from quodlibet.util import iscommand


class TPEP8(TestCase):
    # E12x popped up in pep8 1.4 compared to 1.2..
    # drop them once 1.4 is common enough
    IGNORE_ERROROS = "E12"

    def _run(self, path):
        subprocess.check_call(
            ["pep8", "--ignore=" + self.IGNORE_ERROROS, path])

    def test_utils(self):
        from quodlibet import util
        path = util.__path__[0]
        self._run(path)

    def test_library(self):
        from quodlibet import library
        path = library.__path__[0]
        self._run(path)

    def test_parse(self):
        from quodlibet import parse
        path = parse.__path__[0]
        self._run(path)

    def test_browsers(self):
        from quodlibet import browsers
        path = browsers.__path__[0]
        self._run(path)


if iscommand("pep8"):
    add(TPEP8)
else:
    print_w("pep8 not found")
