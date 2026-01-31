# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gst, Gtk, GObject

from quodlibet import _
from quodlibet.plugins import MissingGstreamerElementPluginError
from quodlibet.plugins.gstelement import GStreamerPlugin
from quodlibet import qltk
from quodlibet import config
from quodlibet.qltk import Icons
from quodlibet.qltk.util import GSignals

_PLUGIN_ID = "karaoke"

_SETTINGS = {
    "band": [_("Filter _band:"), _("The Frequency band of the filter"), 220.0],
    "width": [_("Filter _width:"), _("The Frequency width of the filter"), 100.0],
    "level": [_("_Level:"), _("Level of the effect"), 1.0],
}


def get_cfg(option):
    cfg_option = f"{_PLUGIN_ID}_{option}"
    default = _SETTINGS[option][2]
    return config.getfloat("plugins", cfg_option, default)


def set_cfg(option, value):
    cfg_option = f"{_PLUGIN_ID}_{option}"
    if get_cfg(option) != value:
        config.set("plugins", cfg_option, value)


class Preferences(Gtk.Box):
    __gsignals__: GSignals = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        table = Gtk.Table(n_rows=3, n_columns=2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        labels = {}
        for idx, key in enumerate(["level", "band", "width"]):
            label = Gtk.Label(label=_SETTINGS[key][0])
            labels[key] = label
            label.set_xalign(0.0)
            label.set_yalign(0.5)
            # GTK4: set_padding() removed, use margins
            label.set_margin_start(0)
            label.set_margin_end(0)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_tooltip_text(_SETTINGS[key][1])
            label.set_use_underline(True)
            table.attach(
                label,
                0,
                1,
                idx,
                idx + 1,
                xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
            )

        def scale_changed(scale, option):
            value = scale.get_value()
            set_cfg(option, value)
            self.emit("changed")

        max_values = [1.0, 441, 100]
        steps = [0.01, 10, 10]
        pages = [0.1, 50, 25]

        scales = {}
        for idx, key in enumerate(["level", "band", "width"]):
            max_value = max_values[idx]
            step = steps[idx]
            page = pages[idx]
            scale = Gtk.HScale(
                adjustment=Gtk.Adjustment.new(0, 0, max_value, step, page, 0)
            )
            scales[key] = scale
            if step < 0.1:
                scale.set_digits(2)
            scale.add_mark(_SETTINGS[key][2], Gtk.PositionType.BOTTOM, None)
            labels[key].set_mnemonic_widget(scale)
            scale.set_value_pos(Gtk.PositionType.RIGHT)
            table.attach(scale, 1, 2, idx, idx + 1)
            scale.connect("value-changed", scale_changed, key)
            scale.set_value(get_cfg(key))

        def format_perc(scale, value):
            return _("%d %%") % (value * 100)

        scales["level"].connect("format-value", format_perc)

        def format_hertz(scale, value):
            return _("%d Hz") % value

        scales["band"].connect("format-value", format_hertz)
        scales["width"].connect("format-value", format_hertz)

        self.append(qltk.Frame(_("Preferences"), child=table), True, True, 0)


class Karaoke(GStreamerPlugin):
    PLUGIN_ID = _PLUGIN_ID
    PLUGIN_NAME = _("Karaoke")
    PLUGIN_DESC = _("Removes main vocals from audio.")
    PLUGIN_ICON = Icons.AUDIO_INPUT_MICROPHONE

    @classmethod
    def setup_element(cls):
        return Gst.ElementFactory.make("audiokaraoke", cls.PLUGIN_ID)

    @classmethod
    def update_element(cls, element):
        element.set_property("level", get_cfg("level"))
        element.set_property("filter-band", get_cfg("band"))
        element.set_property("filter-width", get_cfg("width"))

    @classmethod
    def PluginPreferences(cls, window):
        prefs = Preferences()
        prefs.connect("changed", lambda *x: cls.queue_update())
        return prefs


if not Karaoke.setup_element():
    raise MissingGstreamerElementPluginError("audiokaraoke", "good")
