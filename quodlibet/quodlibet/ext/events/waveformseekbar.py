# -*- coding: utf-8 -*-
# Copyright 2016 0x1777
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk, Gst

from quodlibet import _, app, config
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Align
from quodlibet.qltk.seekbutton import TimeLabel
from quodlibet.qltk.tracker import TimeTracker
from quodlibet.util import connect_destroy, print_d


class WaveformSeekBar(Gtk.Box):
    """ A widget containing labels and the seekbar."""

    def __init__(self, player, library):
        super(WaveformSeekBar, self).__init__()

        self._player = player

        self._elapsed_label = TimeLabel()
        self._remaining_label = TimeLabel()
        self._waveform_scale = WaveformScale()

        self.pack_start(Align(self._elapsed_label, border=6), False, True, 0)
        self.pack_start(self._waveform_scale, True, True, 0)
        self.pack_start(Align(self._remaining_label, border=6), False, True, 0)

        for child in self.get_children():
            child.show_all()

        self._tracker = TimeTracker(player)
        self._tracker.connect('tick', self._on_tick, player)

        connect_destroy(player, 'seek', self._on_player_seek)
        connect_destroy(player, 'song-started', self._on_song_started)
        connect_destroy(player, 'notify::seekable', self._on_seekable_changed)
        connect_destroy(library, 'changed', self._on_song_changed, player)

        self.connect('destroy', self._on_destroy)
        self._update(player)
        self._tracker.tick()

    def _create_waveform(self, file):
        # Close any existing pipelines to avoid warnings
        if hasattr(self, "_pipeline") and self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)

        command_template = """
        filesrc location="{}"
        ! decodebin
        ! level name=audiolevel interval=100000000 post-messages=true
        ! fakesink sync=false"""
        command = command_template.format(file)
        pipeline = Gst.parse_launch(command)

        bus = pipeline.get_bus()
        self._bus_id = bus.connect("message", self._on_bus_message)
        bus.add_signal_watch()

        pipeline.set_state(Gst.State.PLAYING)

        self._pipeline = pipeline
        self._rms_vals = []

    def _on_bus_message(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            print_d("Error received from element {name}: {error}".format(
                name=message.src.get_name(), error=error))
            print_d("Debugging information: {}".format(debug))
        elif message.type == Gst.MessageType.ELEMENT:
            structure = message.get_structure()
            if(structure.get_name() == "level"):
                rms_dB = structure.get_value("rms")
                # Calculate average of all channels (usually 2)
                rms_dB_avg = sum(rms_dB) / len(rms_dB)
                # Normalize dB value to value between 0 and 1
                rms = pow(10, (rms_dB_avg / 20))
                self._rms_vals.append(rms)
            else:
                # Shouldn't happen
                print_d("Not Level")
        elif message.type == Gst.MessageType.EOS:
            self._pipeline.set_state(Gst.State.NULL)
            self._waveform_scale.update(self._rms_vals, self._player)

    def _on_destroy(self, *args):
        self._tracker.destroy()

    def _on_song_changed(self, library, songs, player):
        self._update(player)
        if player.info:
            self._create_waveform(player.info("~filename"))

    def _on_tick(self, tracker, player):
        self._update(player)

    def _on_seekable_changed(self, player, *args):
        self._update(player)

    def _on_player_seek(self, player, song, ms):
        self._update(player)

    def _on_song_started(self, player, song):
        self._update(player)

    def _update(self, player):
        if player.info:
            # Position in ms, length in seconds
            position = player.get_position() / 1000
            length = (player.info("~#length"))
            remaining = length - position

            if length == 0:
                return

            self._waveform_scale.set_position(position / length)
            self._elapsed_label.set_time(position)
            self._remaining_label.set_time(remaining)
            self._remaining_label.set_disabled(not player.seekable)
            self._elapsed_label.set_disabled(not player.seekable)

            self.set_sensitive(player.seekable)


class WaveformScale(Gtk.EventBox):
    """ The waveform widget. """

    _rms_vals = []

    def __init__(self, *args, **kwds):
        super(WaveformScale, self).__init__(*args, **kwds)
        self.set_size_request(40, 40)
        self.position = 0

    def update(self, rms_vals, player):
        self._rms_vals = rms_vals
        self.queue_draw()
        self._player = player

    def do_draw(self, cr):
        # Paint the background
        context = self.get_style_context()
        context.save()
        context.set_state(Gtk.StateFlags.NORMAL)
        bg_color = context.get_background_color(context.get_state())
        context.restore()

        cr.set_source_rgba(*list(bg_color))
        cr.paint()
        cr.set_line_width(2)

        # Make sure rms values are available
        if len(self._rms_vals) == 0:
            return

        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height
        value_count = len(self._rms_vals)
        max_value = max(self._rms_vals)
        ratio_width = value_count / float(width)
        ratio_height = max_value / float(height)

        elapsed_color = Gdk.RGBA()
        elapsed_color.parse(get_fg_color())

        context.save()
        context.set_state(Gtk.StateFlags.SELECTED)
        remaining_color = context.get_color(context.get_state())
        context.restore()

        # Draw the waveform
        for x in range(width):
            fg_color = remaining_color

            if x < self.position * width:
                fg_color = elapsed_color

            cr.set_source_rgba(*list(fg_color))

            # The index of the closest rms value
            i = int(x * ratio_width)
            cr.move_to(x, 20)
            # Draw line up and down
            cr.line_to(x, 20 - self._rms_vals[i] / ratio_height * 0.5)
            cr.line_to(x, 20 + self._rms_vals[i] / ratio_height * 0.5)

            cr.stroke()

    def do_button_press_event(self, event):
        # Left mouse button
        if event.button == 1:
            ratio = event.x / self.get_allocation().width
            length = self._player.info("~#length")
            self._player.seek(ratio * length * 1000)

    def set_position(self, position):
        self.position = position
        self.queue_draw()


def get_fg_color():
    default = "#ff5522"
    color = config.get("plugins", __name__, default)

    return color

def set_fg_color(color):
    config.set("plugins", __name__, color)


class WaveformSeekBarPlugin(EventPlugin):
    """ The plugin class. """

    PLUGIN_ID = "WaveformSeekBar"
    PLUGIN_NAME = _("Waveform Seek Bar")
    PLUGIN_DESC = _(
        "A seekbar in the shape of the waveform of the current song.")

    def enabled(self):
        self._bar = WaveformSeekBar(app.player, app.librarian)
        self._bar.show()
        app.window.set_seekbar_widget(self._bar)

    def disabled(self):
        app.window.set_seekbar_widget(None)
        self._bar.destroy()
        del self._bar

    def PluginPreferences(self, parent):
        red = Gdk.RGBA()
        red.parse("#ff0000")

        def changed(entry):
            text = entry.get_text()

            elapsed_color = Gdk.RGBA()
            elapsed_color.parse(get_fg_color())

            if not Gdk.RGBA().parse(text):
                # Invalid color, make text red
                entry.override_color(Gtk.StateFlags.NORMAL, red)
            else:
                # Reset text color
                entry.override_color(Gtk.StateFlags.NORMAL, None)
                set_fg_color(text)

        hbox = Gtk.HBox(spacing=6)
        hbox.set_border_width(6)
        hbox.pack_start(
            Gtk.Label(label=_("Foreground Color:")), False, True, 0)
        entry = Gtk.Entry()
        entry.set_text(get_fg_color())
        entry.connect('changed', changed)
        hbox.pack_start(entry, True, True, 0)
        return hbox
