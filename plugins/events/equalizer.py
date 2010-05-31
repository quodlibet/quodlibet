# Copyright 2010 Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# TODO: Include presets, saving and loading.

import gtk

from quodlibet import config, player
from quodlibet.plugins.events import EventPlugin

def get_config():
    try:
        return map(float, config.get('plugins', 'equalizer_levels').split(','))
    except (config.error, ValueError):
        return []

class Equalizer(EventPlugin):
    PLUGIN_ID = "Equalizer"
    PLUGIN_NAME = _("Equalizer")
    PLUGIN_DESC = _("Control the balance of your music with an equalizer.")
    PLUGIN_ICON = 'gtk-connect'
    PLUGIN_VERSION = '2.3'

    @property
    def player_has_eq(self):
        return hasattr(player.device, 'eq_bands') and player.device.eq_bands

    def __init__(self):
        super(Equalizer, self).__init__()
        self._enabled = False

    def apply(self):
        if not self.player_has_eq:
            return
        levels = self._enabled and get_config() or []
        lbands = len(player.device.eq_bands)
        player.device.eq_values = (levels[:min(len(levels), lbands)] +
                                   [0.] * max(0, (lbands - len(levels))))

    def enabled(self):
        self._enabled = True
        self.apply()

    def disabled(self):
        self._enabled = False
        self.apply()

    def PluginPreferences(self, win):
        vb = gtk.VBox()
        if not self.player_has_eq:
            l = gtk.Label()
            l.set_markup('The current backend does not support equalization.')
            vb.pack_start(l, expand=False)
            return vb

        bands = [(band >= 1000 and ('%.1f kHz' % (band/1000.))
                  or ('%d Hz' % band)) for band in player.device.eq_bands]
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
            table.attach(lbl, 0, 1, i, i+1, xoptions=gtk.FILL)
            lbl = gtk.Label(band.split()[1])
            lbl.set_alignment(1, 0.5)
            table.attach(lbl, 1, 2, i, i+1, xoptions=gtk.FILL)
            adj = gtk.Adjustment(levels[i], -24., 12., 0.1)
            adj.connect('value-changed', set_band, i)
            adjustments.append(adj)
            hs = gtk.HScale(adj)
            hs.set_draw_value(True)
            hs.set_value_pos(gtk.POS_LEFT)
            hs.connect('format-value', lambda s, v: '%.1f dB' % v)
            table.attach(hs, 2, 3, i, i+1)
        vb.pack_start(table)

        def clicked_cb(button):
            [adj.set_value(0) for adj in adjustments]

        bbox = gtk.HButtonBox()
        clear = gtk.Button(stock=gtk.STOCK_CLEAR)
        clear.connect('clicked', clicked_cb)
        bbox.pack_start(clear)
        vb.pack_start(bbox)
        return vb

