# -*- coding: utf-8 -*-
# Copyright 2005 Michael Urman, Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject

from quodlibet.plugins import Manager, SongWrapper, ListWrapper

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

    def enabled(self):
        """Called when the plugin is enabled."""
        pass

    def disabled(self):
        """Called when the plugin is disabled."""
        pass

    def destroy(self):
        """Called when the plugin should release any private resources,
        usually because it's being upgraded."""
        pass

class EventPlugins(Manager):
    library_events = []
    player_events = []

    def __init__(self, librarian=None, player=None, folders=[], name=None):
        super(EventPlugins, self).__init__(folders, name)

        if librarian:
            self.library_events = [
                (s.replace('-', '_'), 'plugin_on_' + s.replace('-', '_'))
                for s in gobject.signal_list_names(librarian)]
        if player:
            self.player_events = [
                (s.replace('-', '_'), 'plugin_on_' + s.replace('-', '_'))
                for s in gobject.signal_list_names(player)]
            self.player_events.remove(('error', 'plugin_on_error'))
        self.all_events = self.library_events + self.player_events

        self.librarian = librarian

        if librarian:
            for event, handle in self.library_events:
                def handler(librarian, *args):
                    self.__invoke(librarian, args[-1], *args[:-1])
                librarian.connect(event, handler, event)
        if player:
            for event, handle in self.player_events:
                def handler(player, *args):
                    self.__invoke(player, args[-1], *args[:-1])
                player.connect_object(event, handler, librarian, event)

    def _load(self, name, module):
        try: objs = [getattr(module, attr) for attr in module.__all__]
        except AttributeError:
            objs = [getattr(module, attr) for attr in vars(module)
                    if not attr.startswith("_")]
        def is_plugin(obj):
            if not isinstance(obj, type): return False
            elif not issubclass(obj, EventPlugin): return False
            elif obj is EventPlugin: return False
            else: return True

        kinds = filter(is_plugin, objs)

        for Kind in kinds:
            try: Kind.PLUGIN_ID
            except AttributeError:
                try: Kind.PLUGIN_ID = Kind.PLUGIN_NAME
                except AttributeError:
                    Kind.PLUGIN_ID = Kind.__name__

            try: Kind.PLUGIN_NAME
            except AttributeError:
                Kind.PLUGIN_NAME = Kind.PLUGIN_ID

            try: obj = Kind()
            except:
                util.print_exc()
            else:
                if obj.PLUGIN_ID in self._plugins:
                    self._plugins[obj.PLUGIN_ID].destroy()
                self._plugins[obj.PLUGIN_ID] = obj

    def list(self):
        return self._plugins.values()

    def enable(self, plugin, enabled):
        if self.enabled(plugin) != enabled:
            super(EventPlugins, self).enable(plugin, enabled)
            try:
                if enabled: plugin.enabled()
                else: plugin.disabled()
            except:
                util.print_exc()

    def __invoke(self, librarian, event, *args):
        try:
            args = list(args)
            if args and args[0]:
                if isinstance(args[0], dict):
                    args[0] = SongWrapper(args[0])
                elif isinstance(args[0], list):
                    args[0] = ListWrapper(args[0])
            for plugin in self._plugins.itervalues():
                if not self.enabled(plugin):
                    continue
                handler = getattr(plugin, 'plugin_on_' + event, None)
                if handler is not None:
                    try: handler(*args)
                    except Exception:
                        util.print_exc()
        finally:
            if event not in ["removed", "changed"] and args:
                from quodlibet.widgets import main
                songs = args[0]
                if not isinstance(songs, list):
                    songs = [songs]
                songs = filter(None, songs)
                self._check_change(librarian, main, songs)
