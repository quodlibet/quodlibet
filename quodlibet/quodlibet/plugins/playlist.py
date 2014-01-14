# Copyright 2013-2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk
from quodlibet.qltk.msg import confirm_action
from quodlibet.qltk.x import SeparatorMenuItem
from quodlibet.util import print_exc
from quodlibet.util.dprint import print_d, print_e
from quodlibet import qltk
from quodlibet.plugins import PluginHandler, PluginManager
from quodlibet.plugins.gui import MenuItemPlugin


class PlaylistPlugin(MenuItemPlugin):
    """
    Playlist plugins are much like songsmenu plugins,
    and provide one or more of the following instance methods:

        self.plugin_single_playlist(playlist)
        self.plugin_playlist(song)
        self.plugin_playlists(songs)

    All matching provided callables on a single object are called in the
    above order if they match until one returns a true value.

    The single_ variant is only called if a single song/album is selected.

    The singular tense is called once for each selected playlist, but the
    plural tense is called with a list of playlists

    Returning `True` from these signifies a change was made and the UI /
    library should update; otherwise this isn't guaranteed.

    Currently (01/2014) only the singular forms are actually supported in
    the UI, but this won't always be the case.

    To make your plugin insensitive if unsupported playlists are selected,
    a method that takes a list of songs and returns True or False to set
    the sensitivity of the menu entry:
        self.plugin_handles(playlists)

    All of this is managed by the constructor, so
    make sure it gets called if you override it (you shouldn't have to).

    TODO: A way to inherit from both PlaylistPlugin and SongsMenuPlugin
    """
    plugin_single_playlist = None
    plugin_playlist = None
    plugin_playlists = None

    def __init__(self, playlists, library, window):
        super(PlaylistPlugin, self).__init__(window)
        self._library = library

        self.set_sensitive(bool(self.plugin_handles(playlists)))

    def plugin_handles(self, playlists):
        return True


class PlaylistPluginHandler(PluginHandler):
    """Handles PlaylistPlugins"""

    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def __init__(self, confirmer):
        self.__plugins = []
        # The method to call for confirmations of risky multi-invocations
        self.confirm_multiple = confirmer

    def populate_menu(self, menu, library, browser, playlists):
        """Appends items onto `menu` for each enabled playlist plugin,
        separated as necessary. """

        top_parent = qltk.get_top_parent(browser)

        attrs = ['plugin_playlist', 'plugin_playlists']

        if len(playlists) == 1:
            attrs.append('plugin_single_playlist')

        items = []
        kinds = self.__plugins
        kinds.sort(key=lambda plugin: plugin.PLUGIN_ID)
        print_d("Found %d Playlist plugin(s): %s" % (len(kinds), kinds))
        for Kind in kinds:
            usable = any([callable(getattr(Kind, s)) for s in attrs])
            if usable:
                try:
                    items.append(Kind(playlists, library, top_parent))
                except:
                    print_e("Couldn't initialise playlist plugin %s: " % Kind)
                    print_exc()
        items = filter(lambda i: i.initialized, items)

        if items:
            menu.append(SeparatorMenuItem())
            for item in items:
                try:
                    menu.append(item)
                    args = (library, browser, playlists)
                    if item.get_submenu():
                        for subitem in item.get_submenu().get_children():
                            subitem.connect_object(
                                'activate', self.__handle, item, *args)
                    else:
                        item.connect('activate', self.__handle, *args)
                except:
                    print_exc()
                    item.destroy()

    def handle(self, plugin_id, library, parent, playlists):
        """Start a plugin directly without a menu"""

        for plugin in self.__plugins:
            if plugin.PLUGIN_ID == plugin_id:
                try:
                    plugin = plugin(playlists, library, parent)
                except Exception:
                    print_exc()
                else:
                    self.__handle(plugin, library, parent, playlists)
                return

    def __handle(self, plugin, library, browser, playlists):
        if len(playlists) == 0:
            return

        if (len(playlists) == 1
                and callable(plugin.plugin_single_playlist)):
            pl = playlists[0]
            try:
                ret = plugin.plugin_single_playlist(pl)
            except Exception:
                print_exc()
            else:
                if ret:
                    print_d("Updating %s" % pl)
                    browser.changed(pl)
                    browser.activate()
                    return
        if callable(plugin.plugin_playlist):
            total = len(playlists)
            if total > plugin.MAX_INVOCATIONS:
                msg = ngettext("Are you sure you want to run "
                                   "the \"%s\" plugin on %d playlist?",
                               "Are you sure you want to run "
                                   "the \"%s\" plugin on %d playlists?",
                               total) % (plugin.PLUGIN_ID, total)
                if not self.confirm_multiple(msg):
                    return
            try:
                ret = map(plugin.plugin_playlist, playlists)
                if ret:
                    for update, pl in zip(ret, playlists):
                        if update:
                            print_d("Updating %s" % pl)
                            browser.changed(pl)
                    browser.activate()
            except Exception:
                print_exc()
            else:
                if max(ret):
                    return
        if callable(plugin.plugin_playlists):
            try:
                if plugin.plugin_playlists(playlists):
                    browser.activate()
            except Exception:
                print_exc()
                for pl in playlists:
                    browser.changed(pl)

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, PlaylistPlugin)

    def plugin_enable(self, plugin):
        self.__plugins.append(plugin.cls)

    def plugin_disable(self, plugin):
        self.__plugins.remove(plugin.cls)


# Single instance
PLAYLIST_HANDLER = PlaylistPluginHandler(confirm_action)

