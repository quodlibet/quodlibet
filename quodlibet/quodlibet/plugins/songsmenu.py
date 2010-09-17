# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet import qltk
from quodlibet.util import print_exc
from quodlibet.plugins import ListWrapper, Manager

class SongsMenuPlugin(gtk.ImageMenuItem):
    """Plugins of this type are subclasses of gtk.ImageMenuItem.
    They will be added, in alphabetical order, to the "Plugins" menu
    that appears when songs or lists of songs are right-clicked.
    They provide one or more of the following instance methods:
    
        self.plugin_single_song(song)
        self.plugin_song(song)
        self.plugin_songs(songs)
        self.plugin_single_album(album)
        self.plugin_album(album)
        self.plugin_albums(albums)

    All matching provided callables on a single object are called in the
    above order if they match until one returns a true value. They are
    not called with real AudioFile objects, but rather wrappers that
    automatically detect metadata or disk changes, and save or reload
    the files as appropriate.

    The single_ variant is only called if a single song/album is selected.

    The singular tense is called once for each selected song/album, but the
    plural tense is called with a list of songs/albums.

    An album is a list of songs all with the same album, labelid,
    and/or musicbrainz_albumid tags (like in the Album List).

    To make your plugin insensitive if unsupported songs are selected,
    a method that takes a list of songs and returns True or False to set
    the sensitivity of the menu entry:
        self.plugin_handles(songs)

    When these functions are called, the self.plugin_window will be
    available. This is the gtk.Window the plugin was invoked from. This
    provides access to two important widgets, self.plugin_window.browser
    and self.plugin_window.songlist.

    All of this is managed by the constructor for SongsMenuPlugin, so
    make sure it gets called if you override it (you shouldn't have to).
    """

    plugin_single_song = None
    plugin_song = None
    plugin_songs = None
    plugin_single_album = None
    plugin_album = None
    plugin_albums = None

    __initialized = False
    def __init__(self, songs):
        super(SongsMenuPlugin, self).__init__(self.PLUGIN_NAME)
        self.__initialized = True
        try: i = gtk.image_new_from_stock(self.PLUGIN_ICON, gtk.ICON_SIZE_MENU)
        except AttributeError: pass
        else: self.set_image(i)
        self.set_sensitive(bool(self.plugin_handles(songs)))

    @property
    def initialized(self):
        # If the GObject __init__ method is bypassed, it can cause segfaults.
        # This explicitly prevents a bad plugin from taking down the app.
        return self.__initialized

    def plugin_handles(self, songs):
        return True

class SongsMenuPlugins(Manager):
    Kinds = [SongsMenuPlugin]

    def Menu(self, library, parent, songs):
        songs = ListWrapper(songs)
        parent = qltk.get_top_parent(parent)

        albums = {}
        for song in songs:
            key = song.album_key
            if key not in albums:
                albums[key] = []
            albums[key].append(song)

        albums = albums.values()
        map(list.sort, albums)

        attrs = ['plugin_song', 'plugin_songs',
                 'plugin_album', 'plugin_albums']

        if len(songs) == 1: attrs.append('plugin_single_song')
        if len(albums) == 1: attrs.append('plugin_single_album')

        items = []
        kinds = self.find_subclasses(SongsMenuPlugin)
        kinds.sort(key=lambda plugin: plugin.PLUGIN_ID)
        for Kind in kinds:
            usable = max([callable(getattr(Kind, s)) for s in attrs])
            if usable:
                try: items.append(Kind(songs))
                except: print_exc()
        items = filter(lambda i: i.initialized, items)

        if items:
            menu = gtk.Menu()
            for item in items:
                try:
                    menu.append(item)
                    args = (library, parent, songs, albums)
                    if item.get_submenu():
                        for subitem in item.get_submenu().get_children():
                            subitem.connect_object(
                                'activate', self.__handle, item, *args)
                    else:
                        item.connect('activate', self.__handle, *args)
                except:
                    print_exc()
                    item.destroy()

        else: menu = None
        return menu

    def __handle(self, plugin, library, parent, songs, albums):
        if len(songs) == 0: return

        plugin.plugin_window = parent
        try:
            if len(songs) == 1 and callable(plugin.plugin_single_song):
                try: ret = plugin.plugin_single_song(songs[0])
                except Exception: print_exc()
                else:
                    if ret: return
            if callable(plugin.plugin_song):
                try: ret = map(plugin.plugin_song, songs)
                except Exception: print_exc()
                else:
                    if max(ret): return
            if callable(plugin.plugin_songs):
                try: ret = plugin.plugin_songs(songs)
                except Exception: print_exc()
                else:
                    if ret: return

            if len(albums) == 1 and callable(plugin.plugin_single_album):
                try: ret = plugin.plugin_single_album(albums[0])
                except Exception: print_exc()
                else:
                    if ret: return
            if callable(plugin.plugin_album):
                try: ret = map(plugin.plugin_album, albums)
                except Exception: print_exc()
                else:
                    if max(ret): return
            if callable(plugin.plugin_albums):
                try: ret = plugin.plugin_albums(albums)
                except Exception: print_exc()
                else:
                    if ret: return

        finally:
            del(plugin.plugin_window)
            self._check_change(library, parent, filter(None, songs))
