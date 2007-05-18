# -*- coding: utf-8 -*-
# Copyright 2005 Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

"""
Plugins are objects (generally classes or modules) that have the following
characteristics:

    Attributes:
        obj.PLUGIN_ID (required)
        obj.PLUGIN_NAME (required, defaults to ID)
        obj.PLUGIN_DESC (required)
        obj.PLUGIN_ICON (optional)

    The name should be a human-readable name, potentially marked for
    translation. The ID does not need to be human readable, and should
    be the same regardless of locale.

    If a module defines __all__, only plugins whose names are listed in __all__
    will be detected. This makes using __all__ in a module-as-plugin impossible.
"""

import glob
import imp
import os
import sys

import gtk

from quodlibet import config
from quodlibet import qltk
from quodlibet import util

from traceback import format_exception

from quodlibet.qltk.wlw import WritingWindow

def hascallable(obj, attr):
    return callable(getattr(obj, attr, None))

class SongWrapper(object):
    __slots__ = ['_song', '_updated', '_needs_write']

    def __init__(self, song):
        self._song = song
        self._updated = False
        self._needs_write = False

    def _was_updated(self):
        return self._updated

    def __setitem__(self, key, value):
        if key in self and self[key] == value: return
        self._updated = True
        self._needs_write = (self._needs_write or not key.startswith("~"))
        return self._song.__setitem__(key, value)

    def __delitem__(self, key):
        retval = self._song.__delitem__(key)
        self._updated = True
        self._needs_write = (self._needs_write or not key.startswith("~"))
        return retval

    def __getattr__(self, attr):
        return getattr(self._song, attr)

    def __setattr__(self, attr, value):
        # Don't set our attributes on the song. However, we only want to
        # set attributes the song already has. So, if the attribute
        # isn't one of ours, and isn't one of the song's, hand it off
        # to our parent's attribute handler for error handling.
        if attr in self.__slots__:
            return super(SongWrapper, self).__setattr__(attr, value)
        elif hasattr(self._song, attr):
            return setattr(self._song, attr, value)
        else:
            return super(SongWrapper, self).__setattr__(attr, value)

    def __cmp__(self, other):
        try: return cmp(self._song, other._song)
        except: return cmp(self._song, other)

    def __getitem__(self, *args): return self._song.__getitem__(*args)
    def __contains__(self, key): return key in self._song
    def __call__(self, *args): return self._song(*args)

    def update(self, other):
        self._updated = True
        self._needs_write = True
        return self._song.update(other)

    def rename(self, newname):
        self._updated = True
        return self._song.rename(newname)

def ListWrapper(songs):
    def wrap(song):
        if song is None: return None
        else: return SongWrapper(song)
    return map(wrap, songs)

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
        self._plugins = {}
        self.__failures = {}
        if name: self.instances[name] = self

    def rescan(self):
        """Check directories for new or changed plugins."""

        for scandir in self.scan:
            try: names = glob.glob(os.path.join(scandir, "[!_]*.py"))
            except OSError: continue
            for pathname in names:
                name = os.path.basename(pathname)
                name = name[:name.rfind(".")]
                try: modified = os.path.getmtime(pathname)
                except EnvironmentError: continue
                info = self.__files.setdefault(name, [None, None])

                try:
                    sys.path.insert(0, scandir)
                    if info[1] is None or info[1] != modified:
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
                            else:
                                info[0] = mod
                                self._load(name, mod)
                        else:
                            try: mod = reload(info[0])
                            except Exception, err:
                                self.__failures[name] = \
                                    format_exception(*sys.exc_info())
                            else:
                                info[0] = mod
                                self._load(name, mod)
                finally:
                    del sys.path[0:1]
                info[1] = modified
        self.restore()

    def restore(self):
        key = "active_" + str(type(self).__name__)
        try: possible = config.get("plugins", key).splitlines()
        except config.error: pass
        else:
            for plugin in self.list():
                self.enable(plugin, plugin.PLUGIN_ID in possible)

    def save(self):
        key = "active_" + str(type(self).__name__)
        active = [plugin.PLUGIN_ID for plugin in self.list()
                  if self.enabled(plugin)]
        config.set("plugins", key, "\n".join(active))

    def _load(self, name, module):
        self.__failures.pop(name, None)
        try: objs = [getattr(module, attr) for attr in module.__all__]
        except AttributeError:
            objs = [getattr(module, attr) for attr in vars(module)
                    if not attr.startswith("_")]
        objs = filter(lambda x: isinstance(x, type), objs)
        self._plugins[name] = objs

    def enable(self, plugin, enabled):
        plugin.__enabled = bool(enabled)

    def enabled(self, plugin):
        try: return plugin.__enabled
        except AttributeError: return False

    def list(self):
        kinds = set()
        for Kind in self.Kinds:
            kinds.update(self.find_subclasses(Kind, all=True))
        return list(kinds)

    def find_subclasses(self, Kind, all=False):
        """Return all classes in all plugins that subclass 'Kind'."""
        kinds = []
        for plugin in self._plugins.values():
            for obj in plugin:
                try:
                    if issubclass(obj, Kind) and obj is not Kind:
                        kinds.append(obj)
                except TypeError: pass

        for Kind in kinds:
            try: Kind.PLUGIN_ID
            except AttributeError:
                try: Kind.PLUGIN_ID = Kind.PLUGIN_NAME
                except AttributeError:
                    Kind.PLUGIN_ID = Kind.__name__

            try: Kind.PLUGIN_NAME
            except AttributeError:
                Kind.PLUGIN_NAME = Kind.PLUGIN_ID

        if not all:
            kinds = filter(self.enabled, kinds)

        return kinds

    def list_failures(self):
        return self.__failures.copy()

    def _check_change(self, library, parent, songs):
        needs_write = filter(lambda s: s._needs_write, songs)

        if needs_write:
            win = WritingWindow(parent, len(needs_write))
            for song in needs_write:
                try: song._song.write()
                except Exception:
                    qltk.ErrorMessage(
                        None, _("Unable to edit song"),
                        _("Saving <b>%s</b> failed. The file "
                          "may be read-only, corrupted, or you "
                          "do not have permission to edit it.")%(
                        util.escape(song('~basename')))).run()
                win.step()
            win.destroy()
            while gtk.events_pending():
                gtk.main_iteration()

        changed = []
        for song in songs:
            needs_reload = []
            if song._was_updated(): changed.append(song._song)
            elif not song.valid() and song.exists():
                library.reload(song._song)
        library.changed(changed)
