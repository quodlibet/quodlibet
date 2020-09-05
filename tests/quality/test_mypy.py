# Copyright 2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import pytest
api = pytest.importorskip("mypy.api")

import quodlibet
from quodlibet.util import get_module_dir
from tests import TestCase


@pytest.mark.quality
class Tmypy(TestCase):

    def test_all(self):
        root = os.path.dirname(get_module_dir(quodlibet))
        out, err, status = api.run([root])
        if status != 0:
            raise Exception("\n" + "\n".join([out, err]))
