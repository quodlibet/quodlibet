# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import quodlibet
from quodlibet.util import get_module_dir


def iter_py_files(root):
    for base, dirs, files in os.walk(root):
        for file_ in files:
            path = os.path.join(base, file_)
            if os.path.splitext(path)[1] == ".py":
                yield path


def iter_project_py_files():
    root = os.path.dirname(get_module_dir(quodlibet))
    skip = [
        os.path.join(root, "quodlibet", "optpackages"),
        os.path.join(root, "quodlibet", "packages"),
        os.path.join(root, "build"),
        os.path.join(root, "dist"),
    ]
    for path in iter_py_files(root):
        if any((path.startswith(s + os.sep) or s == path)
               for s in skip):
            continue
        yield path
