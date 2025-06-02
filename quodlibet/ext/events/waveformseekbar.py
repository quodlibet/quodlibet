# Copyright 2016 0x1777
#        2016-24 Nick Boultbee
#           2017 Didier Villevalois
#           2017 Muges
#           2017 Eyenseo
#           2018 Joschua Gandert
#           2018 Blimmo
#           2018 Olli Helin
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from functools import lru_cache
from math import ceil, floor

from gi.repository import Gtk, Gdk, Gst
import cairo

from quodlibet import _, app
from quodlibet import print_w
from quodlibet import util
from quodlibet.plugins import PluginConfig, IntConfProp, ConfProp, BoolConfProp
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Align, add_css
from quodlibet.qltk import Icons
from quodlibet.qltk.seekbutton import TimeLabel
from quodlibet.qltk.tracker import TimeTracker
from quodlibet.qltk import get_fg_highlight_color
from quodlibet.qltk.x import SymbolicIconImage
from quodlibet.util import connect_destroy, print_d
from quodlibet.util.path import uri2gsturi


@lru_cache
def parse_color(value: str | Gdk.RGBA) -> Gdk.RGBA:
    col = Gdk.RGBA()
    if isinstance(value, Gdk.RGBA):
        return value
    if not col.parse(value):
        print_w(f"Invalid Gdk color: {value}")
    print_d(f"Using {col} for {value}")
    return col


class Config:
    _config = PluginConfig(__name__)

    elapsed_color = ConfProp(_config, "elapsed_color", "")
    hover_color = ConfProp(_config, "hover_color", "")
    remaining_color = ConfProp(_config, "remaining_color", "")
    show_current_pos = BoolConfProp(_config, "show_current_pos", False)
    seek_amount = IntConfProp(_config, "seek_amount", 5000)
    max_data_points = IntConfProp(_config, "max_data_points", 3000)
    show_time_labels = BoolConfProp(_config, "show_time_labels", True)
    height_px = IntConfProp(_config, "height_px", 40)


CONFIG = Config()


