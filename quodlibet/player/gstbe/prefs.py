# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Steven Robertson,
#           2011-2014 Christoph Reiter
#           2020-2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import config
from quodlibet import _
from quodlibet.qltk.ccb import ConfigCheckButton, ConfigSwitch
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.x import Button
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj, is_windows


class GstPlayerPreferences(Gtk.VBox):
    def __init__(self, player, debug=False):
        super().__init__(spacing=12)

        e = UndoEntry()
        e.set_tooltip_text(
            _(
                "The GStreamer output pipeline used for "
                "playback. Leave blank for the default pipeline. "
                "If the pipeline contains a sink, "
                "it will be used instead of the default one."
            )
        )

        e.set_text(config.get("player", "gst_pipeline"))

        def changed(entry):
            config.set("player", "gst_pipeline", entry.get_text())

        e.connect("changed", changed)

        pipe_label = Gtk.Label(label=_("_Output pipeline:"))
        pipe_label.set_use_underline(True)
        pipe_label.set_mnemonic_widget(e)

        apply_button = Button(_("_Apply"), Icons.VIEW_REFRESH)

        def format_buffer(scale, value):
            # Translators: s = seconds  # noqa
            return _("%.1f s") % value

        def scale_changed(scale):
            duration_msec = int(scale.get_value() * 1000)
            player._set_buffer_duration(duration_msec)

        duration = config.getfloat("player", "gst_buffer")
        scale = Gtk.HScale.new(Gtk.Adjustment(value=duration, lower=0.2, upper=10))
        scale.set_value_pos(Gtk.PositionType.LEFT)
        scale.set_show_fill_level(True)
        scale.connect("format-value", format_buffer)
        scale.connect("value-changed", scale_changed)

        buffer_label = Gtk.Label(label=_("_Buffer duration:"))
        buffer_label.set_use_underline(True)
        buffer_label.set_mnemonic_widget(scale)

        def rebuild_pipeline(*args):
            player._rebuild_pipeline()

        apply_button.connect("clicked", rebuild_pipeline)

        gapless_button = ConfigSwitch(
            _("Disable _gapless playback"),
            "player",
            "gst_disable_gapless",
            populate=True,
            tooltip=_(
                "Disabling gapless playback can avoid track changing problems "
                "with some GStreamer versions"
            ),
        )
        jack_button = ConfigSwitch(
            _("Use JACK for playback if available"),
            "player",
            "gst_use_jack",
            populate=True,
            tooltip=_("Uses `jackaudiosink` for playbin sink if it can be detected"),
        )
        jack_connect = ConfigSwitch(
            _("Auto-connect to JACK output devices"),
            "player",
            "gst_jack_auto_connect",
            populate=True,
            tooltip=_("Tells `jackaudiosink` to auto-connect"),
        )

        def _jack_activated(widget: ConfigCheckButton, *args) -> None:
            jack_connect.set_sensitive(widget.get_active())

        jack_button.connect("notify::active", _jack_activated)
        _jack_activated(jack_button, None)

        hb = self._create_pipeline_box(pipe_label, e, apply_button)
        self.pack_start(hb, False, False, 0)

        # Buffer
        hb = self._create_buffer_box(buffer_label, scale)
        self.pack_start(hb, False, False, 0)
        self.pack_start(gapless_button, False, False, 0)
        self.pack_start(jack_button, False, False, 0)
        self.pack_start(jack_connect, False, False, 0)

        exclusive_button = ConfigSwitch(
            _("Exclusive Mode"),
            "player",
            "gst_exclusive_mode",
            populate=True,
            tooltip=_(
                "Enable exclusive audio access. "
                "Other applications won't be able to use audio while active."
            ),
        )
        if is_windows():
            # atm this is a wasapi2sink-only feature, so only makes sense on Windows
            self.pack_start(exclusive_button, False, False, 0)

        if debug:

            def print_bin(player):
                player._print_pipeline()

            b = Button("Print Pipeline", Icons.DIALOG_INFORMATION)
            connect_obj(b, "clicked", print_bin, player)
            hb = Gtk.Box(spacing=6)
            hb.pack_end(b, False, False, 0)
            self.pack_start(hb, False, False, 0)

    def _create_buffer_box(self, label: Gtk.Label, scale: Gtk.HScale):
        hb = Gtk.Box(spacing=6)
        hb.pack_start(label, False, False, 0)
        hb.pack_end(scale, True, True, 0)
        return hb

    def _create_pipeline_box(
        self, pipe_label: Gtk.Label, e: Gtk.Widget, apply_button: Gtk.Button
    ):
        hb = Gtk.Box(spacing=12)
        hb.pack_start(pipe_label, False, False, 0)
        hb.pack_start(e, True, True, 0)
        hb.pack_end(apply_button, False, False, 0)
        return hb
