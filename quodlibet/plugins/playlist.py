# Copyright 2013-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import ngettext, _
from quodlibet.qltk import get_top_parent, get_menu_item_top_parent, get_children
from quodlibet.qltk.msg import ConfirmationPrompt
from quodlibet.qltk.x import SeparatorMenuItem
from quodlibet.util import print_exc, format_int_locale
from quodlibet.util.dprint import print_d, print_e
from quodlibet.plugins import PluginHandler, PluginManager
from quodlibet.plugins.gui import MenuItemPlugin


def confirm_multi_playlist_invoke(parent, plugin_name, count):
    """Dialog to confirm invoking a plugin with X playlists
    in case X is high
    """
    params = {"name": plugin_name, "count": format_int_locale(count)}
    title = (
        ngettext(
            'Run the plugin "%(name)s" on %(count)s playlist?',
            'Run the plugin "%(name)s" on %(count)s playlists?',
            count,
        )
        % params
    )
    description = ""
    ok_text = _("_Run Plugin")
    prompt = ConfirmationPrompt(parent, title, description, ok_text).run()
    return prompt == ConfirmationPrompt.RESPONSE_INVOKE


class PlaylistPlugin(MenuItemPlugin):
    """
    Playlist plugins are much like songsmenu plugins,
    and provide one or more of the following instance methods:

        self.plugin_single_playlist(playlist)
        self.plugin_playlist(song)
        self.plugin_playlists(songs)

    All matching provided callables on a single object are called in the
    above order if they match until one returns a true value.

    The `single_` variant is only called if a single song/album is selected.

    The singular version is called once for each selected playlist, but the
    plural version is called with a list of playlists.

    Returning `True` from these signifies a change was made and the UI /
    library should update; otherwise this isn't guaranteed.

    Currently (01/2016) only the singular forms are actually supported in
    the UI, but this won't always be the case.

    To make your plugin insensitive if unsupported playlists are selected,
    a method that takes a list of songs and returns True or False to set
    the sensitivity of the menu entry:
        self.plugin_handles(playlists)

    All of this is managed by the constructor, so
    make sure it gets called if you override it (you shouldn't have to).

    Note: If inheriting both `PlaylistPlugin` and `SongsMenuPlugin`,
          it (currently) needs to be done in that order.
    """

    plugin_single_playlist = None
    plugin_playlist = None
    plugin_playlists = None

    def __init__(self, playlists=None, library=None):
        super().__init__()
        self._library = library
        self._playlists = playlists or []
        self.set_sensitive(bool(self.plugin_handles(playlists)))

    def plugin_handles(self, playlists):
        return True


class PlaylistPluginHandler(PluginHandler):
    """Handles PlaylistPlugins"""

    def init_plugins(self):
        PluginManager.instance.register_handler(self)

    def __init__(self, confirmer=None):
        """Takes an optional `confirmer`, mainly for testing"""

        self.__plugins = []
        self._confirm_multiple = confirmer or confirm_multi_playlist_invoke

    def populate_menu(self, menu, library, browser, playlists):
        """Appends items onto `menu` for each enabled playlist plugin,
        separated as necessary."""

        attrs = ["plugin_playlist", "plugin_playlists"]

        if len(playlists) == 1:
            attrs.append("plugin_single_playlist")

        items = []
        kinds = self.__plugins
        kinds.sort(key=lambda plugin: plugin.PLUGIN_ID)
        print_d("Found %d Playlist plugin(s): %s" % (len(kinds), kinds))
        for kind in kinds:
            usable = any(callable(getattr(kind, s)) for s in attrs)
            if usable:
                try:
                    items.append(kind(playlists=playlists, library=library))
                except Exception:
                    print_e(f"Couldn't initialise playlist plugin {kind}: ")
                    print_exc()
        items = [i for i in items if i.initialized]

        if items:
            menu.append(SeparatorMenuItem())
            for item in items:
                try:
                    menu.append(item)
                    args = (library, browser, playlists)
                    if item.get_submenu():
                        for subitem in get_children(item.get_submenu()):
                            subitem.connect("activate", self.__on_activate, item, *args)
                    else:
                        item.connect("activate", self.__on_activate, item, *args)
                except Exception:
                    print_exc()
                    # GTK4: destroy() removed - item cleaned up automatically

    def handle(self, plugin_id, library, browser, playlists):
        """Start a plugin directly without a menu"""

        for plugin in self.__plugins:
            if plugin.PLUGIN_ID == plugin_id:
                try:
                    plugin = plugin(playlists, library)
                except Exception:
                    print_exc()
                else:
                    parent = get_top_parent(browser)
                    self.__handle(plugin, library, browser, playlists, parent)
                return

    def __on_activate(self, item, plugin, library, browser, playlists):
        parent = get_menu_item_top_parent(item)
        self.__handle(plugin, library, browser, playlists, parent)

    def __handle(self, plugin, library, browser, playlists, parent):
        if len(playlists) == 0:
            return

        if len(playlists) == 1 and callable(plugin.plugin_single_playlist):
            pl = playlists[0]
            try:
                ret = plugin.plugin_single_playlist(pl)
            except Exception:
                print_exc()
            else:
                if ret:
                    print_d(f"Updating {pl}")
                    browser.changed(pl)
                    browser.activate()
                    return
        if callable(plugin.plugin_playlist):
            total = len(playlists)
            if total > plugin.MAX_INVOCATIONS:
                if not self._confirm_multiple(parent, plugin.PLUGIN_NAME, total):
                    return

            try:
                ret = map(plugin.plugin_playlist, playlists)
                if ret:
                    for update, pl in zip(ret, playlists, strict=False):
                        if update:
                            print_d(f"Updating {pl}")
                            browser.changed(pl)
                    browser.activate()
            except Exception:
                print_exc()
            else:
                if any(ret):
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
PLAYLIST_HANDLER = PlaylistPluginHandler()
