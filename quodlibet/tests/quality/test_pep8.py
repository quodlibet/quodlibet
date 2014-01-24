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

from tests import TestCase, skip


class TPEP8(TestCase):
    # E12x popped up in pep8 1.4 compared to 1.2..
    # drop them once 1.4 is common enough
    # E261: at least two spaces before inline comment
    IGNORE_ERROROS = ["E12", "E261"]
    PACKAGES = ("util library parse browsers devices formats "
                "plugins qltk player").split()

    def _run(self, path, ignore=None):
        if ignore is None:
            ignore = []
        ignore += self.IGNORE_ERROROS

        p = subprocess.Popen(
            ["pep8", "--ignore=" + ",".join(ignore), path],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE)

        class Future(object):

            def __init__(self, p):
                self.p = p

            def result(self):
                if self.p.wait() != 0:
                    return self.p.communicate()

        return Future(p)

    def test_all(self):
        futures = []

        # packages
        for package in self.PACKAGES:
            name = "quodlibet." + package
            mod = getattr(__import__(name), package)
            futures.append(self._run(mod.__path__[0]))

        # main_package
        import quodlibet
        path = quodlibet.__path__[0]
        files = glob.glob(os.path.join(path, "*.py"))
        for file_ in files:
            futures.append(self._run(file_))

        # plugins
        futures.append(self._run(os.path.join(path, "../../plugins")))

        # tests
        futures.append(
            self._run(os.path.join(path, "../tests"), ignore=["W601"]))

        # scripts
        scripts = glob.glob(os.path.join(os.path.join(path, "../"), "*.py"))
        assert scripts
        for script in scripts:
            futures.append(self._run(script))

        # dist
        files = glob.glob(os.path.join(os.path.join(path, "../gdist"), "*.py"))
        assert files
        for file_ in files:
            futures.append(self._run(file_))

        # join and print results
        errors = []
        for f in futures:
            res = f.result()
            if res is not None:
                stdout, stderr = res
                errors.append(stdout)

        if errors:
            raise Exception("\n".join(errors))


if not iscommand("pep8"):
    TPEP8 = skip(TPEP8, "pep8 not found")
