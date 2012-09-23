# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import sys
import imp

from os.path import join, splitext, dirname, basename
from traceback import format_exception

from quodlibet import util


def load_dir_modules(path, package, load_compiled=False):
    """Load all modules in path (non-recursive).
    Load pyc files if load_compiled is True.
    In case the module is already loaded, doesn't reload it.
    """

    try:
        entries = os.listdir(path)
    except OSError:
        print_w("%r not found" % path)
        return []

    modules = set()
    for entry in entries:
        if entry[:1] == "_":
            continue
        if entry.endswith(".py"):
            modules.add(entry[:-3])
        elif load_compiled and entry.endswith(".pyc"):
            modules.add(entry[:-4])

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
    No subfolders in packages, .pyc, .so supported.

    returns a tuple of the import path and a list of possible dependencies
    """

    is_ok = lambda f: f.endswith(".py") and not f.startswith("_")

    for root, dirs, names in os.walk(folder):
        if "__init__.py" in names:
            yield (root, filter(is_ok, [join(root, name) for name in names]))
        else:
            for name in filter(is_ok, names):
                yield (join(root, name), [join(root, name)])


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


class ModuleScanner(object):
    """
    Handles plugin modules. Takes a list of directories and searches
    for loadable python modules/packages in all of them.

    There is only one global namespace for modules using the module name
    as key.

    rescan() - Update the module list. Returns added/removed modules
    failures - A dict of Name: (Exception, Text) for all modules that failed
    modules - A dict of Name: Module for all successfully loaded modules

    """
    def __init__(self, folders):
        self.__folders = folders

        self.__modules = {}     # name: module
        self.__info = {}       # name: (path, deps)
        self.__deps = {}        # dep: mtime of last check
        self.__failures = {}    # name: exception

    def __remove_module(self, name):
        del self.__modules[name]
        path, deps = self.__info[name]
        for dep in deps:
            del self.__deps[dep]
        del self.__info[name]
        if name in self.__failures:
            del self.__failures[name]

    @property
    def failures(self):
        """A name: exception dict for all modules that failed to load"""
        return self.__failures

    @property
    def modules(self):
        """A name: module dict of all loaded modules"""
        return self.__modules

    def rescan(self):
        """Rescan all folders for changed/new/removed modules.

        The caller should release all references to removed modules.

        Returns a tuple: (removed, added)
        """

        print_d("Rescanning..")

        info = {}

        # get what is there atm
        for folder in self.__folders:
            for path, deps in get_importables(folder):
                # take the basename as module key, later modules win
                info[splitext(basename(path))[0]] = (path, deps)

        def deps_changed(old_list, new_list):
            if set(old_list) != set(new_list):
                return True
            for dep in old_list:
                old_mtime = self.__deps[dep]
                if util.mtime(dep) != old_mtime:
                    return True
            return False

        # python can not unload a module, so we can only add new ones
        # or reload if the path is the same and mtime changed,
        # but we can still pretend we removed something

        removed = []
        added = []

        # remove those that are gone and changed ones
        for name, mod in self.__modules.items():
            if name not in info:
                self.__remove_module(name)
                removed.append(name)
                continue
            path, deps = self.__info[name]
            path, new_deps = info[name]
            if deps_changed(deps, new_deps):
                self.__remove_module(name)
                removed.append(name)

        # add new ones
        for (name, (path, deps)) in info.iteritems():
            if name in self.__modules:
                continue

            try:
                mod = load_module(name, "quodlibet.fake.plugins",
                                  dirname(path), reload=True)
                if mod is None:
                    continue
            except Exception, err:
                text = format_exception(*sys.exc_info())
                self.__failures[name] = (err, text)
            else:
                added.append(name)
                self.__modules[name] = mod
                self.__info[name] = info[name]
                for dep in deps:
                    self.__deps[dep] = util.mtime(dep)

        print_d("Rescanning done: %d added, %d removed, %d error(s)" %
                (len(added), len(removed), len(self.__failures)))

        return removed, added
