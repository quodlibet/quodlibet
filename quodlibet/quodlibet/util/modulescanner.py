# -*- coding: utf-8 -*-
# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import imp

from os.path import dirname
from traceback import format_exception

from quodlibet.util.path import mtime
from quodlibet.util.importhelper import get_importables, load_module
from quodlibet.util import print_d
from quodlibet.compat import iteritems


class Module(object):

    def __init__(self, name, module, deps, path):
        self.name = name
        self.module = module
        self.path = path

        self.deps = {}
        for dep in deps:
            self.deps[dep] = mtime(dep)

    def has_changed(self, dep_paths):
        if set(self.deps.keys()) != set(dep_paths):
            return True

        for path, old_mtime in iteritems(self.deps):
            if mtime(path) != old_mtime:
                return True

        return False

    def __repr__(self):
        return "<%s name=%r>" % (type(self).__name__, self.name)


class ModuleImportError(object):

    def __init__(self, name, exception, traceback):
        self.name = name
        self.exception = exception
        self.traceback = traceback


class ModuleScanner(object):
    """
    Handles plugin modules. Takes a list of directories and searches
    for loadable python modules/packages in all of them.

    There is only one global namespace for modules using the module name
    as key.

    rescan() - Update the module list. Returns added/removed module names
    failures - A dict of Name: (Exception, Text) for all modules that failed
    modules - A dict of Name: Module for all successfully loaded modules

    """
    def __init__(self, folders):
        self.__folders = folders
        self.__modules = {}  # name: module
        self.__failures = {}  # name: exception

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
            for name, path, deps in get_importables(folder, True):
                # take the basename as module key, later modules win
                info[name] = (path, deps)

        # python can not unload a module, so we can only add new ones
        # or reload if the path is the same and mtime changed,
        # but we can still pretend we removed something

        removed = []
        added = []

        # remove those that are gone and changed ones
        for name, mod in list(self.__modules.items()):
            # not here anymore, remove
            if name not in info:
                del self.__modules[name]
                removed.append(name)
                continue

            # check if any dependency has changed
            path, new_deps = info[name]
            if mod.has_changed(new_deps):
                del self.__modules[name]
                removed.append(name)

        self.__failures.clear()

        # add new ones
        for (name, (path, deps)) in iteritems(info):
            if name in self.__modules:
                continue

            try:
                # add a real module, so that pickle works
                # https://github.com/quodlibet/quodlibet/issues/1093
                parent = "quodlibet.fake"
                if parent not in sys.modules:
                    sys.modules[parent] = imp.new_module(parent)
                vars(sys.modules["quodlibet"])["fake"] = sys.modules[parent]

                mod = load_module(name, parent + ".plugins",
                                  dirname(path), reload=True)
                if mod is None:
                    continue

            except Exception as err:
                text = format_exception(*sys.exc_info())
                self.__failures[name] = ModuleImportError(name, err, text)
            else:
                added.append(name)
                self.__modules[name] = Module(name, mod, deps, path)

        print_d("Rescanning done: %d added, %d removed, %d error(s)" %
                (len(added), len(removed), len(self.__failures)))

        return removed, added
