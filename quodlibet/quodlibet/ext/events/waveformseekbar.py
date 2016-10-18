# -*- coding: utf-8 -*-
# Copyright 2016 0x1777
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Gdk, Gst
from math import ceil, floor

from quodlibet import _, app
from quodlibet import print_w
from quodlibet.plugins import PluginConfig, BoolConfProp, IntConfProp, \
    ConfProp
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Align
from quodlibet.qltk import Icons
from quodlibet.qltk.seekbutton import TimeLabel
from quodlibet.qltk.tracker import TimeTracker
from quodlibet.util import connect_destroy, print_d


class WaveformSeekBar(Gtk.Box):
    """A widget containing labels and the seekbar."""

    def __init__(self, player, library):
        super(WaveformSeekBar, self).__init__()

        self._player = player
        self._rms_vals = []

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
        connect_destroy(player, 'song-ended', self._on_song_ended)
        connect_destroy(player, 'notify::seekable', self._on_seekable_changed)
        connect_destroy(library, 'changed', self._on_song_changed, player)

        self.connect('destroy', self._on_destroy)
        self._update(player)
        self._tracker.tick()

        if player.info:
            self._create_waveform(player.info, CONFIG.data_size)

    def _create_waveform(self, song, points):
        # Close any existing pipelines to avoid warnings
        if hasattr(self, "_pipeline") and self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)

        command_template = """
        filesrc location="{}"
        ! decodebin ! audioconvert
        ! level name=audiolevel interval={} post-messages=true
        ! fakesink sync=false"""
        interval = int(song("~#length") * 1E9 / points)
        print_d("Computing data for each %.3f seconds" % (interval / 1E9))

        filename = song("~filename").replace('"', '\\"')
        command = command_template.format(filename, interval)
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
            if structure.get_name() == "level":
                rms_db = structure.get_value("rms")
                # Calculate average of all channels (usually 2)
                rms_db_avg = sum(rms_db) / len(rms_db)
                # Normalize dB value to value between 0 and 1
                rms = pow(10, (rms_db_avg / 20))
                self._rms_vals.append(rms)
            else:
                print_w("Got unexpected message of type {}"
                        .format(message.type))
        elif message.type == Gst.MessageType.EOS:
            self._pipeline.set_state(Gst.State.NULL)

            if self._player.info:
                self._waveform_scale.reset(self._rms_vals, self._player)
                self._waveform_scale.set_placeholder(False)

    def _on_destroy(self, *args):
        self._tracker.destroy()

    def _on_tick(self, tracker, player):
        self._update(player)

    def _on_seekable_changed(self, player, *args):
        self._update(player)

    def _on_player_seek(self, player, song, ms):
        self._update(player)

    def _on_song_changed(self, library, songs, player):
        if player.info:
            self._create_waveform(player.info, CONFIG.data_size)

        self._waveform_scale.set_placeholder(True)
        self._update(player)

    def _on_song_started(self, player, song):
        self._update(player)

    def _on_song_ended(self, player, song, ended):
        self._update(player)

    def _update(self, player):
        if player.info:
            # Position in ms, length in seconds
            position = player.get_position() / 1000.0
            length = player.info("~#length")
            remaining = length - position

            if length != 0:
                self._waveform_scale.set_position(position / length)
            else:
                print_d("Length reported as zero for %s" % player.info)
                self._waveform_scale.set_position(0)

            self._elapsed_label.set_time(position)
            self._remaining_label.set_time(remaining)
            self._remaining_label.set_disabled(not player.seekable)
            self._elapsed_label.set_disabled(not player.seekable)

            self.set_sensitive(player.seekable)
        else:
            self._waveform_scale.set_placeholder(True)
            self._remaining_label.set_disabled(True)
            self._elapsed_label.set_disabled(True)

            self.set_sensitive(player.seekable)

        self._waveform_scale.queue_draw()


