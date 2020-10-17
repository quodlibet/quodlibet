# Copyright 2020 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from pathlib import Path
from typing import Iterable

import pytest
from pytest import fixture

import quodlibet

try:
    from flake8.api import legacy as flake8
except ImportError:
    flake8 = None

from tests.helper import capture_output
from quodlibet.util import get_module_dir


def should_check(p: Path) -> bool:
    return (p.is_dir()
            and not (p.name.startswith(".") or p.name.startswith("_")))


def checked_dirs() -> Iterable[Path]:
    root_path = Path(get_module_dir(quodlibet)).parent
    return (p for p in root_path.iterdir() if should_check(p))


@fixture(params=checked_dirs(), ids=lambda p: p.name)
def dir_to_check(request) -> Path:
    return request.param


@pytest.mark.quality
class TestFlake8:

    def test_directory(self, dir_to_check: Path):
        assert flake8 is not None, "flake8 is missing"
        style_guide = flake8.get_style_guide()

        with capture_output() as (o, e):
            style_guide.check_files([str(dir_to_check)])
        errors = o.getvalue().splitlines()
        assert not errors, f"{len(errors)} error(s):\n".join(errors)
