# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gst, Gtk, GObject

from quodlibet import _
from quodlibet.plugins import PluginImportException
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet import qltk
from quodlibet import config


_PLUGIN_ID = "compressor"

_SETTINGS = {
    "threshold": [_("_Threshold:"),
                  _("Threshold until the filter is activated"), 1.0],
    "ratio": [_("R_atio:"), _("Compression ratio"), 1.0],
}


def get_cfg(option):
    cfg_option = "%s_%s" % (_PLUGIN_ID, option)
    default = _SETTINGS[option][2]

    if option == "threshold":
        return config.getfloat("plugins", cfg_option, default)
    elif option == "ratio":
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

        table = Gtk.Table(n_rows=2, n_columns=2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        labels = {}
        for idx, key in enumerate(["threshold", "ratio"]):
            text, tooltip = _SETTINGS[key][:2]
            label = Gtk.Label(label=text)
            labels[key] = label
            label.set_tooltip_text(tooltip)
            label.set_alignment(0.0, 0.5)
            label.set_padding(0, 6)
            label.set_use_underline(True)
            table.attach(label, 0, 1, idx, idx + 1,
                         xoptions=Gtk.AttachOptions.FILL |
                         Gtk.AttachOptions.SHRINK)

        threshold_scale = Gtk.HScale(
            adjustment=Gtk.Adjustment.new(0, 0, 1, 0.01, 0.1, 0))
        threshold_scale.set_digits(2)
        labels["threshold"].set_mnemonic_widget(threshold_scale)
        threshold_scale.set_value_pos(Gtk.PositionType.RIGHT)

        def format_perc(scale, value):
            return _("%d %%") % (value * 100)
        threshold_scale.connect('format-value', format_perc)
        table.attach(threshold_scale, 1, 2, 0, 1)

        def threshold_changed(scale):
            value = scale.get_value()
            set_cfg("threshold", value)
            self.emit("changed")
        threshold_scale.connect('value-changed', threshold_changed)
        threshold_scale.set_value(get_cfg("threshold"))

        ratio_scale = Gtk.HScale(
            adjustment=Gtk.Adjustment.new(0, 0, 1, 0.01, 0.1, 0))
        ratio_scale.set_digits(2)
        labels["ratio"].set_mnemonic_widget(ratio_scale)
        ratio_scale.set_value_pos(Gtk.PositionType.RIGHT)
        table.attach(ratio_scale, 1, 2, 1, 2)

        def ratio_changed(scale):
            value = scale.get_value()
            set_cfg("ratio", value)
            self.emit("changed")
        ratio_scale.connect('value-changed', ratio_changed)
        ratio_scale.set_value(get_cfg("ratio"))

        self.pack_start(qltk.Frame(_("Preferences"), child=table),
                        True, True, 0)


class Compressor(GStreamerPlugin):
    PLUGIN_ID = _PLUGIN_ID
    PLUGIN_NAME = _("Audio Compressor")
    PLUGIN_DESC = _("Changes the amplitude of all samples above a specific "
                    "threshold with a specific ratio.")

    @classmethod
    def setup_element(cls):
        return Gst.ElementFactory.make('audiodynamic', cls.PLUGIN_ID)

    @classmethod
    def update_element(cls, element):
        element.set_property("characteristics", "soft-knee")
        element.set_property("mode", "compressor")
        element.set_property("ratio", get_cfg("ratio"))
        element.set_property("threshold", get_cfg("threshold"))

    @classmethod
    def PluginPreferences(cls, window):
        prefs = Preferences()
        prefs.connect("changed", lambda *x: cls.queue_update())
        return prefs


if not Compressor.setup_element():
    raise PluginImportException(
        "GStreamer element 'audiodynamic' missing (gst-plugins-good)")