class WaveformScale(Gtk.EventBox):
    """The waveform widget."""

    _rms_vals = []
    _player = None
    _placeholder = True

    def __init__(self, *args, **kwds):
        super(WaveformScale, self).__init__(*args, **kwds)
        self.set_size_request(40, 40)
        self.position = 0

    @property
    def width(self):
        return self.get_allocation().width

    def set_placeholder(self, placeholder):
        self._placeholder = placeholder

    def reset(self, rms_vals, player):
        self._rms_vals = rms_vals
        self._player = player
        self.queue_draw()

    def draw_waveform(self, cr, width, height, elapsed_color, remaining_color):
        line_width = CONFIG.line_width
        value_count = len(self._rms_vals)
        max_value = max(self._rms_vals)
        ratio_width = value_count / float(width)
        ratio_height = max_value / float(height) * 2
        half_height = height // 2
        cr.set_line_width(line_width)

        if line_width < 2:
            # Default AA looks bad (and dimmer) for all 1px shapes.
            cr.set_antialias(1)

        position_width = self.position * width
        hw = line_width / 2.0
        # Avoiding object lookups is slightly faster
        data = self._rms_vals
        for x in range(0, width, line_width):
            fg_color = (elapsed_color if x < position_width
                        else remaining_color)
            cr.set_source_rgba(*list(fg_color))

            # Basic anti-aliasing / oversampling
            u1 = max(0, int(floor((x - hw) * ratio_width)))
            u2 = min(int(ceil((x + hw) * ratio_width)), len(data))
            val = sum(data[u1:u2]) / (u2 - u1)

            # Draw single line, ensuring 1px minimum
            cr.move_to(x, half_height - val / ratio_height)
            cr.line_to(x, ceil(half_height + val / ratio_height))
            cr.stroke()

    def draw_placeholder(self, cr, width, height, color):
        cr.set_line_width(2)
        cr.set_source_rgba(*list(color))
        cr.move_to(0, height // 2)
        cr.line_to(width, height // 2)
        cr.stroke()

    def do_draw(self, cr):
        context = self.get_style_context()

        # Get colors
        context.save()
        context.set_state(Gtk.StateFlags.NORMAL)
        bg_color = context.get_background_color(context.get_state())
        fg_color = context.get_color(context.get_state())
        context.set_state(Gtk.StateFlags.LINK)
        elapsed_color = context.get_color(context.get_state())
        context.restore()

        # Check if the user set a different color in the config
        elapsed_color_config = CONFIG.elapsed_color
        if elapsed_color_config and Gdk.RGBA().parse(elapsed_color_config):
            elapsed_color = Gdk.RGBA()
            elapsed_color.parse(elapsed_color_config)

        # Paint the background
        cr.set_source_rgba(*list(bg_color))
        cr.paint()

        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height

        if not self._placeholder and len(self._rms_vals) > 0:
            self.draw_waveform(cr, width, height, elapsed_color, fg_color)
        else:
            self.draw_placeholder(cr, width, height, fg_color)

    def do_button_press_event(self, event):
        # Left mouse button
        if event.button == 1 and self._player:
            ratio = event.x / self.get_allocation().width
            length = self._player.info("~#length")
            self._player.seek(ratio * length * 1000)

    def set_position(self, position):
        self.position = position


class Config(object):
    _config = PluginConfig(__name__)

    high_res = BoolConfProp(_config, "high_res", True)
    elapsed_color = ConfProp(_config, "elapsed_color", "")
    max_data_points = IntConfProp(_config, "max_data_points", 3000)

    @property
    def line_width(self):
        return 1 if self.high_res else 2

    @property
    def data_size(self):
        return self.max_data_points / self.line_width

CONFIG = Config()


class WaveformSeekBarPlugin(EventPlugin):
    """The plugin class."""

    PLUGIN_ID = "WaveformSeekBar"
    PLUGIN_NAME = _("Waveform Seek Bar")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_CONFIG_SECTION = __name__
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

            if not Gdk.RGBA().parse(text):
                # Invalid color, make text red
                entry.override_color(Gtk.StateFlags.NORMAL, red)
            else:
                # Reset text color
                entry.override_color(Gtk.StateFlags.NORMAL, None)

            CONFIG.elapsed_color = text

        vbox = Gtk.VBox(spacing=6)

        def create_color():
            hbox = Gtk.HBox(spacing=6)
            hbox.set_border_width(6)
            label = Gtk.Label(label=_("Override foreground color:"))
            hbox.pack_start(label, False, True, 0)
            entry = Gtk.Entry()
            if CONFIG.elapsed_color:
                entry.set_text(CONFIG.elapsed_color)
            entry.connect('changed', changed)
            hbox.pack_start(entry, True, True, 0)
            return hbox

        def create_resolution():
            hbox = Gtk.HBox(spacing=6)
            ccb = CONFIG._config.ConfigCheckButton(_("High Res"), "high_res",
                                                   populate=True)
            hbox.pack_start(ccb, True, True, 0)
            return hbox

        vbox.pack_start(create_color(), True, True, 0)
        vbox.pack_start(create_resolution(), True, True, 0)

        return vbox
