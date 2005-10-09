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
        obj.PLUGIN_NAME (required)
        obj.PLUGIN_DESC (required)
        obj.PLUGIN_HINT (optional)
        obj.PLUGIN_ICON (optional)

    Callables: (one or more required)
        # manually invoked
        obj.plugin_single_song(song)
        obj.plugin_song(song)
        obj.plugin_songs(songs)
        obj.plugin_single_album(album)
        obj.plugin_album(album)
        obj.plugin_albums(albums)

        # event based callbacks
        obj.plugin_on_song_started(song)
        obj.plugin_on_song_ended(song, stopped)
        obj.plugin_on_changed(song)
        obj.plugin_on_removed(song)
        obj.plugin_on_missing(song)
        obj.plugin_on_refresh()
        obj.plugin_on_paused()
        obj.plugin_on_unpaused()
        obj.plugin_on_seek(song, msec)

    All matching provided callables on a single object are called in the above
    order if they match until one returns a true value.  A plugin should
    generally only provide one of the manually invoked callables, but it's quite
    reasonable to provide many event-based callbacks.

    If a module defines __all__, only plugins whose names are listed in __all__
    will be detected. This makes using __all__ in a module-as-plugin impossible.

    For manually invoked callbacks:
        The single_ variant is only called if a single song/album is selected.

        The singular tense is called once for each selected song/album, but the
        plural tense is called with a list of songs/albums.

        An album is a list of songs all with the same album tag.
