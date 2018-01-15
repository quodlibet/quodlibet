# -*- coding: utf-8 -*-
# Copyright 2010 Steven Robertson
#           2012 Christoph Reiter
#           2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# TODO: Include saving and loading.

from gi.repository import Gtk, Gdk

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet.qltk import Button, Icons
from quodlibet.plugins.events import EventPlugin
from quodlibet.compat import iteritems


# Presets (roughly) taken from Pulseaudio equalizer
PRESET_BANDS = [50, 100, 156, 220, 311, 440, 622, 880, 1250, 1750, 2500,
                3500, 5000, 10000, 20000]
PRESETS = {
    "flat": (_("Flat"), [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    "live": (_("Live"), [-9.0, -5.5, 0.0, 1.5, 2.0, 3.5, 3.5, 3.5, 3.5,
                         3.5, 3.5, 3.5, 3.0, 1.5, 2.0]),
    "full_bass_treble": (_("Full Bass & Treble"),
                         [5.0, 5.0, 3.5, 2.5, 0.0, -7.0, -14.0, -10.0, -10.0,
                          -8.0, 1.0, 1.0, 5.0, 7.5, 9.5]),
    "club": (_("Club"), [0.0, 0.0, 0.0, 0.0, 3.5, 3.5, 3.5, 3.5, 3.5,
                         3.5, 3.5, 2.5, 2.5, 0.0, 0.0]),
    "large_hall": (_("Large Hall"), [7.0, 7.0, 7.0, 3.5, 3.0, 3.0, 3.0, 1.5,
                                     0.0, -2.0, -3.5, -6.0, -9.0, -1.0, 0.0]),
    "party": (_("Party"), [5.0, 5.0, 5.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                           0.0, 0.0, 0.0, 2.5, 5.0]),
    "rock": (_("Rock"), [5.5, 2.5, 2.5, -8.5, -10.5, -11.0, -16.0, -14.5,
                         -6.5, -5.5, -3.0, 3.0, 6.5, 7.0, 7.0]),
    "soft": (_("Soft"), [3.0, 3.0, 1.0, 1.0, 0.0, -2.5, -5.0, 1.5, 0.0, 1.0,
                         3.0, 3.0, 6.0, 8.0, 8.0]),
    "full_bass": (_("Full Bass"),
                  [-16.0, -16.0, 6.5, 6.5, 6.0, 5.5, 4.5, 1.0, 1.0, 1.0, -8.0,
                   -10.0, -16.0, -16.0, -20.5]),
    "classical": (_("Classical"),
                  [0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, -21.0, -21.0, -27.0]),
    "reggae": (_("Reggae"), [0.0, 0.0, 0.0, 0.0, 0.0, -4.5, -10.0, -6.0, 0.5,
                             1.0, 2.0, 4.0, 4.0, 0.0, 0.0]),
    "headphones": (_("Headphones"),
                   [3.0, 3.0, 7.0, 7.0, 3.0, -1.0, -6.5, -6.0, -4.5, -4.0,
                    1.0, 1.0, 6.0, 8.0, 9.0]),
    "soft_rock": (_("Soft Rock"), [3.0, 3.0, 3.0, 1.5, 1.5, 1.5, 0.0, -3.5,
                                   -8.0, -7.0, -10, -9.0, -6.5, 1.5, 6.0]),
    "full_treble": (_("Full Treble"),
                    [5.0, -18.5, -18.5, -18.5, -18.5, -10.0, -8.0, -6.5, 1.5,
                     1.5, 1.5, 8.5, 10.5, 10.5, 10.5]),
    "dance": (_("Dance"), [6.0, 4.0, 4.0, 1.5, 1.5, 1.5, 0.0, 0.0, 0.0,
                           1.0, -10.5, -14.0, -15.0, -7.0, 0.0]),
    "pop": (_("Pop"), [-3.5, 1.0, 2.0, 3.0, 5.0, 5.5, 6.5, 5.0, 3.0, 1.5, 0.0,
                       -2.5, -5.0, -5.0, -3.0]),
    "techno": (_("Techno"), [5.0, 4.0, 4.0, 3.0, 0.0, -4.5, -10.0, -9.0, -8.0,
                             -5.5, -1.5, 3.0, 6.0, 6.0, 6.0]),
    "ska": (_("Ska"), [-4.5, -8.0, -9.0, -8.5, -8.0, -6.0, 0.0, 1.5, 2.5, 2.5,
                       3.0, 3.0, 6.0, 6.0, 6.0]),
    "laptop": (_("Laptop"), [-1, -1, -1, -1, -5, -10, -18, -15, -10, -5, -5,
                             -5, -5, 0, 0]),
}


def interp_bands(src_band, target_band, src_gain):
    """Linear interp from one band to another. All must be sorted."""
    gain = []
    for i, b in enumerate(target_band):
        if b in src_band:
            gain.append(src_gain[i])
            continue
        idx = sorted(src_band + [b]).index(b)
        idx = min(max(idx, 1), len(src_band) - 1)
        x1, x2 = src_band[idx - 1:idx + 1]
        y1, y2 = src_gain[idx - 1:idx + 1]
        g = y1 + ((y2 - y1) * (b - x1)) / float(x2 - x1)
        gain.append(min(12.0, g))
    return gain


def get_config():
    try:
        eq_levels_str = config.get('plugins', 'equalizer_levels')
        return [float(s) for s in eq_levels_str.split(',')]
    except (config.Error, ValueError):
        return []


class Equalizer(EventPlugin):
    PLUGIN_ID = "Equalizer"
    PLUGIN_NAME = _("Equalizer")
    PLUGIN_DESC = _("Controls the tone of your music with an equalizer.\n"
                    "Click or use keys to customise levels "
                    "(right-click resets the band).")
    PLUGIN_ICON = Icons.AUDIO_CARD

    @property
    def player_has_eq(self):
        return hasattr(app.player, 'eq_bands') and app.player.eq_bands

    def __init__(self):
        super(Equalizer, self).__init__()
        self._enabled = False

    def apply(self):
        if not self.player_has_eq:
            return
        levels = self._enabled and get_config() or []
        lbands = len(app.player.eq_bands)
        app.player.eq_values = (levels[:min(len(levels), lbands)] +
                                   [0.] * max(0, (lbands - len(levels))))

    def enabled(self):
        self._enabled = True
        self.apply()

    def disabled(self):
        self._enabled = False
        self.apply()

    def PluginPreferences(self, win):
        vb = Gtk.VBox(spacing=6)
        if not self.player_has_eq:
            l = Gtk.Label()
            l.set_markup(
                _('The current backend does not support equalization.'))
            vb.pack_start(l, False, True, 0)
            return vb

        def format_hertz(band):
            if band >= 1000:
                return _('%.1f kHz') % (band / 1000.)
            return _('%d Hz') % band

        bands = [format_hertz(band) for band in app.player.eq_bands]
        levels = get_config() + [0.] * len(bands)

        table = Gtk.Table(rows=len(bands), columns=3)
        table.set_col_spacings(6)

        def set_band(adj, idx):
            rounded = int(adj.get_value() * 2) / 2.0
            adj.set_value(rounded)
            levels[idx] = rounded
            config.set('plugins', 'equalizer_levels',
                       ','.join(str(lv) for lv in levels))
            self.apply()

        adjustments = []

        for i, band in enumerate(bands):
            # align numbers and suffixes in separate rows for great justice
            lbl = Gtk.Label(label=band.split()[0])
            lbl.set_alignment(1, 0.5)
            lbl.set_padding(0, 4)
            table.attach(lbl, 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            lbl = Gtk.Label(label=band.split()[1])
            lbl.set_alignment(1, 0.5)
            table.attach(lbl, 1, 2, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            adj = Gtk.Adjustment.new(levels[i], -24., 12., 0.5, 3, 0)
            adj.connect('value-changed', set_band, i)
            adjustments.append(adj)
            hs = Gtk.HScale(adjustment=adj)
            hs.connect('button-press-event', self.__rightclick)
            hs.set_draw_value(True)
            hs.set_value_pos(Gtk.PositionType.RIGHT)
            hs.connect('format-value', lambda s, v: _('%.1f dB') % v)
            table.attach(hs, 2, 3, i, i + 1)
        vb.pack_start(table, True, True, 0)

        def clicked_cb(button):
            [adj.set_value(0) for adj in adjustments]

        sorted_presets = sorted(iteritems(PRESETS))

        def combo_changed(combo):
            # custom, skip
            if not combo.get_active():
                return
            gain = sorted_presets[combo.get_active() - 1][1][1]
            gain = interp_bands(PRESET_BANDS, app.player.eq_bands, gain)
            for (g, a) in zip(gain, adjustments):
                a.set_value(g)

        combo = Gtk.ComboBoxText()
        combo.append_text(_("Custom"))
        combo.set_active(0)
        for key, (name, gain) in sorted_presets:
            combo.append_text(name)
        combo.connect("changed", combo_changed)

        bbox = Gtk.HButtonBox()
        clear = Button(_("_Clear"), Icons.EDIT_CLEAR)
        clear.connect('clicked', clicked_cb)
        bbox.pack_start(combo, True, True, 0)
        bbox.pack_start(clear, True, True, 0)
        vb.pack_start(bbox, True, True, 0)
        return vb

    def __rightclick(self, hs, event):
        if event.button == Gdk.BUTTON_SECONDARY:
            hs.set_value(0)
