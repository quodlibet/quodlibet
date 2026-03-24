# Copyright 2006 Joe Wreschnig
#      2013-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet.formats import AudioFile
from quodlibet.plugins.gui import MenuItemPlugin
from quodlibet.plugins.songshelpers import is_a_file
from quodlibet.qltk.chooser import choose_folders
from quodlibet.qltk.download import DownloadProgress
from quodlibet.qltk.pluginwin import PluginWindow

from quodlibet import ngettext, _, print_d, app, util
from quodlibet import qltk
from quodlibet.errorreport import errorhook
from quodlibet.qltk.showfiles import show_songs

from quodlibet.util import print_e, print_w, copool
from quodlibet.qltk.msg import ConfirmationPrompt, ErrorMessage, Message
from quodlibet.qltk.delete import TrashMenuItem, trash_songs
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.x import SeparatorMenuItem
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.qltk import get_top_parent, get_menu_item_top_parent, Icons
from quodlibet.plugins import PluginManager, PluginHandler
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.songwrapper import list_wrapper, check_wrapper_changed


def confirm_song_removal_invoke(parent, songs):
    songs = set(songs)
    if not songs:
        return True

    count = len(songs)
    song = next(iter(songs))
    if count == 1:
        title = _('Remove track: "%(title)s" from the library?') % {
            "title": song("title") or song("~basename")
        }
    else:
        title = _("Remove %(count)d tracks from the library?") % {"count": count}

    prompt = ConfirmationPrompt(
        parent, title, "", _("Remove from Library"), ok_button_icon=Icons.LIST_REMOVE
    )
    return prompt.run() == ConfirmationPrompt.RESPONSE_INVOKE


def confirm_multi_song_invoke(parent, plugin_name, count):
    """Dialog to confirm invoking a plugin with X songs in case X is high"""
    title = ngettext(
        'Run the plugin "%(name)s" on %(count)d song?',
        'Run the plugin "%(name)s" on %(count)d songs?',
        count,
    ) % {"name": plugin_name, "count": count}
    description = ""
    ok_text = _("_Run Plugin")
    prompt = ConfirmationPrompt(parent, title, description, ok_text).run()
    return prompt == ConfirmationPrompt.RESPONSE_INVOKE


def confirm_multi_album_invoke(parent, plugin_name, count):
    """Dialog to confirm invoking a plugin with X albums in case X is high"""
    title = ngettext(
        'Run the plugin "%(name)s" on %(count)d album?',
        'Run the plugin "%(name)s" on %(count)d albums?',
        count,
    ) % {"name": plugin_name, "count": count}
    description = ""
    ok_text = _("_Run Plugin")
    prompt = ConfirmationPrompt(parent, title, description, ok_text).run()
    return prompt == ConfirmationPrompt.RESPONSE_INVOKE


class SongsMenuPluginHandler(PluginHandler):
    def __init__(self, song_confirmer=None, album_confirmer=None):
        """custom confirmers for testing"""

        self.__plugins = []

        self._confirm_multiple_songs = confirm_multi_song_invoke
        if song_confirmer is not None:
            self._confirm_multiple_songs = song_confirmer

        self._confirm_multiple_albums = confirm_multi_album_invoke
        if album_confirmer is not None:
            self._confirm_multiple_albums = album_confirmer

    def menu(self, library, songs):
        songs = list_wrapper(songs)

        attrs = ["plugin_song", "plugin_songs", "plugin_album", "plugin_albums"]

        if len(songs) == 1:
            attrs.append("plugin_single_song")

        last = (songs and songs[-1]) or None
        for song in songs:
            if song.album_key != last.album_key:
                break
            last = song
        else:
            attrs.append("plugin_single_album")

        items = []
        kinds = self.__plugins
        kinds.sort(key=lambda plugin: plugin.PLUGIN_ID)
        for Kind in kinds:
            usable = any(callable(getattr(Kind, s)) for s in attrs)
            if usable:
                try:
                    items.append(Kind(songs, library))
                except Exception:
                    print_e(f"Couldn't initialise song plugin {Kind}. Stack trace:")
                    errorhook()
        items = [i for i in items if i.initialized]

        if items:
            menu = Gtk.Menu()
            for item in items:
                try:
                    menu.append(item)
                    args = (library, songs)
                    if item.get_submenu():
                        for subitem in item.get_submenu().get_children():
                            subitem.connect("activate", self.__on_activate, item, *args)
                    else:
                        item.connect("activate", self.__on_activate, item, *args)
                except Exception:
                    errorhook()
                    item.destroy()
            menu.append(SeparatorMenuItem())
            prefs = Gtk.MenuItem(label=_("Configure Plugins…"))
            prefs.connect("activate", lambda _: PluginWindow().show())
            menu.append(prefs)

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

        albums = list(albums.values())
        for album in albums:
            album.sort()
        return albums

    def handle(self, plugin_id, library, parent, songs):
        """Start a song menu plugin directly without a menu"""

        parent = get_top_parent(parent)

        for plugin in self.__plugins:
            if plugin.PLUGIN_ID == plugin_id:
                songs = list_wrapper(songs)
                try:
                    plugin = plugin(songs, library)
                except Exception:
                    errorhook()
                else:
                    self.__handle(plugin, plugin, library, songs, parent)
                return

    def __on_activate(self, item, plugin, library, songs):
        parent = get_menu_item_top_parent(item)
        self.__handle(item, plugin, library, songs, parent)

    def __handle(self, item, plugin, library, songs, parent):
        if len(songs) == 0:
            return

        try:
            if len(songs) == 1 and callable(plugin.plugin_single_song):
                try:
                    ret = plugin.plugin_single_song(songs[0])
                except Exception:
                    errorhook()
                else:
                    if ret:
                        return
            if callable(plugin.plugin_song):
                total = len(songs)
                if total > plugin.MAX_INVOCATIONS:
                    if not self._confirm_multiple_songs(
                        parent, plugin.PLUGIN_NAME, total
                    ):
                        return

                try:
                    ret = map(plugin.plugin_song, songs)
                except Exception:
                    errorhook()
                else:
                    if any(ret):
                        return
            if callable(plugin.plugin_songs):
                try:
                    ret = plugin.plugin_songs(songs)
                except Exception:
                    errorhook()
                else:
                    if ret:
                        return

            if plugin.handles_albums:
                albums = self.__get_albums(songs)
                total = len(albums)
                if total > plugin.MAX_INVOCATIONS:
                    if not self._confirm_multiple_albums(
                        parent, plugin.PLUGIN_NAME, total
                    ):
                        return

            if callable(plugin.plugin_single_album) and len(albums) == 1:
                try:
                    ret = plugin.plugin_single_album(albums[0])
                except Exception:
                    errorhook()
                else:
                    if ret:
                        return
            if callable(plugin.plugin_album):
                try:
                    ret = map(plugin.plugin_album, albums)
                except Exception:
                    errorhook()
                else:
                    if any(ret):
                        return
            if callable(plugin.plugin_albums):
                try:
                    ret = plugin.plugin_albums(albums)
                except Exception:
                    errorhook()
                else:
                    if ret:
                        return

        finally:
            check_wrapper_changed(library, filter(None, songs))

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, SongsMenuPlugin)

    def plugin_enable(self, plugin):
        self.__plugins.append(plugin.cls)

    def plugin_disable(self, plugin):
        self.__plugins.remove(plugin.cls)


