# Copyright 2006 Joe Wreschnig
#      2013-2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk
from quodlibet.qltk.msg import confirm_action

from quodlibet import qltk

from quodlibet.util import print_exc
from quodlibet.qltk.delete import TrashMenuItem, trash_songs
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.x import SeparatorMenuItem
from quodlibet.plugins import PluginManager, PluginHandler
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.songwrapper import ListWrapper, check_wrapper_changed


class SongsMenuPluginHandler(PluginHandler):

    def __init__(self, confirmer):
        self.__plugins = []
        # The method to call for confirmations of risky multi-invocations
        self.confirm_multiple = confirmer

    def Menu(self, library, parent, songs):
        songs = ListWrapper(songs)
        parent = qltk.get_top_parent(parent)

        attrs = ['plugin_song', 'plugin_songs',
                 'plugin_album', 'plugin_albums']

        if len(songs) == 1:
            attrs.append('plugin_single_song')

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
                try:
                    items.append(Kind(songs, library, parent))
                except:
                    print_e("Couldn't initialise song plugin %s. Stack trace:"
                            % Kind)
                    print_exc()
        items = filter(lambda i: i.initialized, items)

        if items:
            menu = Gtk.Menu()
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

        else:
            menu = None
        return menu

    def __get_albums(self, songs):
        albums = {}
        for song in songs:
            key = song.album_key
            if key not in albums:
                albums[key] = []
            albums[key].append(song)

        albums = albums.values()
        for album in albums:
            album.sort()
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
        if len(songs) == 0:
            return

        try:
            if len(songs) == 1 and callable(plugin.plugin_single_song):
                try:
                    ret = plugin.plugin_single_song(songs[0])
                except Exception:
                    print_exc()
                else:
                    if ret:
                        return
            if callable(plugin.plugin_song):
                total = len(songs)
                if total > plugin.MAX_INVOCATIONS:
                    msg = ngettext("Are you sure you want to run "
                                       "the \"%s\" plugin on %d song?",
                                   "Are you sure you want to run "
                                       "the \"%s\" plugin on %d songs?",
                                   total) % (plugin.PLUGIN_ID, total)
                    if not self.confirm_multiple(msg):
                        return
                try:
                    ret = map(plugin.plugin_song, songs)
                except Exception:
                    print_exc()
                else:
                    if max(ret):
                        return
            if callable(plugin.plugin_songs):
                try:
                    ret = plugin.plugin_songs(songs)
                except Exception:
                    print_exc()
                else:
                    if ret:
                        return

            if plugin.handles_albums:
                albums = self.__get_albums(songs)
                total = len(albums)
                if total > plugin.MAX_INVOCATIONS:
                    msg = ngettext("Are you sure you want to run "
                                       "the \"%s\" plugin on %d album?",
                                   "Are you sure you want to run "
                                       "the \"%s\" plugin on %d albums?",
                                   total) % (plugin.PLUGIN_ID, total)
                    if not self.confirm_multiple(msg):
                        return

            if callable(plugin.plugin_single_album) and len(albums) == 1:
                try:
                    ret = plugin.plugin_single_album(albums[0])
                except Exception:
                    print_exc()
                else:
                    if ret:
                        return
            if callable(plugin.plugin_album):
                try:
                    ret = map(plugin.plugin_album, albums)
                except Exception:
                    print_exc()
                else:
                    if max(ret):
                        return
            if callable(plugin.plugin_albums):
                try:
                    ret = plugin.plugin_albums(albums)
                except Exception:
                    print_exc()
                else:
                    if ret:
                        return

        finally:
            check_wrapper_changed(library, parent, filter(None, songs))

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, SongsMenuPlugin)

    def plugin_enable(self, plugin):
        self.__plugins.append(plugin.cls)

    def plugin_disable(self, plugin):
        self.__plugins.remove(plugin.cls)


