# -*- coding: utf-8 -*-
# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import sys
import imp

from traceback import format_exception

if sys.version_info < (2, 4):
    from sets import Set as set

class Manager(object):
    """A generalized plugin manager. It scans directories for importable
    modules/packages and extracts all objects from them.

    Objects are cached and not imported again unless their mtime changes.

    If a module defines __all__, only objects whose names are listed in
    __all__ will be detected. Otherwise, any object that has a name beginning
    with '_' is skipped."""

    instances = {}

    Kinds = []

    def __init__(self, folders=[], name=None):
        self.scan = []
        self.scan.extend(folders)
        self.__files = {}
        self.__plugins = {}
        self.__failures = {}
        if name: self.instances[name] = self

    def rescan(self):
        """Check directories for new or changed plugins."""

        justscanned = {}
        for scandir in self.scan:
            try: names = os.listdir(scandir)
            except OSError: continue
            for name in names:
                pathname = os.path.realpath(os.path.join(scandir, name))
                if not os.path.isdir(pathname):
                    name = name[: name.rfind('.')]
                if '.' in name or name in justscanned or name.startswith("_"):
                    continue
                else: justscanned[name] = True
                try: modified = os.path.getmtime(pathname)
                except EnvironmentError: continue
                info = self.__files.setdefault(name, [None, None])

                try:
                    sys.path.insert(0, scandir)
                    if info[1] is None or info[1] < modified:
                        if info[0] is None:
                            try: modinfo = imp.find_module(name)
                            except ImportError: continue
                            try:
                                mod = imp.load_module(name, *modinfo)
                            except Exception, err:
                                self.__failures[name] = \
                                    format_exception(*sys.exc_info())
                                try: del sys.modules[name]
                                except KeyError: pass
                            else: info[0] = mod; self._load(name, mod)
                        else:
                            try: mod = reload(info[0])
                            except Exception, err:
                                self.__failures[name] = \
                                    format_exception(*sys.exc_info())
                            else: info[0] = mod; self._load(name, mod)
                finally:
                    del sys.path[0:1]
                info[1] = modified
        self.restore()

    def restore(self):
        import config
        key = "active_" + str(type(self).__name__)
        try: possible = config.get("plugins", key).splitlines()
        except config.error: pass
        else:
            for plugin in self.list():
                self.enable(plugin, plugin.PLUGIN_NAME in possible)

    def save(self):
        import config
        key = "active_" + str(type(self).__name__)
        active = [plugin.PLUGIN_NAME for plugin in self.list()
                  if self.enabled(plugin)]
        config.set("plugins", key, "\n".join(active))

    def _load(self, name, module):
        self.__failures.pop(name, None)
        try: objs = [getattr(module, attr) for attr in module.__all__]
        except AttributeError:
            objs = [getattr(module, attr) for attr in vars(module)
                    if not attr.startswith("_")]
        objs = filter(lambda x: isinstance(x, type), objs)
        self.__plugins[name] = objs

    def enable(self, plugin, enabled): plugin.PMEnFlag = bool(enabled)
    def enabled(self, plugin): return getattr(plugin, 'PMEnFlag', False)

    def list(self):
        kinds = set()
        for Kind in self.Kinds:
            kinds.update(self.find_subclasses(Kind, all=True))
        return list(kinds)

    def find_subclasses(self, Kind, all=False):
        """Return all classes in all plugins that subclass 'Kind'."""
        kinds = []
        for plugin in self.__plugins.values():
            for obj in plugin:
                try:
                    if issubclass(obj, Kind) and obj is not Kind:
                        kinds.append(obj)
                except TypeError: pass

        for Kind in kinds:
            try: Kind.PLUGIN_NAME
            except AttributeError:
                Kind.PLUGIN_NAME = Kind.__name__

        if not all:
            kinds = filter(self.enabled, kinds)

        return kinds

    def list_failures(self):
        return self.__failures.copy()
