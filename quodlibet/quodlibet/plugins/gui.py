# -*- coding: utf-8 -*-
# Copyright 2014, 2016 Nick Boultbee
#                 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config
from quodlibet.qltk import get_menu_item_top_parent
from quodlibet.qltk import Icons
from gi.repository import Gtk


class MenuItemPlugin(Gtk.ImageMenuItem):
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
        super(Gtk.ImageMenuItem, self).__init__(label=label)
        self.__set_icon()
        self.__initialized = True

    @property
    def plugin_window(self):
        return get_menu_item_top_parent(self)

    def __set_icon(self):
        """Sets the GTK icon for this plugin item"""
        icon = getattr(self, "PLUGIN_ICON", Icons.SYSTEM_RUN)

        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)
        self.set_always_show_image(True)
        self.set_image(image)

    @property
    def initialized(self):
        # If the GObject __init__ method is bypassed, it can cause segfaults.
        # This explicitly prevents a bad plugin from taking down the app.
        return self.__initialized
