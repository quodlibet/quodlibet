# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

import quodlibet


def iter_py_files(root):
    for base, dirs, files in os.walk(root):
        for file_ in files:
            path = os.path.join(base, file_)
            if os.path.splitext(path)[1] == ".py":
                yield path


def iter_project_py_files():
    root = os.path.dirname(os.path.abspath(quodlibet.__path__[0]))
    skip = [
        os.path.join(root, "quodlibet", "optpackages"),
    ]
    for path in iter_py_files(root):
        if any((path.startswith(s + os.sep) or s == path)
               for s in skip):
            continue
        yield path
