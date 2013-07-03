# -*- coding: utf-8 -*-
# Copyright 2005 Michael Urman, Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import GObject

from quodlibet import util

from quodlibet.util.songwrapper import SongWrapper, ListWrapper
from quodlibet.util.songwrapper import check_wrapper_changed


class EventPlugin(object):
    """Plugins that run in the background and receive events.

    Event plugins, unlike other plugins, are instantiated on startup and
    the same instance is used even when the plugin is enabled or disabled.

    Callables:
        obj.plugin_on_song_started(song)
        obj.plugin_on_song_ended(song, stopped)
        obj.plugin_on_added([song1, song2, ...])
        obj.plugin_on_changed([song1, song2, ...])
        obj.plugin_on_removed([song1, song2, ...])
        obj.plugin_on_paused()
        obj.plugin_on_unpaused()
        obj.plugin_on_seek(song, msec)
    """

    PLUGIN_INSTANCE = True

    def enabled(self):
        """Called when the plugin is enabled."""
        pass

    def disabled(self):
        """Called when the plugin is disabled."""
        pass


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
    sigs = [(s, prefix + s.replace('-', '_')) for s in sigs]
    return sigs


class EventPluginHandler(object):

    def __init__(self, librarian=None, player=None):
        if librarian:
            sigs = _map_signals(librarian, blacklist=("notify",))
            for event, handle in sigs:
                def handler(librarian, *args):
                    self.__invoke(librarian, args[-1], *args[:-1])
                librarian.connect(event, handler, event)

        if librarian and player:
            sigs = _map_signals(player, blacklist=("notify", "error"))
            for event, handle in sigs:
                def cb_handler(librarian, *args):
                    self.__invoke(player, args[-1], *args[:-1])
                player.connect_object(event, cb_handler, librarian, event)

        self.__plugins = {}

    def __invoke(self, librarian, event, *args):
        args = list(args)
        if args and args[0]:
            if isinstance(args[0], dict):
                args[0] = SongWrapper(args[0])
            elif isinstance(args[0], list):
                args[0] = ListWrapper(args[0])
        for plugin in self.__plugins.itervalues():
            method_name = 'plugin_on_' + event.replace('-', '_')
            handler = getattr(plugin, method_name, None)
            if handler is not None:
                try:
                    handler(*args)
                except Exception:
                    util.print_exc()

        if event not in ["removed", "changed"] and args:
            from quodlibet import app
            songs = args[0]
            if not isinstance(songs, list):
                songs = [songs]
            songs = filter(None, songs)
            check_wrapper_changed(librarian, app.window, songs)

    def plugin_handle(self, plugin):
        return issubclass(plugin, EventPlugin)

    def plugin_enable(self, plugin, obj):
        self.__plugins[plugin] = obj

    def plugin_disable(self, plugin):
        self.__plugins.pop(plugin)
