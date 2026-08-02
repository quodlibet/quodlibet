# Copyright 2006 Joe Wreschnig
#      2013-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections.abc import Callable
from dataclasses import dataclass

from gi.repository import Gtk, Gio, GLib

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
from quodlibet.util import trash
from quodlibet.qltk.msg import ConfirmationPrompt, ErrorMessage, Message
from quodlibet.qltk.delete import trash_songs
from quodlibet.qltk.information import Information
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.qltk import get_top_parent, Icons
from quodlibet.plugins import PluginManager, PluginHandler
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.songwrapper import list_wrapper, check_wrapper_changed


@dataclass
class MenuItemSpec:
    """A declarative context-menu entry for :class:`SongsMenu`'s ``items=``.

    ``callback`` is invoked with the toplevel window (or ``None``) as its
    only argument when the entry is activated.
    """

    label: str
    callback: Callable[[Gtk.Window | None], None]
    enabled: bool = True
    accel: str | None = None


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


def append_flat(menu: Gio.Menu, group: Gio.Menu) -> None:
    """Append a group's items to `menu` directly, without a section.

    GTK 4.22 sizes a popover menu as if its section separators weren't there,
    so a sectioned menu is allocated too little height and scrolls. See
    GTK4_POST_MIGRATION_CLEANUP.md.
    """

    for i in range(group.get_n_items()):
        menu.append_item(Gio.MenuItem.new_from_model(group, i))


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

    def build_menu_item(self, library, songs, action_group, prefix, parent_getter):
        """Build a "Plugins" submenu :class:`Gio.MenuItem`, or ``None``.

        Registers the plugin actions on ``action_group`` under ``prefix``.
        """
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

        if not items:
            return None

        submenu = Gio.Menu()
        plugins_section = Gio.Menu()
        for idx, plugin in enumerate(items):
            widget_submenu = plugin.get_submenu()
            if widget_submenu is not None:
                sub = Gio.Menu()
                for jdx, child in enumerate(qltk.get_children(widget_submenu)):
                    if isinstance(child, Gtk.Separator):
                        continue
                    name = f"plugin-{idx}-{jdx}"
                    self._add_plugin_action(
                        action_group,
                        prefix,
                        name,
                        plugin,
                        child,
                        library,
                        songs,
                        parent_getter,
                        bool(songs),
                    )
                    sub.append(child.get_label() or "", f"{prefix}.{name}")
                plugins_section.append_submenu(plugin.PLUGIN_NAME, sub)
            else:
                name = f"plugin-{idx}"
                self._add_plugin_action(
                    action_group,
                    prefix,
                    name,
                    plugin,
                    None,
                    library,
                    songs,
                    parent_getter,
                    bool(songs),
                )
                plugins_section.append(plugin.PLUGIN_NAME, f"{prefix}.{name}")
        append_flat(submenu, plugins_section)

        config_section = Gio.Menu()
        cfg = Gio.SimpleAction.new("plugin-configure", None)
        cfg.connect("activate", lambda a, p: PluginWindow().show())
        action_group.add_action(cfg)
        config_section.append(_("Configure Plugins…"), f"{prefix}.plugin-configure")
        append_flat(submenu, config_section)

        return Gio.MenuItem.new_submenu(_("_Plugins"), submenu)

    def _add_plugin_action(
        self,
        action_group,
        prefix,
        name,
        plugin,
        widget_child,
        library,
        songs,
        parent_getter,
        enabled,
    ):
        action = Gio.SimpleAction.new(name, None)

        def activate(_action, _param):
            if widget_child is not None:
                widget_child.emit("activate")
            self.__handle(plugin, library, songs, parent_getter())

        action.connect("activate", activate)
        action.set_enabled(enabled)
        action_group.add_action(action)

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
                    self.__handle(plugin, library, songs, parent)
                return

    def __handle(self, plugin, library, songs, parent):
        if len(songs) == 0:
            return

        plugin.plugin_window = parent
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


