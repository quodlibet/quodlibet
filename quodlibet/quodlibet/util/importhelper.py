# -*- coding: utf-8 -*-
# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import imp

from os.path import join, splitext, basename

from quodlibet import util


def load_dir_modules(path, package, load_compiled=False):
    """Load all modules and packages in path (recursive).
    Load pyc files if load_compiled is True.
    In case the module is already loaded, doesn't reload it.
    """

    # needed for pickle etc.
    assert package in sys.modules

    try:
        modules = [e[0] for e in get_importables(path, load_compiled)]
    except OSError:
        util.print_w("%r not found" % path)
        return []

    # get_importables can yield py and pyc for the same module
    # and we want to load it only once
    modules = set(modules)

    loaded = []
    for name in modules:
        try:
            mod = load_module(name, package, path)
        except Exception:
            util.print_exc()
            continue
        if mod:
            loaded.append(mod)

    return loaded


def get_importables(folder, include_compiled=False):
    """Searches a folder and its subfolders for modules and packages to import.
    No subfolders in packages, .so supported.

    The root folder will not be considered a package.

    returns a tuple of the name, import path, list of possible dependencies
    """

    def is_ok(f):
        if f.startswith("_"):
            return False
        if f.endswith(".py"):
            return True
        elif include_compiled and f.endswith(".pyc"):
            return True
        return False

    def is_init(f):
        if f == "__init__.py":
            return True
        elif include_compiled and f == "__init__.pyc":
            return True
        return False

    first = True
    for root, dirs, names in os.walk(folder):
        # Ignore packages like "_shared"
        if basename(root).startswith("_"):
            continue
        if not first and any((is_init(n) for n in names)):
            yield (basename(root), root,
                   list(filter(is_ok, [join(root, name) for name in names])))
        else:
            for name in filter(is_ok, names):
                yield (splitext(name)[0], join(root, name), [join(root, name)])
        first = False


def load_module(name, package, path, reload=False):
    """Load a module/package. Returns the module or None.
       Doesn't catch any exceptions during the actual import.
       If reload is True and the module is already loaded, reload it.
    """

    fullname = package + "." + name
    try:
        return sys.modules[fullname]
    except KeyError:
        pass

    try:
        # this also handles packages
        fp, path, desc = imp.find_module(name, [path])
    except ImportError:
        return

    # modules need a parent package
    if package not in sys.modules:
        sys.modules[package] = imp.new_module(package)

    try:
        mod = imp.load_module(fullname, fp, path, desc)
    finally:
        if fp:
            fp.close()

    # make it accessible from the parent, like __import__ does
    vars(sys.modules[package])[name] = mod

    return mod
