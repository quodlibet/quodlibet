# Copyright 2005 Michael Urman, Joe Wreschnig
#           2014, 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GObject

from quodlibet.util.dprint import print_e

from quodlibet.plugins import PluginHandler

from quodlibet.util.songwrapper import SongWrapper, list_wrapper
from quodlibet.util.songwrapper import check_wrapper_changed
from quodlibet.util import connect_obj
from quodlibet.errorreport import errorhook


class EventPlugin:
    """Plugins that run in the background and receive events.

    Event plugins, unlike other plugins, are instantiated on startup and
    the same instance is used even when the plugin is enabled or disabled.

    Methods `plugin_on_*` can be overridden to provide behaviour hooks
    """

    def plugin_on_song_started(self, song):
        pass

    def plugin_on_song_ended(self, song, stopped):
        pass

    def plugin_on_added(self, songs):
        pass

    def plugin_on_changed(self, songs):
        pass

    def plugin_on_removed(self, songs):
        pass

    def plugin_on_paused(self):
        pass

    def plugin_on_unpaused(self):
        pass

    def plugin_on_seek(self, song, msec):
        pass

    def plugin_on_error(self, song, error):
        pass

    def plugin_on_songs_selected(self, songs):
        """Called when the selection in main songlist changes"""

    PLUGIN_INSTANCE = True

    def enabled(self):
        """Called when the plugin is enabled."""

    def disabled(self):
        """Called when the plugin is disabled."""


def list_signal_names(type_):
    """List of supported signal names for a GType, instance or class"""

    type_ = getattr(type_, "__gtype__", type_)

    names = []
    if not type_.is_instantiatable() and not type_.is_interface():
        return names
    names.extend(GObject.signal_list_names(type_))
    if type_.parent:
        names.extend(list_signal_names(type_.parent))
    for iface in type_.interfaces:
        names.extend(list_signal_names(iface))
    return names


def _map_signals(obj, prefix="plugin_on_", blacklist=None):
    sigs = list_signal_names(obj)
    if blacklist is None:
        blacklist = []
    sigs = [s for s in sigs if s not in blacklist]
    return [(s, prefix + s.replace("-", "_")) for s in sigs]


class EventPluginHandler(PluginHandler):
    def __init__(self, librarian=None, player=None, songlist=None):
        if librarian:
            sigs = _map_signals(librarian, blacklist=("notify",))
            for event, _handle in sigs:

                def handler(librarian, *args):
                    self.__invoke(librarian, args[-1], *args[:-1])

                librarian.connect(event, handler, event)

        if librarian and player:
            sigs = _map_signals(player, blacklist=("notify",))
            for event, _handle in sigs:

                def cb_handler(librarian, *args):
                    self.__invoke(librarian, args[-1], *args[:-1])

                connect_obj(player, event, cb_handler, librarian, event)

        if songlist:

            def __selection_changed_cb(songlist, selection):
                songs = songlist.get_selected_songs()
                self.__invoke(self.librarian, "songs_selected", songs)

            songlist.connect("selection-changed", __selection_changed_cb)

        self.librarian = librarian
        self.__plugins = {}
        self.__sidebars = {}

    def __invoke(self, librarian, event, *args):
        args = list(args)
        if args and args[0]:
            if isinstance(args[0], dict):
                args[0] = SongWrapper(args[0])
            elif isinstance(args[0], set | list):
                args[0] = list_wrapper(args[0])
        for plugin in list(self.__plugins.values()):
            method_name = "plugin_on_" + event.replace("-", "_")
            handler = getattr(plugin, method_name, None)

            def overridden(obj, name):
                return name in type(obj).__dict__

            if overridden(plugin, method_name):
                try:
                    handler(*args)
                except Exception:
                    print_e(f"Error during {method_name} on {type(plugin)}")
                    errorhook()

        if event not in ["removed", "changed"] and args:
            songs = args[0]
            if not isinstance(songs, set | list):
                songs = [songs]
            songs = filter(None, songs)
            check_wrapper_changed(librarian, songs)

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, EventPlugin)

    def plugin_enable(self, plugin):
        self.__plugins[plugin.cls] = plugin.get_instance()

    def plugin_disable(self, plugin):
        self.__plugins.pop(plugin.cls)
