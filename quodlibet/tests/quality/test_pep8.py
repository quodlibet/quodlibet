# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import glob
import errno
import subprocess

import pytest

from tests import TestCase


@pytest.mark.quality
class TPEP8(TestCase):
    # E12x popped up in pep8 1.4 compared to 1.2..
    # drop them once 1.4 is common enough
    # E261: at least two spaces before inline comment
    IGNORE_ERROROS = ["E12", "E261", "E265", "E713", "W602", "E402", "E731",
                      "W503"]

    def _run(self, path, ignore=None):
        if ignore is None:
            ignore = []
        ignore += self.IGNORE_ERROROS

        try:
            p = subprocess.Popen(
                ["pep8", "--ignore=" + ",".join(ignore), path],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise Exception("pep8 missing; please install")
            raise

        class Future(object):

            def __init__(self, p):
                self.p = p

            def result(self):
                if self.p.wait() != 0:
                    return self.p.communicate()

        return Future(p)

    def test_all(self):
        futures = []

        # main_package
        import quodlibet
        path = quodlibet.__path__[0]
        files = glob.glob(os.path.join(path, "*.py"))
        for file_ in files:
            futures.append(self._run(file_))

        # packages
        for entry in os.listdir(path):
            sub = os.path.join(path, entry)
            if os.path.isdir(sub):
                futures.append(self._run(sub))

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
                errors.append(stdout.decode("utf-8"))

        if errors:
            raise Exception("\n".join(errors))
