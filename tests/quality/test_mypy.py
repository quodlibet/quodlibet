# Copyright 2018 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")

import quodlibet
from quodlibet.util import get_module_dir


@pytest.mark.quality
class TestMypy:

    def test_project(self):
        root = Path(get_module_dir(quodlibet))
        assert Path.cwd() == root.parent, "MyPy must be run from project root"
        out, err, status = api.run([str(root)])
        assert status == 0, "Failed mypy checks: \n" + "\n".join([out, err])
