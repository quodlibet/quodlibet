# Copyright 2010 Steven Robertson
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# TODO: Include presets, saving and loading.

import gtk

from quodlibet import app
from quodlibet import config
from quodlibet.plugins.events import EventPlugin

# Presets taken from pulseaudio equalizer
PRESET_BANDS = [50, 100, 156, 220, 311, 440, 622, 880, 1250, 1750, 2500,
                3500, 5000, 10000, 20000]
PRESETS = {
    "flat": (_("Flat"), [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    "live": (_("Live"), [-9.0, -5.5, 0.0, 1.5, 2.1, 3.4, 3.4, 3.4, 3.4,
                         3.4, 3.4, 3.4, 2.8, 1.6, 1.8]),
    "full_bass_treble": (_("Full Bass & Treble"),
                         [4.8, 4.8, 3.5, 2.5, 0.0, -7.0, -14.0, -10.0, -10.0,
                          -8.0, 1.0, 1.0, 5.2, 7.7, 9.5]),
    "club": (_("Club"), [-0.2, -0.2, -0.2, -0.2, 3.5, 3.5, 3.5, 3.5, 3.5,
                         3.5, 3.5, 2.5, 2.5, 0.0, 0.0]),
    "large_hall": (_("Large Hall"), [7.0, 7.0, 7.0, 3.5, 3.0, 3.0, 3.0, 1.5,
                                     0.0, -2.0, -3.5, -6.0, -9.0, -1.0, 0.0]),
    "party": (_("Party"), [4.8, 4.8, 4.8, 3.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                           0.0, 0.0, 0.0, 2.5, 4.8]),
    "rock": (_("Rock"), [5.3, 2.6, 2.6, -8.5, -10.5, -11.2, -16.0, -14.7,
                         -6.6, -5.7, -3.0, 3.0, 6.7, 7.3, 7.3]),
    "soft": (_("Soft"), [3.2, 2.8, 0.8, 0.9, 0.0, -2.4, -4.8, 1.5, 0.0, 1.1,
                         3.0, 3.0, 5.8, 7.8, 7.8]),
    "full_bass": (_("Full Bass"),
                  [-16.0, -16.0, 6.5, 6.5, 6.0, 5.5, 4.5, 1.0, 1.0, 1.0, -8.0,
                   -10.0, -16.0, -16.0, -20.4]),
    "classical": (_("Classical"),
                  [-0.2, -0.2, -0.2, -0.2, -0.2, -0.2, -0.2, -0.2, -0.2,
                   -0.2, -0.2, -0.2, -21.0, -21.0, -27.0]),
    "reggae": (_("Reggae"), [0.0, 0.0, 0.0, 0.0, 0.0, -4.5, -10.0, -6.0, 0.5,
                             1.0, 2.0, 4.0, 4.0, 0.0, 0.0]),
    "headphones": (_("Headphones"),
                   [3.0, 3.0, 7.3, 7.0, 3.0, -1.0, -6.6, -6.3, -4.5, -4.0,
                    1.1, 1.2, 5.8, 7.9, 8.8]),
    "soft_rock": (_("Soft Rock"), [2.7, 2.7, 2.7, 1.5, 1.5, 1.4, 0.0, -3.6,
                                   -8.0, -7.2, -9.8, -8.9, -6.6, 1.4, 5.8]),
    "full_treble": (_("Full Treble"),
                    [4.8, -18.6, -18.6, -18.6, -18.6, -10.0, -8.0, -6.5, 1.5,
                     1.5, 1.5, 8.5, 10.6, 10.6, 10.6]),
    "dance": (_("Dance"), [6.1, 4.3, 4.3, 1.7, 1.7, 1.7, -0.1, -0.1, -0.1,
                           0.8, -10.7, -14.2, -15.1, -7.2, 0.0]),
    "pop": (_("Pop"), [-3.4, 1.7, 2.0, 3.0, 5.0, 5.6, 6.5, 5.2, 3.2, 1.5, 0.0,
                       -2.5, -4.8, -4.8, -3.2]),
    "techno": (_("Techno"), [5.0, 4.0, 3.9, 3.3, 0.0, -4.5, -10.0, -8.9, -8.1,
                             -5.5, -1.5, 3.0, 6.0, 6.1, 5.8]),
    "ska": (_("Ska"), [-4.5, -8.1, -8.9, -8.5, -8.0, -6.0, 0.0, 1.5, 2.5, 2.7,
                       3.2, 3.3, 5.8, 6.4, 6.4]),
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
        return map(float, config.get('plugins', 'equalizer_levels').split(','))
    except (config.Error, ValueError):
        return []


class Equalizer(EventPlugin):
    PLUGIN_ID = "Equalizer"
    PLUGIN_NAME = _("Equalizer")
    PLUGIN_DESC = _("Control the balance of your music with an equalizer.")
    PLUGIN_ICON = 'gtk-connect'
    PLUGIN_VERSION = '2.3'

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
        vb = gtk.VBox(spacing=6)
        if not self.player_has_eq:
            l = gtk.Label()
            l.set_markup('The current backend does not support equalization.')
            vb.pack_start(l, expand=False)
            return vb

        bands = [(band >= 1000 and ('%.1f kHz' % (band / 1000.))
                  or ('%d Hz' % band)) for band in app.player.eq_bands]
        levels = get_config() + [0.] * len(bands)

        table = gtk.Table(rows=len(bands), columns=3)
        table.set_col_spacings(6)

        def set_band(adj, idx):
            levels[idx] = adj.get_value()
            config.set('plugins', 'equalizer_levels',
                       ','.join(map(str, levels)))
            self.apply()

        adjustments = []

        for i, band in enumerate(bands):
            # align numbers and suffixes in separate rows for great justice
            lbl = gtk.Label(band.split()[0])
            lbl.set_alignment(1, 0.5)
            lbl.set_padding(0, 4)
            table.attach(lbl, 0, 1, i, i + 1, xoptions=gtk.FILL)
            lbl = gtk.Label(band.split()[1])
            lbl.set_alignment(1, 0.5)
            table.attach(lbl, 1, 2, i, i + 1, xoptions=gtk.FILL)
            adj = gtk.Adjustment(levels[i], -24., 12., 0.1)
            adj.connect('value-changed', set_band, i)
            adjustments.append(adj)
            hs = gtk.HScale(adj)
            hs.set_draw_value(True)
            hs.set_value_pos(gtk.POS_RIGHT)
            hs.connect('format-value', lambda s, v: '%.1f dB' % v)
            table.attach(hs, 2, 3, i, i + 1)
        vb.pack_start(table)

        def clicked_cb(button):
            [adj.set_value(0) for adj in adjustments]

        sorted_presets = sorted(PRESETS.iteritems())

        def combo_changed(combo):
            # custom, skip
            if not combo.get_active():
                return
            gain = sorted_presets[combo.get_active() - 1][1][1]
            gain = interp_bands(PRESET_BANDS, app.player.eq_bands, gain)
            for (g, a) in zip(gain, adjustments):
                a.set_value(g)

        combo = gtk.combo_box_new_text()
        combo.append_text(_("Custom"))
        combo.set_active(0)
        for key, (name, gain) in sorted_presets:
            combo.append_text(name)
        combo.connect("changed", combo_changed)

        bbox = gtk.HButtonBox()
        clear = gtk.Button(stock=gtk.STOCK_CLEAR)
        clear.connect('clicked', clicked_cb)
        bbox.pack_start(combo)
        bbox.pack_start(clear)
        vb.pack_start(bbox)
        return vb
