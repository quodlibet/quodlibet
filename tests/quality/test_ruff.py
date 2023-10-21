# Copyright 2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import subprocess

import pytest

try:
    from ruff.__main__ import find_ruff_bin
except ImportError:
    find_ruff_bin = None
from tests import QL_BASE_PATH, skipUnless


@pytest.mark.quality
@skipUnless(find_ruff_bin, "Can't find ruff executable")
def test_ruff():
    ruff = find_ruff_bin()
    completed_process = subprocess.run([os.fsdecode(ruff), "check", str(QL_BASE_PATH)])
    assert completed_process.returncode == 0, "Failed with:\n{completed_process.stderr}"
