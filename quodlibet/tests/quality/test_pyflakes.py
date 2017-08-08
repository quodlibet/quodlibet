# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import pytest

from quodlibet.util import is_wine
from .util import iter_project_py_files, setup_cfg

os.environ["PYFLAKES_NODOCTEST"] = "1"
os.environ["PYFLAKES_BUILTINS"] = ",".join(setup_cfg.builtins)

try:
    from pyflakes.scripts import pyflakes
except ImportError:
    pyflakes = None

from tests import TestCase
from tests.helper import capture_output


def create_pool():
    if is_wine():
        # ProcessPoolExecutor is broken under wine
        return ThreadPoolExecutor(1)
    else:
        return ProcessPoolExecutor(None)


def _check_file(f):
    with capture_output() as (o, e):
        pyflakes.checkPath(f)
    return o.getvalue().splitlines()


def check_files(files, ignore=[]):
    lines = []
    with create_pool() as pool:
        for res in pool.map(_check_file, files):
            lines.extend(res)
    return sorted(lines)


@pytest.mark.quality
class TPyFlakes(TestCase):

    def test_all(self):
        assert pyflakes is not None, "pyflakes is missing"

        files = iter_project_py_files()
        files = (f for f in files if not f.endswith("compat.py"))
        errors = check_files(files)
        if errors:
            raise Exception("\n".join(errors))
