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
        obj.plugin_single_song(song)
        obj.plugin_song(song)
        obj.plugin_songs(songs)
        obj.plugin_single_album(album)
        obj.plugin_album(album)
        obj.plugin_albums(albums)
        obj.plugin_single_full_album(album)
        obj.plugin_full_album(album)
        obj.plugin_full_albums(albums)

    All matching provided callables on a single object are called in the above
    order if they match until one returns a true value.  A plugin should
    generally only provide one of the callables.

    The single_ variant is only called if a single song/album is selected.

    The singular tense is called once for each selected song/album, but the
    plural tense is called with a list of songs/albums.

    An album is a list of songs all with the same album tag.

    The full variants of album will expand the selection to all songs matching
    the album, and pass similarly to the normal variants.

    If a module defines __all__, only plugins whose names are listed in __all__
    will be detected. This makes using __all__ in a module-as-plugin impossible.
"""

def hascallable(obj, attr):
    return callable(getattr(obj, attr, None))

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

class PluginManager(object):
    """PluginManager manages all the plugins"""

    def __init__(self, folders=[]):
        self.scan = []
        self.scan.extend(folders)
        self.files = {}
        self.byfile = {}
        self.plugins = {}

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
                mtime = os.stat(pathname)[ST_MTIME]
                info = self.files.setdefault(name, [None, None])

                try:
                    sys.path.insert(0, scandir)
                    if info[1] is None or info[1] < mtime:
                        changes = True
                        if info[0] is None:
                            try:
                                mod = __import__(name)
                            except Exception, err:
                                import traceback; traceback.print_exc()
                                try: del sys.modules[name]
                                except KeyError: pass
                            else: info[0] = mod; self.load(name, mod)
                        else:
                            try: mod = reload(info[0])
                            except Exception, err:
                                import traceback; traceback.print_exc()
                            else: info[0] = mod; self.load(name, mod)
                finally:
                    del sys.path[0:1]
                info[1] = mtime

        return changes

    def load(self, name, mod):
        
        print 'bf', self.byfile
        print 'pl', self.plugins
        for pluginname in self.byfile.get(name, []):
            try: del self.plugins[pluginname]
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

            # if an object doesn't have at least one plugin method skip it
            for attr in all_callables:
                if hascallable(obj, attr): break
            else: continue

            pluginname = name + '.' + obj.PLUGIN_NAME
            self.byfile[name].append(pluginname)
            self.plugins[pluginname] = obj

    def list(self, selection):

        if len(selection) == 0:
            return []

        elif len(selection) == 1:
            plugins = []
            for plugin in self.plugins.values():
                for fn in all_callables:
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
                for fn in all_callables[1:]:
                    if not hascallable(plugin, fn): continue
                    elif albums and fn in callables['single']: continue
                    else: break
                else: continue
                plugins.append(plugin)
            return plugins
                    
    def invoke(self, plugin, selection):
        for fn in all_callables:
            if not hascallable(plugin, fn): continue

            if fn in callables['song_callables']:
                args = selection[:]

            elif fn in callables['album_callables']:
                albums = {}
                for song in selection: albums[song.comma('album')] = song
                args = albums.values()

            elif fn in callables['full_callables']:
                albums = {}
                for song in selection: albums[song.comma('album')] = song
                args = []
                for album in albums.keys():
                    args.append(list(library.query('album=/^%s$/c' % album)))

            if fn in callables['single']:
                if len(selection) == 1:
                    getattr(plugin, fn)(args[0])

            elif fn in callables['mapped']:
                map(getattr(plugin, fn), args)

            elif fn in callables['plural']:
                    getattr(plugin, fn)(args)
