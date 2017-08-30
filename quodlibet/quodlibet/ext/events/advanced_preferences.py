# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#        2016-17 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import _
from quodlibet import config
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons
from quodlibet.util.string import decode
from quodlibet.util import gdecode
from quodlibet.plugins.events import EventPlugin
from quodlibet.compat import text_type


def _config(section, option, label, tooltip=None, getter=None):
    def on_changed(entry, *args):
        config.settext(section, option, gdecode(entry.get_text()))

    entry = UndoEntry()
    if tooltip:
        entry.set_tooltip_text(tooltip)
    entry.set_text(config.gettext(section, option))
    entry.connect("changed", on_changed)

    def on_reverted(*args):
        config.reset(section, option)
        entry.set_text(config.gettext(section, option))

    revert = Gtk.Button()
    revert.add(Gtk.Image.new_from_icon_name(
        Icons.DOCUMENT_REVERT, Gtk.IconSize.BUTTON))
    revert.connect("clicked", on_reverted)

    return (Gtk.Label(label=label), entry, revert)


def text_config(section, option, label, tooltip=None):

    def getter(section, option):
        return decode(config.get(section, option))

    return _config(section, option, label, tooltip, getter)


def boolean_config(section, option, label, tooltip):

    def getter(section, option):
        return text_type(config.getboolean(section, option))

    return _config(section, option, label, tooltip, getter)


def int_config(section, option, label, tooltip):

    def getter(section, option):
        return text_type(config.getint(section, option))

    return _config(section, option, label, tooltip, getter)


class AdvancedPreferences(EventPlugin):
    PLUGIN_ID = "Advanced Preferences"
    PLUGIN_NAME = _("Advanced Preferences")
    PLUGIN_DESC = _("Allow editing of advanced config settings.")
    PLUGIN_CAN_ENABLE = False
    PLUGIN_ICON = Icons.PREFERENCES_SYSTEM

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
                "ID3 encodings:",
                ("ID3 encodings separated by spaces. "
                 "UTF-8 is always tried first, and Latin-1 "
                 "is always tried last.")))

        rows.append(
            text_config(
                "settings", "search_tags",
                "Search tags:",
                ("Tags which get searched in addition to "
                 "the ones present in the song list. Separate with \",\"")))

        rows.append(
            text_config(
                "settings", "rating_symbol_full",
                "Rating symbol (full):"))

        rows.append(
            text_config(
                "settings", "rating_symbol_blank",
                "Rating symbol (blank):"))

        rows.append(
            text_config(
                "player", "backend",
                "Backend:",
                "Identifier of the playback backend to use"))

        rows.append(
            boolean_config(
                "settings", "disable_hints",
                "Disable hints:",
                "Disable popup windows (treeview hints)"))

        rows.append(
            int_config(
                "browsers", "cover_size",
                "Album cover size:",
                ("Size of the album cover images in the album list browser "
                 "(restart required)")))

        rows.append(
            boolean_config(
                "settings", "disable_mmkeys",
                "Disable multimedia keys:",
                "(restart required)"))

        rows.append(
            text_config(
                "settings", "window_title_pattern",
                "Main window title:",
                ("A (tied) tag for the main window title, e.g. ~title~~people "
                 "(restart required)")))

        for (row, (label, entry, button)) in enumerate(rows):
            label.set_alignment(1.0, 0.5)
            table.attach(label, 0, 1, row, row + 1,
                         xoptions=Gtk.AttachOptions.FILL)
            table.attach(entry, 1, 2, row, row + 1)
            table.attach(button, 2, 3, row, row + 1,
                         xoptions=Gtk.AttachOptions.SHRINK)

        def on_click(button):
            button.hide()
            table.set_no_show_all(False)
            table.show_all()

        button = Gtk.Button(label=_("I know what I'm doing"))
        button.connect("clicked", on_click)
        vb.pack_start(button, True, True, 0)
        vb.pack_start(table, True, True, 0)
        table.set_no_show_all(True)

        return vb
