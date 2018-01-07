# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk

from quodlibet import _
from quodlibet import app
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons


class ToggleMenuBarPlugin(EventPlugin):
    PLUGIN_ID = "ToggleMenuBar"
    PLUGIN_NAME = _("Toggle Menu Bar")
    PLUGIN_DESC = _("Toggle the menu bar by pressing the Alt key.")
    PLUGIN_ICON = Icons.EDIT

    def enabled(self):
        window = app.window

        # Maybe this should be made directly accessible
        self._menubar = window.get_children()[0].get_children()[0]

        # Initially set hidden
        self._menubar.set_visible(False)

        # Menu bar visibility toggle
        def toggle_menubar(widget, event):
            if event.keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R):
                self._menubar.set_visible(not self._menubar.get_visible())
                # Select the menu bar if visible
                if self._menubar.get_visible():
                    self._menubar.select_first(False)
                    self._menubar.deselect()

        self._key_release_handler = \
            window.connect('key_release_event', toggle_menubar)

        # Menu bar hide after deactivation
        def hide_menubar(widget):
            self._menubar.set_visible(False)

        self._deactivate_handler = \
            self._menubar.connect('deactivate', hide_menubar)

    def disabled(self):
        window = app.window
        window.disconnect(self._key_release_handler)
        del self._key_release_handler
        self._menubar.disconnect(self._deactivate_handler)
        self._menubar.set_visible(True)
        del self._deactivate_handler
