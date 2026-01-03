# Copyright 2014, 2016 Nick Boultbee
#                 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config, print_d, app
from quodlibet.plugins import PluginHandler
from quodlibet.qltk import get_menu_item_top_parent
from quodlibet.qltk import Icons
from gi.repository import Gtk


class UserInterfacePlugin:
    """Plugins that provide a (Gtk+ Widget)
    to display as a side bar (currently) in the main Quod Libet Window.

    These can be combined well with an EventPlugin to listen for
    current song or selection changes.

    TODO: generalise this better. See #152, #2273, #1991.
    """

    PLUGIN_INSTANCE = True

    def create_sidebar(self):
        """If defined, returns a Gtk.Box to populate the sidebar"""


class UserInterfacePluginHandler(PluginHandler):
    def __init__(self):
        self.__plugins = {}
        self.__sidebars = {}

    def plugin_handle(self, plugin):
        return issubclass(plugin.cls, UserInterfacePlugin)

    def plugin_enable(self, plugin):
        self.__plugins[plugin.cls] = pl_obj = plugin.get_instance()
        sidebar = pl_obj.create_sidebar()
        app.window.hide_side_book()
        if sidebar:
            print_d(f"Enabling sidebar for {plugin.cls}")
            self.__sidebars[plugin] = app.window.add_sidebar(sidebar, name=plugin.name)
            sidebar.show_all()

    def plugin_disable(self, plugin):
        widget = self.__sidebars.get(plugin)
        if widget:
            print_d(f"Removing sidebar {widget}")
            app.window.remove_sidebar(widget)
        self.__plugins.pop(plugin.cls)


class MenuItemPlugin(Gtk.Button):
    """
    A base plugin that appears in a menu, typically.

    During plugin callbacks, `self.plugin_window` will be
    available. This is the `Gtk.Window` that the plugin was invoked from.
    It provides access to two important widgets, `self.plugin_window.browser`
    and `self.plugin_window.songlist`.
    """

    MAX_INVOCATIONS = config.getint("plugins", "default_max_invocations", 30)
    """An upper limit on how many instances of the plugin should be launched
       at once without warning. Heavyweight plugins should override this value
       to prevent users killing their performance by opening on many songs."""

    REQUIRES_ACTION = False
    """This plugin will run a user interface first (e.g. dialog) requiring
       action from the user. The menu entry may be altered accordingly"""

    def __init__(self):
        label = self.PLUGIN_NAME + ("…" if self.REQUIRES_ACTION else "")
        # GTK4: Use Button with label, not Widget
        super().__init__(label=label, use_underline=True)
        self.add_css_class("flat")  # Menu-like appearance
        self.__set_icon()
        self.__initialized = True

    def set_submenu(self, menu):
        """Store submenu reference for GTK4 compatibility"""
        self._submenu = menu

    @property
    def plugin_window(self):
        return get_menu_item_top_parent(self)

    def __set_icon(self):
        """Sets the GTK icon for this plugin item"""
        icon = getattr(self, "PLUGIN_ICON", Icons.SYSTEM_RUN)

        # GTK4: Buttons use set_child() with a Box containing icon+label
        image = Gtk.Image.new_from_icon_name(icon)
        label_text = self.get_label()
        if label_text:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box.append(image)
            label = Gtk.Label(label=label_text, use_underline=True)
            box.append(label)
            self.set_child(box)
        else:
            self.set_child(image)

    @property
    def initialized(self):
        # If the GObject __init__ method is bypassed, it can cause segfaults.
        # This explicitly prevents a bad plugin from taking down the app.
        return self.__initialized
