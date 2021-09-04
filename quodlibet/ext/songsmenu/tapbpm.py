# Copyright 2017 Didier Villevalois,
#           2010 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, Gtk

from quodlibet import _
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.window import Dialog


class TapBpmPanel(Gtk.VBox):
    def __init__(self, parent, song):
        super().__init__()

        self.dialog = parent
        self.song = song
        self.original_bpm = song["bpm"] if "bpm" in song else _("n/a")

        self.set_margin_bottom(6)
        self.set_spacing(6)

        box = Gtk.HBox()
        box.set_spacing(6)
        # TRANSLATORS: BPM mean "beats per minute"
        box.pack_start(Gtk.Label(_("BPM:")), False, True, 0)
        self.bpm_label = Gtk.Label(_("n/a"))
        self.bpm_label.set_xalign(0.5)
        box.pack_start(self.bpm_label, True, True, 0)

        self.reset_btn = Gtk.Button(label=_("Reset"))
        self.reset_btn.connect('clicked', lambda *x: self.reset())
        box.pack_end(self.reset_btn, False, True, 0)

        self.pack_start(box, False, True, 0)

        self.tap_btn = Gtk.Button(label=_("Tap"))
        self.tap_btn.connect('button-press-event', self.tap)
        self.tap_btn.connect('key-press-event', self.key_tap)
        self.pack_start(self.tap_btn, True, True, 0)

        self.init_tap()
        self.update()

        self.show_all()

    def update(self):
        has_new_bpm = self.clicks > 1

        self.dialog.set_response_sensitive(Gtk.ResponseType.OK, has_new_bpm)
        self.reset_btn.set_sensitive(has_new_bpm)

        if self.clicks > 1:
            self.bpm_label.set_text("%.1f" % self.floating_bpm)
        elif self.clicks == 1:
            self.bpm_label.set_text(_("n/a"))
        else:
            self.bpm_label.set_text(str(self.original_bpm))

        # Give focus back to the tap button even if reset was pressed
        self.tap_btn.grab_focus()

    def tap(self, widget, event):
        self.count_tap(event.time)
        self.update()

    def key_tap(self, widget, event):
        if event.keyval != Gdk.KEY_space \
                and event.keyval != Gdk.KEY_Return:
            return False

        self.count_tap(event.time)
        self.update()
        return True

    def reset(self):
        self.init_tap()
        self.update()

    def save(self):
        self.song["bpm"] = "%.0f" % self.floating_bpm
        self.song.write()

    def init_tap(self):
        self.bpm = 0.0
        self.clicks = 0
        self.last = 0
        self.last_times = []
        self.last_bpms = []
        self.last_floating_bpms = []
        self.last_floating_squares = []
        self.bpms_sum = 0.0
        self.squares_sum = 0.0
        self.average_count = 0
        self.min = 0
        self.max = 0
        try:
            self.floating_bpm = float(self.original_bpm)
        except ValueError:
            self.floating_bpm = 0.0
        self.floating_square = 0.0
        self.keep = 100

        self.pause = 3
        self.min_weight = 0.01

    def count_tap(self, now):
        now = now / 1000.
        # reset?
        if now - self.last > self.pause:
            self.clicks = 0
            self.bpm = 0.0

            self.last_times = []
            self.last_bpms = []
            self.last_floating_bpms = []
            self.last_floating_squares = []
            self.bpms_sum = 0.0
            self.squares_sum = 0.0
            self.average_count = 0
            self.min = 0
            self.max = 0
            self.floating_bpm = 0.0
            self.floating_square = 0.0
        elif now > self.last:
            # Use previous 5 values to average BPM
            bpms = []
            bpms.append(60.0 / (now - self.last))
            # and four out of the list
            for i in iter(range(1, 5)):
                if len(self.last_times) <= i:
                    break
                bpms.append((i + 1) * 60.0 / (now - self.last_times[-i]))

            self.bpm = sum(bpms) / len(bpms)

            # Exponentially weighted floating average
            weight = (1.0 / self.clicks) ** .5
            if weight < self.min_weight:
                weight = self.min_weight
            self.floating_bpm = \
                self.floating_bpm * (1.0 - weight) \
                + self.bpm * weight
            self.floating_square = \
                self.floating_square * (1.0 - weight) \
                + self.bpm * self.bpm * weight

            if self.bpm < self.min or self.average_count == 0:
                self.min = self.bpm
            if self.bpm > self.max or self.average_count == 0:
                self.max = self.bpm
            self.bpms_sum += self.bpm
            self.squares_sum += self.bpm * self.bpm
            self.average_count += 1

            # Update history
            self.last_times = self.last_times[-(self.keep - 1):] + [self.last]
            self.last_bpms = self.last_bpms[-(self.keep - 1):] + [self.bpm]
            self.last_floating_bpms = \
                self.last_floating_bpms[-(self.keep - 1):] \
                + [self.floating_bpm]
            self.last_floating_squares = \
                self.last_floating_squares[-(self.keep - 1):] \
                + [self.floating_square]

        self.last = now
        self.clicks += 1


class TapBpm(SongsMenuPlugin):
    PLUGIN_ID = "Tap BPM"
    PLUGIN_NAME = _("Tap BPM")
    PLUGIN_DESC = _("🥁 Tap BPM for the selected song.")
    PLUGIN_ICON = Icons.EDIT
    PLUGIN_VERSION = "0.1"

    def plugin_song(self, song):
        self._window = window = \
            Dialog(title=_("Tap BPM"), parent=self.plugin_window)

        window.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        window.add_icon_button(_("_Save"), Icons.DOCUMENT_SAVE,
                             Gtk.ResponseType.OK)

        window.set_default_size(300, 100)
        window.set_border_width(6)
        self.__resp_sig = window.connect('response', self.response)

        self._panel = TapBpmPanel(window, song)
        window.vbox.pack_start(self._panel, False, True, 0)

        window.vbox.show_all()
        window.present()

    def response(self, win, response):
        if response == Gtk.ResponseType.OK:
            # Save metadata
            self._panel.save()

        win.hide()
        win.disconnect(self.__resp_sig)
        win.destroy()
