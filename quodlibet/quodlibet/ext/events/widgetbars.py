# -*- coding: utf-8 -*-
# Copyright 2017 Pete Beardmore
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import app

from quodlibet.util import print_d
from quodlibet import _
from quodlibet.plugins import PluginConfig, ConfProp
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.x import Button
from quodlibet.qltk import Icons


plugin_id = "widgetbars"


class Config(object):
    _config = PluginConfig(plugin_id)

    pane_order = ConfProp(_config, "pane_order", "")


CONFIG = Config()


class WidgetBars(EventPlugin):
    """The plugin class."""

    PLUGIN_ID = "widgetbars"
    PLUGIN_NAME = _("WidgetBars")
    PLUGIN_DESC = _("Control plugin for WidgetBars.")
    PLUGIN_ICON = Icons.PREFERENCES_PLUGIN

    def enabled(self):
        pass

    def disabled(self):
        self.__update()

    def __pane_order_changed(self, widget, *data):
        print_d("__pane_order_changed")
        CONFIG.pane_order = widget.get_text()
        return False

    def plugin_on_plugin_toggled(self, plugin, enabled):
        if plugin.id == plugin_id:
            self.__update()

    def __update(self):
        app.window.update_ui()

    def PluginPreferences(self, window):

        box = Gtk.VBox(spacing=10)

        # entries
        entries = [
            (CONFIG.pane_order,
             _("Pane order"),
             "e.g. main,playbar",
             self.__pane_order_changed),
        ]
        for text, label, tooltip, changed_cb in entries:
            entry_box = Gtk.HBox(spacing=6)
            entry_entry = UndoEntry()
            entry_entry.set_text(text)
            entry_entry.connect('focus-out-event', changed_cb)
            entry_entry.set_tooltip_markup(tooltip)
            entry_label = Gtk.Label(label)
            entry_label.set_mnemonic_widget(entry_entry)
            entry_label.set_alignment(xalign=0, yalign=0.5)
            entry_label.set_size_request(60, -1)
            entry_box.pack_start(entry_label, False, True, 5)
            entry_box.pack_start(entry_entry, True, True, 0)
            box.pack_start(entry_box, True, True, 0)

        # buttons
        buttons = [
            (_('Update'), "", lambda *x: self.__update()),
        ]
        for label, tooltip, changed_cb in buttons:
            button = Button(label)
            button.set_size_request(100, -1)
            button.connect("clicked", changed_cb)
            button_box = Gtk.HBox()
            button_box.pack_end(button, False, False, 0)
            if tooltip:
                button.set_tooltip_text(tooltip)
            box.pack_start(button_box, True, True, 0)

        return box
