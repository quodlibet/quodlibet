# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import re

import pytest

try:
    from pyflakes.scripts import pyflakes
except ImportError:
    pyflakes = None

from quodlibet.compat import PY3

from tests import TestCase


class FakeStream(object):
    # skip these by default
    BL = []
    if PY3:
        BL.append(
            "undefined name "
            "'(unichr|unicode|long|basestring|xrange|cmp|execfile|reload)'")

    def __init__(self, blacklist=None):
        self.lines = []
        if blacklist is None:
            blacklist = []
        self.bl = self.BL[:] + blacklist

    def write(self, text):
        for p in self.bl:
            if re.search(p, text):
                return
        text = text.strip()
        if not text:
            return
        self.lines.append(text)

    def check(self):
        if self.lines:
            raise Exception("\n" + "\n".join(self.lines))


@pytest.mark.quality
class TPyFlakes(TestCase):

    def __check_path(self, path):
        if not pyflakes:
            raise Exception("pyflakes missing; please install")

        old_stdout = sys.stdout
        stream = FakeStream()
        try:
            sys.stdout = stream
            for dirpath, dirnames, filenames in os.walk(path):
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
        self.__check_path(path)
