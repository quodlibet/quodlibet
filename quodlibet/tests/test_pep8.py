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
    PACKAGES = "util library parse browsers devices formats".split()

    def _run(self, path):
        subprocess.check_call(
            ["pep8", "--ignore=" + self.IGNORE_ERROROS, path])

    def test_packages(self):
        for package in self.PACKAGES:
            name = "quodlibet." + package
            mod = getattr(__import__(name), package)
            self._run(mod.__path__[0])


if iscommand("pep8"):
    add(TPEP8)
else:
    print_w("pep8 not found")