"""

import util; from util import mtime
from traceback import print_exc

import gobject, gtk, qltk

def hascallable(obj, attr):
    return callable(getattr(obj, attr, None))

class SongWrapper(object):
    __slots__ = ['_song', '_updated', '_mtime', '_needs_write']
    def __init__(self, song):
        self._song = song
        self._updated = False
        self._needs_write = False

    def _was_updated(self): return self._updated

    def __setitem__(self, key, value):
        if key in self and self[key] == value: return
        self._updated = True
        self._needs_write = (self._needs_write or not key.startswith("~"))
        return self._song.__setitem__(key, value)

    def __getitem__(self, *args): return self._song.__getitem__(*args)
    def __cmp__(self, other): return cmp(self._song, other)
    def __contains__(self, key): return key in self._song
    def __call__(self, *args): return self._song(*args)
    def get(self, key): return self._song.get(key)
    def realkeys(self): return self._song.realkeys()
    def can_change(self, key): return self._song.can_change(key)
    def keys(self): return self._song.keys()
    def values(self): return self._song.values()
    def items(self): return self._song.items()
    def comma(self, key): return self._song.comma(key)
    def list(self, key): return self._song.list(key)
    def rename(self, newname): return self._song.rename(newname)
    def website(self): return self._song.website()
    def valid(self): return self._song.valid()
    def find_cover(self): return self._song.find_cover()

def ListWrapper(songs):
    return [(song and SongWrapper(song)) for song in songs]

class PluginManager(object):
    """PluginManager manages all the plugins"""

    # by being in here, you can tweak the behavior by subclassing and
    # overriding these class attributes
    all_callables = [
        'plugin_single_song', 'plugin_song', 'plugin_songs',
        'plugin_single_album', 'plugin_album', 'plugin_albums',
    ]

    callables = {
        'song_callables': all_callables[0:3],
        'album_callables': all_callables[3:6],
        'single': all_callables[0::3],
        'mapped': all_callables[1::3],
        'plural': all_callables[2::3],
    }

    all_events = [(s.replace('-', '_'), 'plugin_on_' + s.replace('-', '_'))
                  for s in gobject.signal_list_names(qltk.SongWatcher)]

    def __init__(self, watcher=None, folders=[]):
        self.scan = []
        self.scan.extend(folders)
        self.files = {}
        self.byfile = {}
        self.plugins = {}
        self.watcher = watcher

        self.events = {}
        invoke = self.invoke_event
        for event, handle in self.all_events:
            self.events[event] = {}
            if watcher:
                def handler(watcher, *args): invoke(args[-1], *args[:-1])
                watcher.connect(event, handler, event)

    def rescan(self):
        import os, sys, dircache, imp

        changes = False;

        justscanned = {}
        for scandir in self.scan:
            try: names = dircache.listdir(scandir)
            except OSError: continue
            for name in names:
                pathname = os.path.realpath(os.path.join(scandir, name))
                if not os.path.isdir(pathname):
                    name = name[: name.rfind('.')]
                if '.' in name or name in justscanned or name.startswith("_"):
                    continue
                else: justscanned[name] = True
                modified = mtime(pathname)
                info = self.files.setdefault(name, [None, None])

                try:
                    sys.path.insert(0, scandir)
                    if info[1] is None or info[1] < modified:
                        changes = True
                        if info[0] is None:
                            try: modinfo = imp.find_module(name)
                            except ImportError: continue
                            try:
                                mod = imp.load_module(name, *modinfo)
                            except Exception, err:
                                print_exc()
                                try: del sys.modules[name]
                                except KeyError: pass
                            else: info[0] = mod; self.load(name, mod)
                        else:
                            try: mod = reload(info[0])
                            except Exception, err:
                                print_exc()
                            else: info[0] = mod; self.load(name, mod)
                finally:
                    del sys.path[0:1]
                info[1] = modified

        self.restore()
        return changes

    def load(self, name, mod):        
        for pluginname in self.byfile.get(name, []):
            try: del self.plugins[pluginname]
            except KeyError: pass

        for events in self.events.values():
            try: del events[name]
            except KeyError: pass

        self.byfile[name] = []
        objects = [mod] + [getattr(mod, attr) for attr in
                            getattr(mod, '__all__', vars(mod))]
        for obj in objects:
            try: obj = obj()
            except TypeError:
                if obj is not mod: continue # let the module through
            except (KeyboardInterrupt,MemoryError):
                raise
            except:
                print_exc()
                continue

            # if an object doesn't have all required metadata, skip it
            try:
                for attr in ['PLUGIN_NAME', 'PLUGIN_DESC']:
                    getattr(obj, attr)
            except AttributeError:
                continue

            self.load_invokables(obj, name)
            self.load_events(obj, name)

    def restore(self):
        import config
        possible = config.get("plugins", "active").split("\n")
        for plugin in self.list():
            self.enable(plugin, plugin.PLUGIN_NAME in possible)

    def save(self):
        import config
        active = [plugin.PLUGIN_NAME for plugin in self.list()
                  if self.enabled(plugin)]
        config.set("plugins", "active", "\n".join(active))

    def load_invokables(self, obj, name):
        # if an object doesn't have at least one plugin method skip it
        for attr in self.all_callables:
            if hascallable(obj, attr): break
        else: return

        pluginname = name + '.' + obj.PLUGIN_NAME
        self.byfile[name].append(pluginname)
        self.plugins[pluginname] = obj

    def load_events(self, obj, name):
        for bin, attr in self.all_events:
            if hascallable(obj, attr):
                self.events[bin].setdefault(name, []).append(obj)

    def enable(self, plugin, enabled): plugin.PMEnFlag = bool(enabled)
    def enabled(self, plugin): return getattr(plugin, 'PMEnFlag', False)

    def list(self, selection=None):

        if selection is None:
            called = self.plugins.values()
            signaled = [plugin for handlers in self.events.values()
                        for ps in handlers.values() for plugin in ps]
            plugins = [(p.PLUGIN_NAME, p)
                        for p in dict.fromkeys(called + signaled).keys()]
            plugins.sort()
            return [p for (pn, p) in plugins]

        if len(selection) == 0:
            return []

        elif len(selection) == 1:
            plugins = []
            for plugin in self.plugins.values():
                if not self.enabled(plugin): continue
                for fn in self.all_callables:
                    if hascallable(plugin, fn): break
                else: continue
                plugins.append(plugin)
            return plugins

        else:
            albums = True
            album = selection[-1].comma('album')
            for song in selection:
                if album != song.comma('album'): break
            else: albums = False

            plugins = []
            for plugin in self.plugins.values():
                if not self.enabled(plugin): continue
                for fn in self.all_callables[1:]:
                    if not hascallable(plugin, fn): continue
                    elif albums and fn in self.callables['single']: continue
                    else: break
                else: continue
                plugins.append(plugin)
            return plugins
                    
    def invoke(self, plugin, selection):
        for fn in self.all_callables:
            if not hascallable(plugin, fn): continue

            if fn in self.callables['song_callables']:
                args = ListWrapper(selection)

            elif fn in self.callables['album_callables']:
                albums = {}
                for song in selection:
                    albums.setdefault(song.comma('album'),[]).append(song)
                args = [ListWrapper(album) for album in albums.values()]

            if fn in self.callables['single']:
                if len(selection) == 1:
                    try: getattr(plugin, fn)(args[0])
                    except Exception: print_exc()

            elif fn in self.callables['mapped']:
                try: map(getattr(plugin, fn), args)
                except Exception: print_exc()

            elif fn in self.callables['plural']:
                try: getattr(plugin, fn)(args)
                except Exception: print_exc()

            if fn in self.callables['song_callables']:
                self.check_change_and_refresh(args)
            elif fn in self.callables['album_callables']:
                self.check_change_and_refresh(sum(args, []))

    def check_change_and_refresh(self, args):
        updated = False
        songs = filter(None, args)
        needs_write = filter(lambda s: s._needs_write, songs)

        if needs_write:
            win = qltk.WritingWindow(None, len(needs_write))
            for song in needs_write:
                try: song._song.write()
                except Exception:
                    self.watcher.error(song._song)
                    qltk.ErrorMessage(
                        None, _("Unable to edit song"),
                        _("Saving <b>%s</b> failed. The file "
                          "may be read-only, corrupted, or you "
                          "do not have permission to edit it.")%(
                        util.escape(song('~basename')))).run()
                win.step()
            win.destroy()
            while gtk.events_pending(): gtk.main_iteration()

        for song in songs:
            if song._was_updated():
                self.watcher.changed([song._song])
                updated = True
            elif not song.valid():
                self.watcher.reload(song._song)
                updated = True
        if updated:
            self.watcher.refresh()

    def invoke_event(self, event, *args):
        try:
            args = list(args)
            if args and args[0]:
                if isinstance(args[0], dict): args[0] = SongWrapper(args[0])
                elif isinstance(args[0], list): args[0] = ListWrapper(args[0])
            for plugins in self.events[event].values():
                for plugin in plugins:
                    if not self.enabled(plugin): continue
                    handler = getattr(plugin, 'plugin_on_' + event, None)
                    if handler is not None:
                        try: handler(*args)
                        except Exception: print_exc()
        finally:
            if event not in ["removed", "missing", "changed"] and args:
                if isinstance(args[0], list):
                    self.check_change_and_refresh(args[0])
                else:
                    self.check_change_and_refresh([args[0]])

    def create_plugins_menu(self, songs):
        menu = gtk.Menu()
        plugins = [(plugin.PLUGIN_NAME, plugin) for plugin in self.list(songs)]
        plugins.sort()
        for name, plugin in plugins:
            if hasattr(plugin, 'PLUGIN_ICON'):
                b = qltk.MenuItem(name, plugin.PLUGIN_ICON)
            else:
                b = gtk.MenuItem(name)
            b.connect('activate', self.__plugin_activate, plugin, songs)

            menu.append(b)

        if menu.get_children():
            menu.show_all()
            return menu
        else:
            menu.destroy()

    def __plugin_activate(self, event, plugin, songs):
        self.invoke(plugin, songs)