class WaveformSeekBar(Gtk.Box):
    """A widget containing labels and the seekbar."""

    def __init__(self, player, library):
        super().__init__()

        self._player = player
        self._rms_vals = []
        self._hovering = False

        self._elapsed_label = TimeLabel()
        self._remaining_label = TimeLabel()
        self._waveform_scale = WaveformScale(player)

        self.prepend(Align(self._elapsed_label, border=6), False, True, 0)
        self.prepend(self._waveform_scale, True, True, 0)
        self.prepend(Align(self._remaining_label, border=6), False, True, 0)

        for child in self.get_children():
            child.show_all()
        self.set_time_label_visibility(CONFIG.show_time_labels)

        self._waveform_scale.connect("size-allocate", self._update_redraw_interval)
        self._waveform_scale.connect("motion-notify-event", self._on_mouse_hover)
        self._waveform_scale.connect("leave-notify-event", self._on_mouse_leave)

        self._label_tracker = TimeTracker(player)
        self._label_tracker.connect("tick", self._on_tick_label, player)

        self._redraw_tracker = TimeTracker(player)
        self._redraw_tracker.connect("tick", self._on_tick_waveform, player)

        connect_destroy(player, "seek", self._on_player_seek)
        connect_destroy(player, "song-started", self._on_song_started)
        connect_destroy(player, "song-ended", self._on_song_ended)
        connect_destroy(player, "notify::seekable", self._on_seekable_changed)
        connect_destroy(library, "changed", self._on_song_changed, player)

        self.connect("destroy", self._on_destroy)
        self._update(player)

        if player.info:
            self._create_waveform(player.info, CONFIG.max_data_points)

    def set_time_label_visibility(self, is_visible):
        self._time_labels_visible = is_visible
        if is_visible:
            self._elapsed_label.show()
            self._remaining_label.show()
        else:
            self._elapsed_label.hide()
            self._remaining_label.hide()

    def _create_waveform(self, song, points):
        # Close any existing pipeline to avoid leaks
        self._clean_pipeline()

        if not song.is_file:
            return

        command_template = """
        uridecodebin name=uridec
        ! audioconvert
        ! level name=audiolevel interval={} post-messages=true
        ! fakesink sync=false"""
        interval = int(song("~#length") * 1e9 / points)
        if not interval:
            return
        print_d("Computing data for each %.3f seconds" % (interval / 1e9))

        command = command_template.format(interval)
        pipeline = Gst.parse_launch(command)
        pipeline.get_by_name("uridec").set_property("uri", uri2gsturi(song("~uri")))

        bus = pipeline.get_bus()
        self._bus_id = bus.connect("message", self._on_bus_message, points)
        bus.add_signal_watch()

        pipeline.set_state(Gst.State.PLAYING)

        self._pipeline = pipeline
        self._new_rms_vals = []

    def _on_bus_message(self, bus, message, points):
        force_stop = False
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            print_d(f"Error received from element {message.src.get_name()}: {error}")
            print_d(f"Debugging information: {debug}")
        elif message.type == Gst.MessageType.ELEMENT:
            structure = message.get_structure()
            if structure.get_name() == "level":
                rms_db = structure.get_value("rms")
                if rms_db:
                    # Calculate average of all channels (usually 2)
                    rms_db_avg = sum(rms_db) / len(rms_db)
                    # Normalize dB value to value between 0 and 1
                    rms = pow(10, (rms_db_avg / 20))
                    self._new_rms_vals.append(rms)
                    if len(self._new_rms_vals) >= points:
                        # The audio might be much longer than we anticipated
                        # and we would get way too many events due to the too
                        # short interval set.
                        force_stop = True
            else:
                print_w(f"Got unexpected message of type {message.type}")

        if message.type == Gst.MessageType.EOS or force_stop:
            self._clean_pipeline()

            # Update the waveform with the new data
            self._rms_vals = self._new_rms_vals
            self._waveform_scale.reset(self._rms_vals)
            self._update_redraw_interval()

            # Clear temporary reference to the waveform data
            del self._new_rms_vals

    def _clean_pipeline(self):
        if hasattr(self, "_pipeline") and self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
            if self._bus_id:
                bus = self._pipeline.get_bus()
                bus.remove_signal_watch()
                bus.disconnect(self._bus_id)
                self._bus_id = None
            if self._pipeline:
                self._pipeline = None

    def _update_redraw_interval(self, *args):
        if self._player.info and self.is_visible():
            # Must be recomputed when size is changed
            interval = self._waveform_scale.compute_redraw_interval()
            self._redraw_tracker.set_interval(interval)

    def _on_destroy(self, *args):
        self._clean_pipeline()
        self._label_tracker.destroy()
        self._redraw_tracker.destroy()

    def _on_tick_label(self, tracker, player):
        self._update_label(player)

    def _on_tick_waveform(self, tracker, player):
        self._update_waveform(player)

    def _on_seekable_changed(self, player, *args):
        self._update_label(player)

    def _on_player_seek(self, player, song, ms):
        self._update(player)

    def _on_song_changed(self, library, songs, player):
        if not player.info:
            return
        # Check that the currently playing song has changed
        if player.info in songs:
            # Trigger a re-computation of the waveform
            self._create_waveform(player.info, CONFIG.max_data_points)
            self._resize_labels(player.info)
            # Only update the label if some tag value changed
            self._update_label(player)

    def _on_song_started(self, player, song):
        if player.info:
            # Trigger a re-computation of the waveform
            self._create_waveform(player.info, CONFIG.max_data_points)
            self._resize_labels(player.info)

        self._rms_vals.clear()
        self._update(player, True)

    def _on_song_ended(self, player, song, ended):
        self._update(player)

    def _update(self, player, full_redraw=False):
        self._update_label(player)
        self._update_waveform(player, full_redraw)

    def _update_label(self, player):
        if not self._time_labels_visible:
            self.set_sensitive(player.info is not None and player.seekable)
            return

        if player.info:
            if self._hovering:
                # Show the position pointed by the mouse
                position = self._waveform_scale.get_mouse_position()
            else:
                # Show the position of the player (converted in seconds)
                position = player.get_position() / 1000.0
            length = player.info("~#length")
            remaining = length - position

            self._elapsed_label.set_time(position)
            self._remaining_label.set_time(remaining)

            self._elapsed_label.set_disabled(not player.seekable)
            self._remaining_label.set_disabled(not player.seekable)
            self.set_sensitive(player.seekable)
        else:
            self._remaining_label.set_disabled(True)
            self._elapsed_label.set_disabled(True)
            self.set_sensitive(False)

    def _update_waveform(self, player, full_redraw=False):
        if player.info:
            # Position in ms, length in seconds
            position = player.get_position() / 1000.0
            length = player.info("~#length")

            if length != 0:
                self._waveform_scale.set_position(position / length)
            else:
                print_d(f"Length reported as zero for {player.info}")
                self._waveform_scale.set_position(0)

            if position == 0 or full_redraw:
                self._waveform_scale.queue_draw()
            else:
                (x, y, w, h) = self._waveform_scale.compute_redraw_area()
                self._waveform_scale.queue_draw_area(x, y, w, h)
        else:
            self._rms_vals.clear()
            self._waveform_scale.queue_draw()

    def _on_mouse_hover(self, _, event):
        def clamp(a, x, b):
            """Return x if a <= x <= b, else the a or b nearest to x."""
            return min(max(x, a), b)

        width = self._waveform_scale.get_allocation().width
        self._waveform_scale.set_mouse_x_position(clamp(0, event.x, width))

        if self._hovering:
            (x, y, w, h) = self._waveform_scale.compute_hover_redraw_area()
            self._waveform_scale.queue_draw_area(x, y, w, h)
        else:
            self._waveform_scale.queue_draw()

        self._update_label(self._player)
        self._hovering = True

    def _on_mouse_leave(self, _, event):
        self._waveform_scale.set_mouse_x_position(-1)
        self._waveform_scale.queue_draw()

        self._hovering = False
        self._update_label(self._player)

    def _resize_labels(self, song):
        """Resize the labels to make sure there is enough space to display the
        length of the songs.

        This prevents the waveform from changing size when the position changes
        from 9:59 to 10:00 for example."""
        length = util.format_time_display(song("~#length"))

        # Get the width needed to display the length of the song (the text
        # displayed in the labels will always be shorter than that)
        layout = self._remaining_label.get_layout()
        layout.set_text(length, -1)
        width, height = layout.get_pixel_size()

        # Set it as the minimum width of the labels to prevent them from
        # changing width
        self._remaining_label.set_size_request(width, -1)
        self._elapsed_label.set_size_request(width, -1)


