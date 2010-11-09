# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk

from quodlibet import util
from quodlibet import const
from quodlibet import config

from quodlibet.plugins.songsmenu import SongsMenuPlugin

class ResetLibrary(SongsMenuPlugin):
    PLUGIN_ID = "Reset Library Data"
    PLUGIN_NAME = _("Reset Library Data")
    PLUGIN_VERSION = "1"
    PLUGIN_DESC = "Reset ratings, play counts, skip counts, and play times."
    PLUGIN_ICON = 'gtk-refresh'

    def plugin_song(self, song):
        for key in ["~#playcount", "~#skipcount", "~#lastplayed",
                    "~#laststarted", "~#rating"]:
            if key in song:
                del song[key]

class ResetRating(SongsMenuPlugin):
    PLUGIN_ID = "Reset Rating"
    PLUGIN_NAME = _("Reset Rating")
    PLUGIN_VERSION = "1"
    PLUGIN_DESC = _("Reset to the default rating "
        "and change the global default rating.")
    PLUGIN_ICON = 'gtk-clear'

    def plugin_song(self, song):
        if "~#rating" in song:
            del song["~#rating"]

    @classmethod
    def PluginPreferences(klass, window):
        vb2 = gtk.VBox(spacing=3)
        hb = gtk.HBox(spacing=3)
        lab = gtk.Label(_("Default r_ating:"))
        lab.set_use_underline(True)
        hb.pack_start(lab, expand=False)

        def draw_rating(column, cell, model, it):
            i = model[it][0]
            text = "%0.2f\t%s" % (i, util.format_rating(i))
            cell.set_property('text', text)

        def default_rating_changed(combo, model):
            it = combo.get_active_iter()
            if it is None: return
            default_rating = model[it][0]
            config.set("settings", "default_rating", default_rating)
            const.DEFAULT_RATING = default_rating

        model = gtk.ListStore(float)
        combo = gtk.ComboBox(model)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        for i in range(0, int(1.0/util.RATING_PRECISION)+1):
            i *= util.RATING_PRECISION
            it = model.append(row=[i])
            if i == const.DEFAULT_RATING:
                combo.set_active_iter(it)
        combo.set_cell_data_func(cell, draw_rating)
        combo.connect('changed', default_rating_changed, model)
        hb.pack_start(combo, expand=False)
        lab.set_mnemonic_widget(combo)
        vb2.pack_start(hb)

        return vb2
