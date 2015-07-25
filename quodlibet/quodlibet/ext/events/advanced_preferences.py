# -*- coding: utf-8 -*-
# Copyright 2011,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import warnings
import os

from gi.repository import Gtk

from quodlibet import qltk
from quodlibet import config
from quodlibet import const
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.plugins.events import EventPlugin

# TODO : rating_symbol_blank, rating_symbol_full

class AdvancedPreferences(EventPlugin):
    PLUGIN_ID = "Advanced Preferences"
    PLUGIN_NAME = _("Advanced Preferences")
    PLUGIN_DESC = _("Allow to tweak advanced config settings.")

    def __init_defaults(self):
        self.__enabled = False

    def PluginPreferences(self, *args):
        def changed(entry, name, section="settings"):
            config.set(section, name, entry.get_text())

        vb = Gtk.VBox(spacing=12)

        # Tabulate all settings for neatness
        table = Gtk.Table(n_rows=6, n_columns=2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        rows = []

        ve = Gtk.Entry()
        ve.set_tooltip_text("ID3 encodings separated by spaces. "
            "UTF-8 is always tried first, and Latin-1 is always tried last.")
        ve.set_text(config.get("editing", "id3encoding"))
        ve.connect('changed', changed, 'id3encoding', 'editing')
        rows.append((Gtk.Label(label=_("ID3 encodings:")), ve))

        ve = Gtk.Entry()
        ve.set_tooltip_text("Tags which get searched in addition to "
            "the ones present in the song list, separate with \",\"")
        ve.set_text(config.get("settings", "search_tags"))
        ve.connect('changed', changed, 'search_tags', 'settings')
        rows.append((Gtk.Label(label=_("Search tags:")), ve))

        ve = Gtk.Entry()
        ve.set_text(config.get("settings", "rating_symbol_full",
                               "\xe2\x98\x85"))
        ve.connect('changed', changed, 'rating_symbol_full', 'settings')
        rows.append((Gtk.Label(label=_("Rating symbol full:")), ve))

        ve = Gtk.Entry()
        ve.set_text(config.get("settings", "rating_symbol_blank",
                               "\xe2\x98\x86"))
        ve.connect('changed', changed, 'rating_symbol_blank', 'settings')
        rows.append((Gtk.Label(label=_("Rating symbol blank:")), ve))

        ve = Gtk.Entry()
        ve.set_tooltip_text("Identifier of the playback backend to use")
        ve.set_text(config.get("player", "backend"))
        ve.connect('changed', changed, 'backend', 'player')
        rows.append((Gtk.Label(label=_("Backend:")), ve))

        for (row, (label, entry)) in enumerate(rows):
            label.set_alignment(0.0, 0.5)
            table.attach(label, 0, 1, row, row + 1,
                         xoptions=Gtk.AttachOptions.FILL)
            table.attach(entry, 1, 2, row, row + 1)

        vb.pack_start(table, True, True, 0)

        disable_hints = ConfigCheckButton(_("Disable hints"),
                 'settings', 'disable_hints', populate=True,
                 tooltip="Disable popup windows (treeview hints)")
        vb.pack_start(disable_hints, True, True, 0)

        return vb
