# Copyright 2014, 2015 Christoph Reiter
#              2020-21 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import re
from pathlib import Path
from re import Pattern
from collections.abc import Iterable

import pytest
from gi.repository import Gtk
from pytest import fixture

from quodlibet.util import get_module_dir
from tests.test_po import QL_BASE_PATH


def iter_py_paths() -> Iterable[Path]:
    """Iterates over all Python source files that are part of Quod Libet"""

    import quodlibet
    root = Path(get_module_dir(quodlibet)).parent

    skip = [root / d for d in
            ("build",
             "dist",
             "docs",
             "dev-utils",
             Path("quodlibet") / "packages")
            ]
    # Path.glob() not efficient on big trees :(
    for dirpath, dirnames, filenames in os.walk(root):
        root = Path(dirpath)
        parents = root.parents
        if root.name.startswith(".") or any(s in parents for s in skip):
            # Don't test *any* subdirs of hidden / ignored parents
            dirnames.clear()
            continue
        for filename in filenames:
            if filename.endswith(".py"):
                yield root / filename


def prettify_path(p: Path) -> str:
    return os.path.splitext(p.relative_to(QL_BASE_PATH))[0]


@pytest.fixture(params=list(iter_py_paths()), ids=prettify_path)
def py_path(request) -> Path:
    return request.param


@pytest.mark.quality
class TestLicense:
    ALLOWED_RAW = ["""
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
""", """
Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""]
    ALLOWED = ["".join(license.split()) for license in ALLOWED_RAW]

    def test_license_is_compliant(self, py_path: Path):
        header = b""
        with open(py_path, "rb") as h:
            for line in h:
                line = line.strip()
                if not line.startswith(b"#"):
                    break
                header += line.lstrip(b"# ") + b"\n"

        norm = b"".join(header.split())
        norm = norm.decode("utf-8")
        assert any(l in norm for l in self.ALLOWED)


# Don't mark this as quality - useful to execute _everywhere_
class TestStockIcons:
    @fixture
    def res(self) -> Iterable[Pattern]:
        return [re.compile(r)
                for r in ("(Gtk\\.STOCK_[_A-Z]*)",
                          "[\"\'](gtk-[\\-a-z]*)")]

    @fixture
    def white(self) -> list[str]:
        # gtk setting keys start like stock icons, so white list them
        white = [x.replace("_", "-") for x in
                 dir(Gtk.Settings.get_default().props)
                 if x.startswith("gtk_")]
        # older gtk doesn't have those, but we still have them in the source
        white += ["gtk-dialogs-use-header",
                  "gtk-primary-button-warps-slider"]
        # some more..
        white += ["gtk-tooltip", "gtk-", "gtk-update-icon-cache-"]
        return white

    def test_icons_used(self, py_path: Path, res, white):
        if py_path.name in ("icons.py", "test_source.py"):
            return
        with open(py_path, "rb") as h:
            data = h.read().decode("utf-8")
            for r in res:
                match = r.search(data)
                if match:
                    group = match.group(1)
                    assert group in white
