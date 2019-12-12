# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import itertools
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import pytest

from quodlibet.util import is_wine

from tests import TestCase
from tests.helper import capture_output

from .util import iter_project_py_files, setup_cfg

try:
    import pycodestyle
except ImportError:
    try:
        import pep8 as pycodestyle
    except ImportError:
        pycodestyle = None


def create_pool():
    if is_wine():
        # ProcessPoolExecutor is broken under wine
        return ThreadPoolExecutor(1)
    else:
        return ProcessPoolExecutor(None)


def _check_file(f, ignore):
    style = pycodestyle.StyleGuide(ignore=ignore)
    with capture_output() as (o, e):
        style.check_files([f])
    return o.getvalue().splitlines()


def check_files(files, ignore=[]):
    lines = []
    with create_pool() as pool:
        for res in pool.map(_check_file, files, itertools.repeat(ignore)):
            lines.extend(res)
    return sorted(lines)


@pytest.mark.quality
class TPEP8(TestCase):
    def test_all(self):
        assert pycodestyle is not None, "pycodestyle/pep8 is missing"

        files = iter_project_py_files()
        errors = check_files(files, ignore=setup_cfg.ignore)
        if errors:
            raise Exception("\n".join(errors))
