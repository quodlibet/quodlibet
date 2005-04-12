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
        obj.plugin_single_full_album(album)
        obj.plugin_full_album(album)
        obj.plugin_full_albums(albums)

        # event based callbacks
        obj.plugin_on_song_started(song)
        obj.plugin_on_song_ended(song, stopped)
        obj.plugin_on_changed(song)
        obj.plugin_on_removed(song)
        obj.plugin_on_missing(song)
        obj.plugin_on_refresh()
        obj.plugin_on_paused()
        obj.plugin_on_unpaused()

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

        The full variants of album will expand the selection to all songs
        matching the album, and pass similarly to the normal variants.
"""

from util import mtime
from traceback import print_exc
def hascallable(obj, attr):
    return callable(getattr(obj, attr, None))

class SongWrapper(object):
    __slots__ = ['_song', '_updated', '_mtime']
    def __init__(self, song):
        self._song = song
        self._updated = False
        self._mtime = mtime(self["~filename"])

    def _was_updated(self): return self._updated
    def _was_changed(self): return self._mtime < mtime(self["~filename"])

    def __setitem__(self, *args):
        self.__updated = True
        if self.__song.can_change(args[0]):
            return self.__song.__setitem__(*args)
        else:
            raise ValueError, "Can not set %s" % args[0]

    def __getitem__(self, *args): return self._song.__getitem__(*args)
    def __cmp__(self, other): return cmp(self._song, other)
    def __contains__(self, key): return key in self._song
    def __call__(self, *args): return self._song(*args)
    def realkeys(self): return self._song.realkeys()
    def comma(self, key): return self._song.comma(key)
    def list(self, key): return self._song.list(key)
    def rename(self, newname): return self._song.rename(newname)
    def website(self): return self._song.website()
    def find_cover(self): return self._song.find_cover()

class ListWrapper(list):
    def __new__(cls, songs): return [SongWrapper(song) for song in songs]

class PluginManager(object):
    """PluginManager manages all the plugins"""

    # by being in here, you can tweak the behavior by subclassing and overriding
    # these class attributes
    all_callables = [
        'plugin_single_song', 'plugin_song', 'plugin_songs',
        'plugin_single_album', 'plugin_album', 'plugin_albums',
        'plugin_single_full_album', 'plugin_full_album', 'plugin_full_albums'
    ]

    callables = {
        'song_callables': all_callables[0:3],
        'album_callables': all_callables[3:6],
        'full_callables': all_callables[6:9],
        'single': all_callables[0::3],
        'mapped': all_callables[1::3],
        'plural': all_callables[2::3],
    }

    all_events = [
        ('changed', 'plugin_on_changed'),
        ('removed', 'plugin_on_removed'),
        ('refresh', 'plugin_on_refresh'),
        ('song_started', 'plugin_on_song_started'),
        ('song_ended', 'plugin_on_song_ended'),
        ('paused', 'plugin_on_paused'),
        ('unpaused', 'plugin_on_unpaused'),
        ('missing', 'plugin_on_missing'),
    ]

    def __init__(self, watcher=None, folders=[]):
        self.scan = []
        self.scan.extend(folders)
        self.files = {}
        self.byfile = {}
        self.plugins = {}
        self.watcher = watcher

        self.events = {}
        for event in 'changed removed refresh song_started song_ended ' \
                'paused unpaused missing'.split():
            self.events[event] = {}
            handler = getattr(self, 'on_' + event, None)
            if handler:
                watcher.connect(event, handler)

    def rescan(self):
        import os, sys, dircache
        from stat import ST_MTIME

        changes = False;

        justscanned = {}
        for scandir in self.scan:
            try: names = dircache.listdir(scandir)
            except OSError, err: continue
            for name in names:
                pathname = os.path.realpath(os.path.join(scandir, name))
                if not os.path.isdir(pathname):
                    name = name[: name.rfind('.')]
                if '.' in name or name in justscanned: continue
                else: justscanned[name] = True
                modified = mtime(pathname)
                info = self.files.setdefault(name, [None, None])

                try:
                    sys.path.insert(0, scandir)
                    if info[1] is None or info[1] < modified:
                        changes = True
                        if info[0] is None:
                            try:
                                mod = __import__(name)
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

            # if an object doesn't have all required metadata, skip it
            try:
                for attr in ['PLUGIN_NAME', 'PLUGIN_DESC']:
                    getattr(obj, attr)
            except AttributeError:
                continue

            self.load_invokables(obj, name)
            self.load_events(obj, name)

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
                self.events[bin].setdefault(name, []).append(getattr(obj, attr))

    def list(self, selection):

        if len(selection) == 0:
            return []

        elif len(selection) == 1:
            plugins = []
            for plugin in self.plugins.values():
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
                for song in selection: albums[song.comma('album')] = song
                args = [ListWrapper(album) for album in albums.values()]

            elif fn in self.callables['full_callables']:
                albums = {}
                for song in selection: albums[song.comma('album')] = song
                args = []
                for album in albums.keys():
                    args.append(ListWrapper(library.query('album=/^%s$/c' % album)))

            if fn in self.callables['single']:
                if len(selection) == 1:
                    try:
                        if getattr(plugin, fn)(args[0]): break
                    except Exception:
                        print_exc()

            elif fn in self.callables['mapped']:
                try:
                    if map(getattr(plugin, fn), args): break
                except Exception:
                    print_exc()

            elif fn in self.callables['plural']:
                try:
                    if getattr(plugin, fn)(args): break
                except Exception:
                    print_exc()

        self.check_change_and_refresh(args)

    def check_change_and_refresh(self, args):
        updated = False
        for song in args:
            if song._was_changed():
                self.watcher.changed(song._song)
                updated = True
        if updated:
            self.watcher.refresh()

    def invoke_event(self, event, *args):
        try:
            try: args = [SongWrapper(args[0])] + list(args[1:])
            except IndexError: pass
            for handlers in self.events[event].values():
                for handler in handlers:
                    try: handler(*args)
                    except Exception: print_exc()
        finally:
            self.check_change_and_refresh(args[0:1])

    def on_changed(self, watcher, song):
        self.invoke_event('changed', song)

    def on_removed(self, watcher, song):
        self.invoke_event('removed', song)

    def on_refresh(self, watcher):
        self.invoke_event('refresh')

    def on_song_started(self, watcher, song):
        self.invoke_event('song_started', song)

    def on_song_ended(self, watcher, song, stopped):
        self.invoke_event('song_ended', song, stopped)

    def on_paused(self, watcher):
        self.invoke_event('paused')

    def on_unpaused(self, watcher):
        self.invoke_event('unpaused')

    def on_missing(self, watcher, song):
        self.invoke_event('missing', song)