class SongsMenu(Gtk.Menu):
    plugins = SongsMenuPluginHandler()

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.plugins)

    def __init__(
        self,
        library,
        songs,
        plugins=True,
        playlists=True,
        queue=True,
        remove=True,
        delete=False,
        edit=True,
        info=True,
        ratings=True,
        show_files=True,
        download=False,
        items=None,
        accels=True,
        removal_confirmer=None,
        folder_chooser=None,
    ):
        super().__init__()
        # The library may actually be a librarian; if it is, use it,
        # otherwise find the real librarian.
        librarian = getattr(library, "librarian", library)

        if ratings:
            ratings_item = RatingsMenuItem(songs, librarian)
            ratings_item.set_sensitive(bool(songs))
            self.append(ratings_item)
            self.separate()

        # external item groups
        for subitems in reversed(items or []):
            self.separate()
            for item in subitems:
                self.append(item)
            self.separate()

        if plugins:
            submenu = self.plugins.menu(librarian, songs)
            if submenu is not None:
                b = qltk.MenuItem(_("_Plugins"), Icons.SYSTEM_RUN)
                b.set_sensitive(bool(songs))
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

        if playlists:
            self.init_playlists(can_add, library, songs)
        if queue:
            self.init_queue(accels, can_add, songs)

        if remove or delete:
            self.separate()

        if remove:
            self.init_remove(in_lib, library, removal_confirmer, remove, songs)

        if delete:
            self.init_delete(accels, delete, is_file, songs, librarian)

        if edit:
            self.init_edit(accels, songs, librarian)

        if info:
            self.init_info(accels, songs, librarian)

        if show_files and any(is_a_file(s) for s in songs):
            self.init_show_files(songs)

        if download:
            self.init_download(songs, folder_chooser)

        def selection_done_cb(menu):
            menu.destroy()

        self.connect("selection-done", selection_done_cb)

    def init_download(self, songs, folder_chooser):
        def is_downloadable(song: AudioFile):
            return bool(not song.is_file and song.get("~uri", False))

        self.separate()
        relevant = [s for s in songs if is_downloadable(s)]
        total = len(relevant)
        text = ngettext("_Download file…", "_Download %(total)d files…", total) % {
            "total": total
        }
        b = qltk.MenuItem(text, Icons.FOLDER_DOWNLOAD)
        b.set_sensitive(relevant and len(relevant) < MenuItemPlugin.MAX_INVOCATIONS)

        def _finished(p, successes, failures):
            msg = (
                f"{util.bold(str(successes))} "
                + _("successful")
                + f"\n{util.bold(str(failures))} "
                + _("failed")
            )
            print_d(msg.replace("\n", "; "))
            warning = Message(
                Gtk.MessageType.INFO,
                app.window,
                title=_("Downloads complete"),
                description=msg,
                escape_desc=False,
            )
            warning.run()

        def download_cb(menu_item):
            songs = relevant
            total = len(songs)
            msg = ngettext("Download {name!r} to", "Download {total} files to", total)
            msg = msg.format(
                name=next(iter(songs))("title")[:99] if total else "?", total=total
            )
            chooser = folder_chooser or choose_folders
            paths = chooser(None, msg, _("Download here"), allow_multiple=False)
            if not paths:
                print_d("Cancelling download")
                return
            path = paths[0]
            progress = DownloadProgress(songs)

            progress.connect("finished", _finished)
            copool.add(progress.download_songs, path)

        b.connect("activate", download_cb)
        self.append(b)

    def init_show_files(self, songs):
        def show_files_cb(menu_item):
            print_d("Trying to show files...")
            if not show_songs(songs):
                parent = get_menu_item_top_parent(menu_item)
                msg = ErrorMessage(
                    parent,
                    _("Unable to show files"),
                    _("Error showing files, or no program available to show them."),
                )
                msg.run()

        self.separate()
        total = len([s for s in songs if is_a_file(s)])
        text = ngettext(
            "_Show in File Manager", "_Show %(total)d Files in File Manager", total
        ) % {"total": total}
        b = qltk.MenuItem(text, Icons.DOCUMENT_OPEN)
        b.set_sensitive(bool(songs) and len(songs) < MenuItemPlugin.MAX_INVOCATIONS)
        b.connect("activate", show_files_cb)
        self.append(b)

    def init_info(self, accels, songs, librarian):
        b = qltk.MenuItem(_("_Information"), Icons.DIALOG_INFORMATION)
        b.set_sensitive(bool(songs))
        if accels:
            qltk.add_fake_accel(b, "<Primary>I")

        def information_cb(menu_item):
            parent = get_menu_item_top_parent(menu_item)
            window = Information(librarian, songs, parent)
            window.show()

        b.connect("activate", information_cb)
        self.append(b)

    def init_edit(self, accels, songs, librarian):
        self.separate()
        b = qltk.MenuItem(_("_Edit…"), Icons.EDIT)
        b.set_sensitive(bool(songs))
        if accels:
            qltk.add_fake_accel(b, "<alt>Return")

        def song_properties_cb(menu_item):
            parent = get_menu_item_top_parent(menu_item)
            window = SongProperties(librarian, songs, parent)
            window.show()

        b.connect("activate", song_properties_cb)
        self.append(b)

    def init_delete(self, accels, delete, is_file, songs, librarian):
        if callable(delete):
            b = qltk.MenuItem(_("_Delete"), Icons.EDIT_DELETE)
            b.connect("activate", lambda item: delete(songs))
            if accels:
                qltk.add_fake_accel(b, "<Primary>Delete")
        else:
            b = TrashMenuItem()
            if accels:
                qltk.add_fake_accel(b, "<Primary>Delete")

            def trash_cb(item):
                parent = get_menu_item_top_parent(item)
                trash_songs(parent, songs, librarian)

            b.connect("activate", trash_cb)
            b.set_sensitive(is_file and bool(songs))
        self.append(b)

    def init_remove(self, in_lib, library, removal_confirmer, remove, songs):
        self._confirm_song_removal = removal_confirmer or confirm_song_removal_invoke
        b = qltk.MenuItem(_("_Remove from Library…"), Icons.LIST_REMOVE)
        if callable(remove):
            b.connect("activate", lambda item: remove(songs))
        else:

            def remove_cb(item, songs, library):
                parent = get_menu_item_top_parent(item)
                if self._confirm_song_removal(parent, songs):
                    library.remove(songs)

            b.connect("activate", remove_cb, songs, library)
            b.set_sensitive(in_lib and bool(songs))
        self.append(b)

    def init_queue(self, accels, can_add, songs):
        b = qltk.MenuItem(_("Add to _Queue"), Icons.LIST_ADD)

        def enqueue_cb(item, songs):
            songs = [s for s in songs if s.can_add]
            if songs:
                from quodlibet import app

                app.window.playlist.enqueue(songs)

        b.connect("activate", enqueue_cb, songs)
        if accels:
            qltk.add_fake_accel(b, "<Primary>Return")
        self.append(b)
        b.set_sensitive(can_add and bool(songs))

    def init_playlists(self, can_add, library, songs):
        try:
            from quodlibet.browsers.playlists.menu import PlaylistMenu

            submenu = PlaylistMenu(songs, library.playlists)
        except AttributeError as e:
            print_w(f"Couldn't get Playlists menu: {e}")
        else:
            b = qltk.MenuItem(_("Play_lists"), Icons.FOLDER_DRAG_ACCEPT)
            b.set_sensitive(can_add and bool(songs))
            b.set_submenu(submenu)
            self.append(b)

    def separate(self):
        if not self.get_children():
            return
        if not isinstance(self.get_children()[-1], Gtk.SeparatorMenuItem):
            self.append(SeparatorMenuItem())

    def preseparate(self):
        if not self.get_children():
            return
        if not isinstance(self.get_children()[0], Gtk.SeparatorMenuItem):
            self.prepend(SeparatorMenuItem())
