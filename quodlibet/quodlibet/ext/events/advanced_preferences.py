# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import config
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons
from quodlibet.util.string import decode
from quodlibet.plugins.events import EventPlugin


def _config(section, option, label, tooltip, getter):
    def on_changed(entry, *args):
        config.set(section, option, entry.get_text())

    entry = UndoEntry()
    entry.set_tooltip_text(tooltip)
    entry.set_text(decode(config.get(section, option)))
    entry.connect("changed", on_changed)

    def on_reverted(*args):
        config.reset(section, option)
        entry.set_text(decode(config.get(section, option)))

    revert = Gtk.Button()
    revert.add(Gtk.Image.new_from_icon_name(
        Icons.DOCUMENT_REVERT, Gtk.IconSize.BUTTON))
    revert.connect("clicked", on_reverted)

    return (Gtk.Label(label=label), entry, revert)


def text_config(section, option, label, tooltip):

    def getter(section, option):
        return decode(config.get(section, option))

    return _config(section, option, label, tooltip, getter)


def boolean_config(section, option, label, tooltip):

    def getter(section, option):
        return unicode(config.getboolean(section, option))

    return _config(section, option, label, tooltip, getter)


def int_config(section, option, label, tooltip):

    def getter(section, option):
        return unicode(config.getint(section, option))

    return _config(section, option, label, tooltip, getter)


class AdvancedPreferences(EventPlugin):
    PLUGIN_ID = "Advanced Preferences"
    PLUGIN_NAME = _("Advanced Preferences")
    PLUGIN_DESC = _("Allow to tweak advanced config settings.")
    PLUGIN_CAN_ENABLE = False

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

        # We don't use translations as these things are internal and I don't
        # want to burden the translators...

        rows.append(
            text_config(
                "editing", "id3encoding",
                "ID3 Encodings:",
                ("ID3 encodings separated by spaces. "
                 "UTF-8 is always tried first, and Latin-1 "
                 "is always tried last.")))

        rows.append(
            text_config(
                "settings", "search_tags",
                "Search Tags:",
                ("Tags which get searched in addition to "
                 "the ones present in the song list, separate with \",\"")))

        rows.append(
            text_config(
                "settings", "rating_symbol_full",
                "Rating Symbol (Full):",
                ""))

        rows.append(
            text_config(
                "settings", "rating_symbol_blank",
                "Rating Symbol (Blank):",
                ""))

        rows.append(
            text_config(
                "player", "backend",
                "Backend:",
                "Identifier of the playback backend to use"))

        rows.append(
            boolean_config(
                "settings", "disable_hints",
                "Disable Hints:",
                "Disable popup windows (treeview hints)"))

        rows.append(
            boolean_config(
                "browsers", "rating_hotkeys",
                "Rating Hotkeys:",
                "Enable rating by pressing the 0-X keys"))

        rows.append(
            int_config(
                "browsers", "cover_size",
                "Album Cover Size:",
                ("Size of the album cover images in the album list browser "
                 "(restart required)")))

        rows.append(
            boolean_config(
                "settings", "osx_mmkeys",
                "OS X Multimedia Keys:",
                "Enable experimental mmkeys support (restart required)"))

        for (row, (label, entry, button)) in enumerate(rows):
            label.set_alignment(1.0, 0.5)
            table.attach(label, 0, 1, row, row + 1,
                         xoptions=Gtk.AttachOptions.FILL)
            table.attach(entry, 1, 2, row, row + 1)
            table.attach(button, 2, 3, row, row + 1,
                         xoptions=Gtk.AttachOptions.SHRINK)

        vb.pack_start(table, True, True, 0)

        return vb