class SongsMenu(Gtk.PopoverMenu):
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
        self.set_has_arrow(False)
        self._model = Gio.Menu()
        self._actions = Gio.SimpleActionGroup()
        self.set_menu_model(self._model)
        self.insert_action_group("songs", self._actions)
        self._accels = accels
        # Keep submenu builders alive for the lifetime of the menu.
        self._keepalive: list = []
        self._removal_confirmer = removal_confirmer or confirm_song_removal_invoke
        self._folder_chooser = folder_chooser

        # The library may actually be a librarian; if it is, use it,
        # otherwise find the real librarian.
        librarian = getattr(library, "librarian", library)

        if ratings:
            rating = RatingsMenuItem(
                songs,
                librarian,
                self._actions,
                "songs",
                parent_getter=self._top_parent,
            )
            rating.set_sensitive(bool(songs))
            self._keepalive.append(rating)
            section = Gio.Menu()
            section.append_item(rating.menu_item)
            append_flat(self._model, section)

        # external item groups
        for group_idx, subitems in enumerate(items or []):
            section = Gio.Menu()
            for item_idx, spec in enumerate(subitems):
                name = f"item-{group_idx}-{item_idx}"
                self._add_spec_action(name, spec)
                section.append_item(self._menu_item(spec.label, name, spec.accel))
            if section.get_n_items():
                append_flat(self._model, section)

        if plugins:
            plugin_item = self.plugins.build_menu_item(
                librarian, songs, self._actions, "songs", self._top_parent
            )
            if plugin_item is not None:
                section = Gio.Menu()
                section.append_item(plugin_item)
                append_flat(self._model, section)

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

        add_section = Gio.Menu()
        if playlists:
            self.init_playlists(add_section, can_add, library, songs)
        if queue:
            self.init_queue(add_section, can_add, songs)
        if add_section.get_n_items():
            append_flat(self._model, add_section)

        rm_section = Gio.Menu()
        if remove:
            self.init_remove(rm_section, in_lib, library, remove, songs)
        if delete:
            self.init_delete(rm_section, delete, is_file, songs, librarian)
        if rm_section.get_n_items():
            append_flat(self._model, rm_section)

        edit_section = Gio.Menu()
        if edit:
            self.init_edit(edit_section, songs, librarian)
        if info:
            self.init_info(edit_section, songs, librarian)
        if edit_section.get_n_items():
            append_flat(self._model, edit_section)

        if show_files and any(is_a_file(s) for s in songs):
            section = Gio.Menu()
            self.init_show_files(section, songs)
            append_flat(self._model, section)

        if download:
            section = Gio.Menu()
            self.init_download(section, songs)
            append_flat(self._model, section)

    def _top_parent(self):
        return get_top_parent(self)

    def _add_action(self, name, callback, enabled=True):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda a, p: callback())
        action.set_enabled(bool(enabled))
        self._actions.add_action(action)
        return action

    def _add_spec_action(self, name, spec: MenuItemSpec):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda a, p: spec.callback(self._top_parent()))
        action.set_enabled(bool(spec.enabled))
        self._actions.add_action(action)

    def _menu_item(self, label, name, accel=None):
        item = Gio.MenuItem.new(label, f"songs.{name}")
        if accel and self._accels:
            item.set_attribute_value("accel", GLib.Variant("s", accel))
        return item

    def init_download(self, section, songs):
        def is_downloadable(song: AudioFile):
            return bool(not song.is_file and song.get("~uri", False))

        relevant = [s for s in songs if is_downloadable(s)]
        total = len(relevant)
        text = ngettext("_Download file…", "_Download %(total)d files…", total) % {
            "total": total
        }

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

        def download_cb():
            total = len(relevant)
            msg = ngettext("Download {name!r} to", "Download {total} files to", total)
            msg = msg.format(
                name=next(iter(relevant))("title")[:99] if total else "?", total=total
            )
            chooser = self._folder_chooser or choose_folders
            paths = chooser(None, msg, _("Download here"), allow_multiple=False)
            if not paths:
                print_d("Cancelling download")
                return
            path = paths[0]
            progress = DownloadProgress(relevant)
            progress.connect("finished", _finished)
            copool.add(progress.download_songs, path)

        enabled = bool(relevant) and len(relevant) < MenuItemPlugin.MAX_INVOCATIONS
        self._add_action("download", download_cb, enabled)
        section.append(text, "songs.download")

    def init_show_files(self, section, songs):
        def show_files_cb():
            print_d("Trying to show files...")
            if not show_songs(songs):
                msg = ErrorMessage(
                    self._top_parent(),
                    _("Unable to show files"),
                    _("Error showing files, or no program available to show them."),
                )
                msg.run()

        total = len([s for s in songs if is_a_file(s)])
        text = ngettext(
            "_Show in File Manager", "_Show %(total)d Files in File Manager", total
        ) % {"total": total}
        enabled = bool(songs) and len(songs) < MenuItemPlugin.MAX_INVOCATIONS
        self._add_action("show-files", show_files_cb, enabled)
        section.append(text, "songs.show-files")

    def init_info(self, section, songs, librarian):
        def information_cb():
            window = Information(librarian, songs, self._top_parent())
            window.show()

        self._add_action("information", information_cb, bool(songs))
        section.append_item(
            self._menu_item(_("_Information"), "information", "<Primary>I")
        )

    def init_edit(self, section, songs, librarian):
        def song_properties_cb():
            window = SongProperties(librarian, songs, self._top_parent())
            window.show()

        self._add_action("edit", song_properties_cb, bool(songs))
        section.append_item(self._menu_item(_("_Edit…"), "edit", "<alt>Return"))

    def init_delete(self, section, delete, is_file, songs, librarian):
        if callable(delete):
            self._add_action("delete", lambda: delete(songs))
            section.append_item(
                self._menu_item(_("_Delete"), "delete", "<Primary>Delete")
            )
        else:

            def trash_cb():
                trash_songs(self._top_parent(), songs, librarian)

            label = _("_Move to Trash") if trash.use_trash() else _("_Delete")
            self._add_action("delete", trash_cb, is_file and bool(songs))
            section.append_item(self._menu_item(label, "delete", "<Primary>Delete"))

    def init_remove(self, section, in_lib, library, remove, songs):
        if callable(remove):
            self._add_action("remove", lambda: remove(songs))
            section.append(_("_Remove from Library…"), "songs.remove")
        else:

            def remove_cb():
                parent = self._top_parent()
                if self._removal_confirmer(parent, songs):
                    library.remove(songs)

            self._add_action("remove", remove_cb, in_lib and bool(songs))
            section.append(_("_Remove from Library…"), "songs.remove")

    def init_queue(self, section, can_add, songs):
        def enqueue_cb():
            to_add = [s for s in songs if s.can_add]
            if to_add:
                app.window.playlist.enqueue(to_add)

        self._add_action("queue", enqueue_cb, can_add and bool(songs))
        section.append_item(
            self._menu_item(_("Add to _Queue"), "queue", "<Primary>Return")
        )

    def init_playlists(self, section, can_add, library, songs):
        try:
            from quodlibet.browsers.playlists.menu import PlaylistMenu

            playlist_menu = PlaylistMenu(
                songs,
                library.playlists,
                self._actions,
                "songs",
                parent_getter=self._top_parent,
            )
        except AttributeError as e:
            print_w(f"Couldn't get Playlists menu: {e}")
        else:
            self._keepalive.append(playlist_menu)
            playlist_menu.set_sensitive(can_add and bool(songs))
            section.append_item(playlist_menu.menu_item)