class SongsMenu(Gtk.Menu):
    plugins = SongsMenuPluginHandler(confirm_action)

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.plugins)

    def __init__(self, library, songs, plugins=True, playlists=True,
                 queue=True, devices=True, remove=True, delete=False,
                 edit=True, parent=None):
        super(SongsMenu, self).__init__()

        # The library may actually be a librarian; if it is, use it,
        # otherwise find the real librarian.
        librarian = getattr(library, 'librarian', library)

        if plugins:
            submenu = self.plugins.Menu(librarian, parent, songs)
            if submenu is not None:
                b = qltk.MenuItem(_("_Plugins"), Gtk.STOCK_EXECUTE)
                self.append(b)
                b.set_submenu(submenu)
                self.append(SeparatorMenuItem())

        in_lib = True
        can_add = True
        is_file = True
        for song in songs:
            if song not in library:
                in_lib = False
            if not song.can_add:
                can_add = False
            if not song.is_file:
                is_file = False

        self.separate()

        if playlists:
            # Needed here to avoid a circular import; most browsers use
            # a SongsMenu, but SongsMenu needs access to the playlist
            # browser for this item.

            # FIXME: Two things are now importing browsers, so we need
            # some kind of inversion of control here.
            from quodlibet import browsers
            try:
                submenu = browsers.playlists.main.Menu(songs, parent)
            except AttributeError as e:
                print_w("Couldn't get Playlists menu: %s" % e)
            else:
                b = qltk.MenuItem(_("_Add to Playlist"), Gtk.STOCK_ADD)
                b.set_sensitive(can_add)
                b.set_submenu(submenu)
                self.append(b)
        if queue:
            b = qltk.MenuItem(_("Add to _Queue"), Gtk.STOCK_ADD)
            b.connect('activate', self.__enqueue, songs)
            qltk.add_fake_accel(b, "<ctrl>Return")
            self.append(b)
            b.set_sensitive(can_add)

        if devices:
            from quodlibet import browsers
            try:
                browsers.media
            except AttributeError:
                pass
            else:
                if browsers.media.MediaDevices in browsers.browsers:
                    submenu = browsers.media.Menu(songs, library)
                    b = qltk.MenuItem(_("_Copy to Device"), Gtk.STOCK_COPY)
                    b.set_sensitive(can_add and len(submenu) > 0)
                    b.set_submenu(submenu)
                    self.append(b)

        if remove or delete:
            self.separate()

        if remove:
            b = qltk.MenuItem(_("_Remove from library"), Gtk.STOCK_REMOVE)
            if callable(remove):
                b.connect_object('activate', remove, songs)
            else:
                b.connect('activate', self.__remove, songs, library)
                b.set_sensitive(in_lib)
            self.append(b)

        if delete:
            if callable(delete):
                b = Gtk.ImageMenuItem(Gtk.STOCK_DELETE, use_stock=True)
                b.connect_object('activate', delete, songs)
            else:
                b = TrashMenuItem()
                b.connect_object('activate', trash_songs,
                                 parent, songs, librarian)
                b.set_sensitive(is_file)
            self.append(b)

        if edit:
            self.separate()
            b = qltk.MenuItem(_("Edit _Tags"), Gtk.STOCK_PROPERTIES)
            qltk.add_fake_accel(b, "<alt>Return")

            def song_properties_cb(menu_item):
                window = SongProperties(librarian, songs, parent)
                window.show()

            b.connect('activate', song_properties_cb)
            self.append(b)

            b = Gtk.ImageMenuItem(label=Gtk.STOCK_INFO, use_stock=True)
            qltk.add_fake_accel(b, "<ctrl>I")

            def information_cb(menu_item):
                window = Information(librarian, songs, parent)
                window.show()
            b.connect('activate', information_cb)
            self.append(b)

        self.connect_object('selection-done', Gtk.Menu.destroy, self)

    def separate(self):
        if not self.get_children():
            return
        elif not isinstance(self.get_children()[-1], Gtk.SeparatorMenuItem):
            self.append(SeparatorMenuItem())

    def preseparate(self):
        if not self.get_children():
            return
        elif not isinstance(self.get_children()[0], Gtk.SeparatorMenuItem):
            self.prepend(SeparatorMenuItem())

    def __remove(self, item, songs, library):
        library.remove(set(songs))

    def __enqueue(self, item, songs):
        songs = filter(lambda s: s.can_add, songs)
        if songs:
            from quodlibet import app
            app.window.playlist.enqueue(songs)
