# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import glob
import subprocess
import unittest
from quodlibet.util.path import iscommand

from tests import TestCase, add


class TPEP8(TestCase):
    # E12x popped up in pep8 1.4 compared to 1.2..
    # drop them once 1.4 is common enough
    # E261: at least two spaces before inline comment
    # W603: we use <> to check for py3k atm..
    IGNORE_ERROROS = ["E12", "E261", "W603"]
    PACKAGES = ("util library parse browsers devices formats "
                "plugins qltk player").split()

    def _run(self, path, ignore=None):
        if ignore is None:
            ignore = []
        ignore += self.IGNORE_ERROROS

        p = subprocess.Popen(
            ["pep8", "--ignore=" + ",".join(ignore), path],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        if p.wait() != 0:
            o, e = p.communicate()
            raise Exception("\n" + o)

    def test_packages(self):
        for package in self.PACKAGES:
            name = "quodlibet." + package
            mod = getattr(__import__(name), package)
            self._run(mod.__path__[0])

    def test_main_package(self):
        import quodlibet
        path = quodlibet.__path__[0]
        files = glob.glob(os.path.join(path, "*.py"))
        for file_ in files:
            self._run(file_)

    def test_plugins(self):
        import quodlibet
        path = quodlibet.__path__[0]
        path = os.path.join(path, "../../plugins")
        self._run(path)

    def test_tests(self):
        import quodlibet
        path = quodlibet.__path__[0]
        path = os.path.join(path, "../tests")
        self._run(path, ignore=["W601"])

    def test_scripts(self):
        import quodlibet
        path = quodlibet.__path__[0]
        path = os.path.join(path, "../")
        files = glob.glob(os.path.join(path, "*.py"))
        assert files

        for file_ in files:
            self._run(file_)

    def test_dist(self):
        import quodlibet
        path = quodlibet.__path__[0]
        path = os.path.join(path, "../gdist")
        files = glob.glob(os.path.join(path, "*.py"))
        assert files

        for file_ in files:
            self._run(file_)

if iscommand("pep8"):
    add(TPEP8)
else:
    print_w("pep8 not found")