class WaveformScale(Gtk.Box):
    """The waveform widget."""

    _rms_vals: list[int] = []
    _player = None

    def __init__(self, player):
        super().__init__()
        self._player = player
        self.set_size_request(40, CONFIG.height_px)
        self.position = 0
        self._last_drawn_position = 0
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(alpha=0))

        self.mouse_position = -1
        self._last_mouse_position = -1
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        self._seeking = False

    @property
    def width(self):
        return self.get_allocation().width

    def reset(self, rms_vals):
        self._rms_vals = rms_vals
        self._seeking = False
        self.queue_draw()

    @classmethod
    def reset_config(cls):
        cls.hover_color.cache_clear()
        cls.remaining_color.cache_clear()
        cls.elapsed_color.cache_clear()

    def compute_redraw_interval(self):
        allocation = self.get_allocation()
        width = allocation.width

        scale_factor = self.get_scale_factor()
        pixel_ratio = float(scale_factor)

        # Compute the coarsest time interval for redraws
        length = self._player.info("~#length")
        if length == 0:
            # The length is 0 for example when playing a stream from
            # Internet radio. If 0 is passed forward as the update interval,
            # UI will freeze as it will try to update continuously.
            # The update interval is usually 1 second so use that instead.
            print_d(
                f"Length is zero for {self._player.info}, "
                "using redraw interval of 1000 ms"
            )
            return 1000
        return length * 1000 / max(width * pixel_ratio, 1)

    def compute_redraw_area(self):
        width = self.width
        last_position_x = self._last_drawn_position * width
        position_x = self.position * width
        return self._compute_redraw_area_between(last_position_x, position_x)

    def compute_hover_redraw_area(self):
        return self._compute_redraw_area_between(
            self._last_mouse_position, self.mouse_position
        )

    def _compute_redraw_area_between(self, x1, x2):
        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height

        scale_factor = self.get_scale_factor()
        pixel_ratio = float(scale_factor)
        line_width = 1.0 / pixel_ratio

        # Compute the thinnest rectangle to redraw
        x = max(0.0, min(x1, x2) - line_width * 5)
        w = min(width, abs(x2 - x1) + line_width * 10)
        return x, 0.0, w, height

    def draw_waveform(
        self,
        cr,
        width,
        height,
        elapsed_color,
        hover_color,
        remaining_color,
        show_current_pos_config,
    ):
        if width == 0 or height == 0:
            return
        scale_factor = self.get_scale_factor()
        pixel_ratio = float(scale_factor)
        line_width = 1.0 / pixel_ratio

        half_height = self.compute_half_height(height, pixel_ratio)

        value_count = len(self._rms_vals)
        max_value = max(self._rms_vals)
        ratio_width = value_count / (float(width) * pixel_ratio)
        ratio_height = max_value / half_height

        cr.set_line_width(line_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

        position_width = self.position * width * pixel_ratio
        mouse_position = self.mouse_position * scale_factor

        hw = line_width / 2.0
        # Avoiding object lookups is slightly faster
        data = self._rms_vals

        # Use the clip rectangles to redraw only what is necessary
        for cx, _cy, cw, _ch in cr.copy_clip_rectangle_list():
            for x in range(
                int(floor(cx * pixel_ratio)), int(ceil((cx + cw) * pixel_ratio)), 1
            ):
                if mouse_position >= 0:
                    if self._seeking:
                        # The user is seeking (holding mousebutton down)
                        fg_color = (
                            elapsed_color if x < mouse_position else remaining_color
                        )
                    elif show_current_pos_config:
                        # Use hover color and elapsed color to display the
                        # current playing position while hovering
                        if x < mouse_position:
                            if x < position_width:
                                fg_color = elapsed_color
                            else:
                                fg_color = hover_color
                        elif x < position_width:
                            fg_color = hover_color
                        else:
                            fg_color = remaining_color
                    else:
                        # The mouse is hovering the seekbar
                        fg_color = (
                            hover_color if x < mouse_position else remaining_color
                        )
                else:
                    fg_color = elapsed_color if x < position_width else remaining_color

                cr.set_source_rgba(*list(fg_color))

                # Basic anti-aliasing / oversampling
                u1 = max(0, int(floor((x - hw) * ratio_width)))
                u2 = min(int(ceil((x + hw) * ratio_width)), len(data))
                val = sum(data[u1:u2]) / (ratio_height * (u2 - u1)) if u1 != u2 else 0.0

                hx = x / pixel_ratio + hw
                cr.move_to(hx, half_height - val)
                cr.line_to(hx, half_height + val)
                cr.stroke()

        self._last_drawn_position = self.position
        self._last_mouse_position = self.mouse_position

    def draw_placeholder(self, cr, width, height, color: Gdk.RGBA):
        if width == 0 or height == 0:
            return
        scale_factor = self.get_scale_factor()
        pixel_ratio = float(scale_factor)
        line_width = 1.0 / pixel_ratio
        position_width = self.position * width * pixel_ratio

        half_height = self.compute_half_height(height, pixel_ratio)
        hw = line_width / 2.0

        cr.set_line_width(line_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_source_rgba(*self.elapsed_color(self.get_style_context()))
        cr.move_to(hw, half_height)
        cr.rectangle(hw, half_height - line_width, position_width - hw, line_width * 2)
        cr.fill()

        cr.set_source_rgba(*color)
        cr.move_to(position_width, half_height)
        cr.line_to(width, half_height)
        cr.stroke()

    @staticmethod
    def compute_half_height(height, pixel_ratio):
        # Ensure half_height is in the middle of a pixel (c.f. Cairo's FAQ)
        height_px = int(height * pixel_ratio)
        return (height_px if height_px % 2 else height_px - 1) / pixel_ratio / 2

    def do_draw(self, cr):
        context = self.get_style_context()

        # Get colors
        context.save()
        context.set_state(Gtk.StateFlags.NORMAL)
        bg_color = context.get_background_color(context.get_state())
        context.restore()

        # Paint the background
        cr.set_source_rgba(*list(bg_color))
        cr.paint()

        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height

        if self._rms_vals:
            self.draw_waveform(
                cr,
                width,
                height,
                self.elapsed_color(context),
                self.hover_color(context),
                self.remaining_color(context),
                CONFIG.show_current_pos,
            )
        else:
            self.draw_placeholder(cr, width, height, self.remaining_color(context))

    @classmethod
    @lru_cache
    def elapsed_color(cls, context: Gtk.StyleContext) -> Gdk.RGBA:
        # Check if the user set a different elapsed color in the config
        return (
            parse_color(text)
            if (text := CONFIG.elapsed_color)
            else get_fg_highlight_color(context)
        )

    @classmethod
    @lru_cache
    def hover_color(cls, context: Gtk.StyleContext) -> Gdk.RGBA:
        if CONFIG.hover_color:
            return parse_color(CONFIG.hover_color)
        opacity = 0.4
        elapsed = cls.elapsed_color(context)
        remaining = cls.remaining_color(context)
        r = (
            opacity * elapsed.alpha * elapsed.red
            + (1 - opacity) * remaining.alpha * remaining.red
        )
        g = (
            opacity * elapsed.alpha * elapsed.green
            + (1 - opacity) * remaining.alpha * remaining.green
        )
        b = (
            opacity * elapsed.alpha * elapsed.blue
            + (1 - opacity) * remaining.alpha * remaining.blue
        )
        a = opacity * elapsed.alpha + (1 - opacity) * remaining.alpha
        return Gdk.RGBA(r, g, b, a)

    @classmethod
    @lru_cache
    def remaining_color(cls, context: Gtk.StyleContext) -> Gdk.RGBA:
        if CONFIG.remaining_color:
            return parse_color(CONFIG.remaining_color)
        default = context.get_color(context.get_state())
        default.alpha = 0.35
        return default

    def do_button_press_event(self, event):
        # Left mouse button
        if event.button == 1 and self._player:
            self._seeking = True
            self.queue_draw()

    def do_button_release_event(self, event):
        # Left mouse button
        if event.button == 1 and self._player:
            ratio = event.x / self.get_allocation().width
            length = self._player.info("~#length")
            self._player.seek(ratio * length * 1000)
            self._seeking = False
            self.queue_draw()
            return True
        return None

    def do_scroll_event(self, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self._player.seek(self._player.get_position() + CONFIG.seek_amount)
            self.queue_draw()
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self._player.seek(self._player.get_position() - CONFIG.seek_amount)
            self.queue_draw()

    def set_position(self, position):
        self.position = position

    def set_mouse_x_position(self, mouse_position):
        """Set the horizontal position of the mouse in pixel"""
        self.mouse_position = mouse_position

    def get_mouse_position(self):
        """Return the position of the song pointed by the mouse in seconds"""
        ratio = self.mouse_position / self.get_allocation().width
        length = self._player.info("~#length")
        return ratio * length


class WaveformSeekBarPlugin(EventPlugin):
    """The plugin class."""

    PLUGIN_ID = "WaveformSeekBar"
    PLUGIN_NAME = _("Waveform Seek Bar")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_CONFIG_SECTION = __name__
    PLUGIN_DESC = _("∿ A seekbar in the shape of the waveform of the current song.")

    def __init__(self):
        self._bar = None

    def enabled(self):
        self._bar = WaveformSeekBar(app.player, app.librarian)
        self._bar.show()
        app.window.set_seekbar_widget(self._bar)

    def disabled(self):
        app.window.set_seekbar_widget(None)
        self._bar.destroy()
        self._bar = None

    def PluginPreferences(self, parent):
        def colour_changed(c: Gdk.RGBA, config_key: str):
            # This can get parsed back, so we're OK writing it
            string = c.to_string()
            print_d(f"Saving {string} for {config_key}")
            setattr(CONFIG, config_key, string)
            WaveformScale.reset_config()
            # It's nice to refresh the running one
            self._bar._waveform_scale.queue_draw()

        def on_show_pos_toggled(button, *args):
            CONFIG.show_current_pos = button.get_active()

        def seek_amount_changed(spinbox):
            CONFIG.seek_amount = spinbox.get_value_as_int()

        def on_show_time_labels_toggled(button, *args):
            CONFIG.show_time_labels = button.get_active()
            if self._bar is not None:
                self._bar.set_time_label_visibility(CONFIG.show_time_labels)

        def on_height_px_changed(spinbox):
            CONFIG.height_px = spinbox.get_value_as_int()
            if self._bar is not None and self._bar._waveform_scale is not None:
                self._bar._waveform_scale.set_size_request(40, CONFIG.height_px)

        def create_color(label_text, config_item):
            hbox = Gtk.Box(spacing=6)
            label = Gtk.Label(label=label_text)
            label.set_alignment(0.0, 0.5)
            hbox.prepend(label, False, True, 0)
            colour = getattr(CONFIG, config_item)
            colour_label = Gtk.Label()
            colour_label.set_alignment(0.0, 0.5)
            colour_label.set_size_request(160, -1)

            def colour_updated(_widget, c: Gdk.RGBA):
                colour_changed(c, config_item)
                colour = c.to_string()
                add_css(
                    colour_label,
                    f"* {{ background-color: {colour}; border:1px solid #666; }}",
                )

            def on_clicked(*args):
                chooser = Gtk.ColorChooserDialog()
                chooser.set_property("use-alpha", True)
                chooser.set_rgba(parse_color(colour))
                chooser.connect("color-activated", colour_updated)
                chooser.connect("response", on_exited)
                chooser.run()

            def on_exited(dialog: Gtk.ColorChooserDialog, code):
                colour_updated(dialog, dialog.get_rgba())
                dialog.destroy()

            button = Gtk.Button()
            button.connect("clicked", on_clicked)
            button.add(SymbolicIconImage(Icons.EDIT, Gtk.IconSize.NORMAL))
            if colour:
                add_css(
                    colour_label,
                    f"""* {{
                   background-color: {colour};
                   border-radius: 3px;
                   border: 1px solid rgba(128,128,128,0.5);
                }}""",
                )
            hbox.append(button, False, False, 0)
            hbox.append(colour_label, False, True, 0)
            return hbox

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        box = create_color(_("Foreground color"), "elapsed_color")
        vbox.prepend(box, True, True, 0)

        box = create_color(_("Hover color"), "hover_color")
        vbox.prepend(box, True, True, 0)

        box = create_color(_("Remaining color"), "remaining_color")
        vbox.prepend(box, True, True, 0)

        sw = Gtk.Switch()
        label = Gtk.Label(_("Show current position whilst hovering"))
        sw.set_active(CONFIG.show_current_pos)
        sw.connect("notify::active", on_show_pos_toggled)
        hbox = Gtk.Box(spacing=6)
        hbox.prepend(label, False, True, 0)
        hbox.append(sw, False, True, 0)
        vbox.prepend(hbox, True, True, 0)

        sw = Gtk.Switch()
        label = Gtk.Label(_("Show time labels"))
        sw.set_active(CONFIG.show_time_labels)
        sw.connect("notify::active", on_show_time_labels_toggled)
        hbox = Gtk.Box(spacing=6)
        hbox.prepend(label, False, True, 0)
        hbox.append(sw, False, True, 0)
        vbox.prepend(hbox, True, True, 0)

        hbox = Gtk.Box(spacing=6)
        label = Gtk.Label(label=_("Seek amount when scrolling (milliseconds):"))
        hbox.prepend(label, False, True, 0)
        seek_amount = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(CONFIG.seek_amount, 0, 60000, 1000, 1000, 0)
        )
        seek_amount.set_numeric(True)
        seek_amount.connect("changed", seek_amount_changed)
        hbox.append(seek_amount, False, True, 0)
        vbox.prepend(hbox, True, True, 0)

        hbox = Gtk.Box(spacing=6)
        label = Gtk.Label(label=_("Waveform height (pixels):"))
        hbox.prepend(label, False, True, 0)
        height_px = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(CONFIG.height_px, 40, 400, 10, 10, 0)
        )
        height_px.set_numeric(True)
        height_px.connect("changed", on_height_px_changed)
        hbox.append(height_px, False, True, 0)
        vbox.prepend(hbox, True, True, 0)

        return vbox
