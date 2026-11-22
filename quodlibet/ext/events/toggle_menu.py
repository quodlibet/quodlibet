# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, Gtk

from quodlibet import _
from quodlibet import app
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons, get_children


class ToggleMenuBarPlugin(EventPlugin):
    PLUGIN_ID = "ToggleMenuBar"
    PLUGIN_NAME = _("Toggle Menu Bar")
    PLUGIN_DESC = _("Toggle the menu bar by pressing the Alt key.")
    PLUGIN_ICON = Icons.EDIT

    def enabled(self):
        window = app.window

        # Maybe this should be made directly accessible
        self._menubar = get_children(get_children(window)[0])[0]

        # Initially set hidden
        self._menubar.set_visible(False)

        # Menu bar visibility toggle
        def toggle_menubar(controller, keyval, keycode, state):
            if keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R):
                self._menubar.set_visible(not self._menubar.get_visible())
                # Select the menu bar if visible
                if self._menubar.get_visible():
                    self._menubar.child_focus(Gtk.DirectionType.TAB_FORWARD)

        self._key_controller = Gtk.EventControllerKey()
        self._key_controller.connect("key-released", toggle_menubar)
        window.add_controller(self._key_controller)

        # Menu bar hide after deactivation
        def hide_menubar(controller):
            self._menubar.set_visible(False)

        self._focus_controller = Gtk.EventControllerFocus()
        self._focus_controller.connect("leave", hide_menubar)
        self._menubar.add_controller(self._focus_controller)

    def disabled(self):
        app.window.remove_controller(self._key_controller)
        del self._key_controller
        self._menubar.remove_controller(self._focus_controller)
        del self._focus_controller
        self._menubar.set_visible(True)
