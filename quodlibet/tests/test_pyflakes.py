# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import glob
import sys
import subprocess
import unittest

try:
    from pyflakes.scripts import pyflakes
except ImportError:
    pyflakes = None

from tests import TestCase, add


class FakeStream(object):
    # skip these, can be false positives
    BL = ["imported but unused",
          "redefinition of unused",
          "unable to detect undefined names",
          "redefinition of function"]

    def __init__(self):
        self.lines = []

    def write(self, text):
        for p in self.BL:
            if p in text:
                return
        text = text.strip()
        if not text:
            return
        self.lines.append(text)

    def check(self):
        if self.lines:
            raise Exception("\n".join(self.lines))


class TPyFlakes(TestCase):

    def __check_path(self, path, bl=None):
        if bl is None:
            bl = []
        old_stdout = sys.stdout
        stream = FakeStream()
        try:
            sys.stdout = stream
            for dirpath, dirnames, filenames in os.walk(path):
                if os.path.relpath(dirpath, path) in bl:
                    continue
                for filename in filenames:
                    if filename.endswith('.py'):
                        pyflakes.checkPath(os.path.join(dirpath, filename))
        finally:
            sys.stdout = old_stdout
        stream.check()

    def test_core(self):
        import quodlibet
        path = quodlibet.__path__[0]
        path = os.path.dirname(path)
        self.__check_path(path, bl=["build"])

    def test_plugins(self):
        import quodlibet
        path = quodlibet.__path__[0]
        path = os.path.join(path, "../../plugins")
        self.__check_path(path)


if pyflakes:
    add(TPyFlakes)
else:
    print_w("pyflakes not found")
