# Copyright 2020 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import quodlibet

import pytest

try:
    from flake8.api import legacy as flake8
except ImportError:
    flake8 = None

from tests import TestCase
from tests.helper import capture_output
from quodlibet.util import get_module_dir


@pytest.mark.quality
class TFlake8(TestCase):

    def test_all(self):
        assert flake8 is not None, "flake8 is missing"
        style_guide = flake8.get_style_guide()
        root = os.path.dirname(get_module_dir(quodlibet))
        root = os.path.relpath(root, os.getcwd())
        with capture_output() as (o, e):
            style_guide.check_files([root])
        errors = o.getvalue().splitlines()
        if errors:
            raise Exception("\n" + "\n".join(errors))
