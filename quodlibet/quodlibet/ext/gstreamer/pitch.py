# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GObject, Gst

from quodlibet import _
from quodlibet.plugins import PluginImportException
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet import qltk
from quodlibet import config


_PLUGIN_ID = "pitch"

_SETTINGS = {
    "rate": [_("R_ate:"), 1.0],
    "tempo": [_("_Tempo:"), 1.0],
    "pitch": [_("_Pitch:"), 1.0],
}


def get_cfg(option):
    cfg_option = "%s_%s" % (_PLUGIN_ID, option)
    default = _SETTINGS[option][1]

    if option == "rate":
        return config.getfloat("plugins", cfg_option, default)
    elif option == "tempo":
        return config.getfloat("plugins", cfg_option, default)
    elif option == "pitch":
        return config.getfloat("plugins", cfg_option, default)


def set_cfg(option, value):
    cfg_option = "%s_%s" % (_PLUGIN_ID, option)
    if get_cfg(option) != value:
        config.set("plugins", cfg_option, value)


class Preferences(Gtk.VBox):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, tuple()),
    }

    def __init__(self):
        super(Preferences, self).__init__(spacing=12)

        table = Gtk.Table(n_rows=3, n_columns=2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        labels = {}
        for idx, key in enumerate(["tempo", "rate", "pitch"]):
            label = Gtk.Label(label=_SETTINGS[key][0])
            labels[key] = label
            label.set_alignment(0.0, 0.5)
            label.set_padding(0, 6)
            label.set_use_underline(True)
            table.attach(label, 0, 1, idx, idx + 1,
                         xoptions=Gtk.AttachOptions.FILL |
                         Gtk.AttachOptions.SHRINK)

        def scale_changed(scale, option):
            value = scale.get_value()
            set_cfg(option, value)
            self.emit("changed")

        for idx, key in enumerate(["tempo", "rate", "pitch"]):
            scale = Gtk.HScale(
                adjustment=Gtk.Adjustment.new(0, 0.1, 3, 0.1, 1, 0))
            scale.set_digits(2)
            scale.add_mark(1.0, Gtk.PositionType.BOTTOM, None)
            labels[key].set_mnemonic_widget(scale)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            table.attach(scale, 1, 2, idx, idx + 1)
            scale.connect('value-changed', scale_changed, key)
            scale.set_value(get_cfg(key))

        self.pack_start(qltk.Frame(_("Preferences"), child=table),
                        True, True, 0)


class Pitch(GStreamerPlugin):
    PLUGIN_ID = _PLUGIN_ID
    PLUGIN_NAME = _("Audio Pitch / Speed")
    PLUGIN_DESC = _("Controls the pitch of an audio stream.")

    @classmethod
    def setup_element(cls):
        return Gst.ElementFactory.make('pitch', cls.PLUGIN_ID)

    @classmethod
    def update_element(cls, element):
        for key in ["tempo", "rate", "pitch"]:
            element.set_property(key, get_cfg(key))

    @classmethod
    def PluginPreferences(cls, window):
        prefs = Preferences()
        prefs.connect("changed", lambda *x: cls.queue_update())
        return prefs


if not Pitch.setup_element():
    raise PluginImportException(
        "GStreamer element 'pitch' missing (gst-plugins-bad)")
