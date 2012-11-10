# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet import qltk

from quodlibet.util import print_exc
from quodlibet.qltk.delete import DeleteDialog
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.plugins import PluginManager
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.songwrapper import ListWrapper, check_wrapper_changed


class SongsMenuPluginHandler(object):
    def __init__(self):
        self.__plugins = []

    def Menu(self, library, parent, songs):
        songs = ListWrapper(songs)
        parent = qltk.get_top_parent(parent)

        attrs = ['plugin_song', 'plugin_songs',
                 'plugin_album', 'plugin_albums']

        if len(songs) == 1: attrs.append('plugin_single_song')

        last = (songs and songs[-1]) or None
        for song in songs:
            if song.album_key != last.album_key:
                break
            last = song
        else:
            attrs.append('plugin_single_album')

        items = []
        kinds = self.__plugins
        kinds.sort(key=lambda plugin: plugin.PLUGIN_ID)
        for Kind in kinds:
            usable = max([callable(getattr(Kind, s)) for s in attrs])
            if usable:
                try: items.append(Kind(songs, library, parent))
                except:
                    print_e("Couldn't initalise song plugin %s. Stack trace:" % Kind)
                    print_exc()
        items = filter(lambda i: i.initialized, items)

        if items:
            menu = gtk.Menu()
            for item in items:
                try:
                    menu.append(item)
                    args = (library, parent, songs)
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

    def __get_albums(self, songs):
        albums = {}
        for song in songs:
            key = song.album_key
            if key not in albums:
                albums[key] = []
            albums[key].append(song)

        albums = albums.values()
        map(list.sort, albums)
        return albums

    def handle(self, plugin_id, library, parent, songs):
        """Start a song menu plugin directly without a menu"""

        for plugin in self.__plugins:
            if plugin.PLUGIN_ID == plugin_id:
                songs = ListWrapper(songs)
                try:
                    plugin = plugin(songs, library, parent)
                except Exception:
                    print_exc()
                else:
                    self.__handle(plugin, library, parent, songs)
                return

    def __handle(self, plugin, library, parent, songs):
        if len(songs) == 0: return

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

            if max(map(callable,(plugin.plugin_single_album,
                plugin.plugin_album, plugin.plugin_albums))):
                albums = self.__get_albums(songs)

            if callable(plugin.plugin_single_album) and len(albums) == 1:
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
            check_wrapper_changed(library, parent, filter(None, songs))

    def plugin_handle(self, plugin):
        return issubclass(plugin, SongsMenuPlugin)

    def plugin_enable(self, plugin, obj):
        self.__plugins.append(plugin)

    def plugin_disable(self, plugin):
        self.__plugins.remove(plugin)


class SongsMenu(gtk.Menu):
    __accels = gtk.AccelGroup()

    plugins = SongsMenuPluginHandler()

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.plugins)

    def __init__(self, library, songs, plugins=True, playlists=True,
                 queue=True, devices=True, remove=True, delete=False,
                 edit=True, accels=None, parent=None):
        super(SongsMenu, self).__init__()

        # The library may actually be a librarian; if it is, use it,
        # otherwise find the real librarian.
        librarian = getattr(library, 'librarian', library)

        if plugins:
            submenu = self.plugins.Menu(librarian, parent, songs)
            if submenu is not None:
                b = qltk.MenuItem(_("_Plugins"), gtk.STOCK_EXECUTE)
                self.append(b)
                b.set_submenu(submenu)
                self.append(gtk.SeparatorMenuItem())

        in_lib = True
        can_add = True
        is_file = True
        for song in songs:
            if song not in library: in_lib = False
            if not song.can_add: can_add = False
            if not song.is_file: is_file = False

        self.separate()

        if playlists:
            # Needed here to avoid a circular import; most browsers use
            # a SongsMenu, but SongsMenu needs access to the playlist
            # browser for this item.

            # FIXME: Two things are now importing browsers, so we need
            # some kind of inversion of control here.
            from quodlibet import browsers
            try: submenu = browsers.playlists.Menu(songs, parent)
            except AttributeError: pass
            else:
                b = qltk.MenuItem(_("_Add to Playlist"), gtk.STOCK_ADD)
                b.set_sensitive(can_add)
                b.set_submenu(submenu)
                self.append(b)
        if queue:
            b = qltk.MenuItem(_("Add to _Queue"), gtk.STOCK_ADD)
            b.connect('activate', self.__enqueue, songs)
            if accels is not None:
                key, val = gtk.accelerator_parse("<ctrl>Return")
                b.add_accelerator(
                    'activate', accels, key, val, gtk.ACCEL_VISIBLE)
            self.append(b)
            b.set_sensitive(can_add)

        if devices:
            from quodlibet import browsers
            try: browsers.media
            except AttributeError: pass
            else:
                if browsers.media.MediaDevices in browsers.browsers:
                    submenu = browsers.media.Menu(songs, library)
                    b = qltk.MenuItem(_("_Copy to Device"), gtk.STOCK_COPY)
                    b.set_sensitive(can_add and len(submenu) > 0)
                    b.set_submenu(submenu)
                    self.append(b)

        if remove or delete or edit:
            self.separate()

        if remove:
            b = qltk.MenuItem(_("_Remove from library"), gtk.STOCK_REMOVE)
            if callable(remove):
                b.connect_object('activate', remove, songs)
            else:
                b.connect('activate', self.__remove, songs, library)
                b.set_sensitive(in_lib)
            self.append(b)

        if delete:
            b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            if callable(delete):
                b.connect_object('activate', delete, songs)
            else:
                b.connect('activate', self.__delete, songs, librarian)
                b.set_sensitive(is_file)
            self.append(b)

        if edit:
            b = qltk.MenuItem(_("Edit _Tags"), gtk.STOCK_PROPERTIES)
            if accels is not None:
                key, val = gtk.accelerator_parse("<alt>Return")
                b.add_accelerator(
                    'activate', accels, key, val, gtk.ACCEL_VISIBLE)
            b.connect_object(
                'activate', SongProperties, librarian, songs, parent)
            self.append(b)

            b = gtk.ImageMenuItem(gtk.STOCK_INFO)
            if accels is not None:
                b.add_accelerator('activate', accels, ord('I'),
                                  gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
            b.connect_object('activate', Information, librarian, songs, parent)
            self.append(b)

        self.connect_object('selection-done', gtk.Menu.destroy, self)

    def separate(self):
        if not self.get_children(): return
        elif not isinstance(self.get_children()[-1], gtk.SeparatorMenuItem):
            self.append(gtk.SeparatorMenuItem())

    def preseparate(self):
        if not self.get_children(): return
        elif not isinstance(self.get_children()[0], gtk.SeparatorMenuItem):
            self.prepend(gtk.SeparatorMenuItem())

    def __remove(self, item, songs, library):
        library.remove(set(songs))

    def __enqueue(self, item, songs):
        songs = filter(lambda s: s.can_add, songs)
        if songs:
            from quodlibet import app
            app.window.playlist.enqueue(songs)

    def __delete(self, item, songs, library):
        songs = set(songs)
        files = [song["~filename"] for song in songs]
        d = DeleteDialog(None, files)
        removed = dict.fromkeys(d.run())
        d.destroy()
        removed = filter(lambda s: s["~filename"] in removed, songs)
        if removed:
            try: library.librarian.remove(removed)
            except AttributeError:
                library.remove(removed)
