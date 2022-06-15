# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import importlib

from os.path import join, splitext, basename

from quodlibet import util, print_d


def load_dir_modules(path, package):
    """Load all modules and packages in path (recursive).

    In case the module is already loaded, doesn't reload it.
    """

    # needed for pickle etc.
    assert package in sys.modules

    try:
        modules = [e[0] for e in get_importables(path)]
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


def get_importables(folder):
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
        return False

    def is_init(f):
        return f == "__init__.py"

    first = True
    for root, dirs, names in os.walk(folder):
        # Ignore packages like "_shared"
        for d in dirs:
            if d.startswith("_") or d.startswith("."):
                print_d("Ignoring %r" % os.path.join(root, d))
                dirs.remove(d)
        if not first and any((is_init(n) for n in names)):
            yield (basename(root), root,
                   [d for d in (join(root, name) for name in names) if is_ok(d)])
        else:
            for name in filter(is_ok, names):
                yield (splitext(name)[0], join(root, name), [join(root, name)])
        first = False


def load_module(name, package, path):
    """Load a module/package. Returns the module or None.
       Doesn't catch any exceptions during the actual import.
    """

    fullname = package + "." + name
    try:
        return sys.modules[fullname]
    except KeyError:
        pass

    loader = importlib.find_loader(fullname, [path])
    if loader is None:
        return

    # modules need a parent package
    if package not in sys.modules:
        spec = importlib.machinery.ModuleSpec(package, None, is_package=True)
        sys.modules[package] = importlib.util.module_from_spec(spec)

    mod = loader.load_module(fullname)

    # make it accessible from the parent, like __import__ does
    vars(sys.modules[package])[name] = mod

    return mod
