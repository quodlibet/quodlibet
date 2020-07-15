# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import const
from quodlibet import util
from quodlibet import _


SHORTCUTS = [
    (_("Main Window"), [
        ("<Alt>Left", _("Seek backwards by 10 seconds")),
        ("<Alt>Right", _("Seek forward by 10 seconds")),
        ("<Primary>L", _("Focus the search entry")),
    ]),
    (_("Browsers"), [
        ("<Primary><Shift>J", _("Reset filters and jump to the playing song")),
    ]),
    (_("Song List"), [
        ("<Primary>I",
         _("Open the information window for the selected songs")),
        ("<Alt>Return", _("Open the tag editor for the selected songs")),
        ("<Primary>Return", _("Queue the selected songs")),
        ("<Primary>Delete", _("Delete the selected songs")),
        ("<Primary>F", _("Show the inline search entry")),
        ("<Ctrl>", "+ " + _("Left click on a column header") + ":\n"
         + _("Add the column to the list of columns to sort by")),
    ]),
    (_("Tree View"), [
        ("Left <Primary>Left",
         _("Collapses the element or select the parent element")),
        ("Right <Primary>Right", _("Expands the element")),
    ]),
    (_("Text Entries"), [
        ("<Primary>Z",
         _("Undo the last change")),
        ("<Primary><Shift>Z", _("Redo the last undone change")),
    ]),
    (_("Paned Browser"), [
        ("<Primary>Home", _("Select all songs in all panes")),
    ]),
]


def build_shortcut_window(data):
    """Returns a filled Gtk.ShortcutsWindow"""

    assert has_shortcut_window()

    # Note: gtk+ is picky about the order of adding/showing things because
    # this is usually done through XML. e.g. adding shortcuts after a section
    # won't make them show up in the search etc..
    w = Gtk.ShortcutsWindow()
    section = Gtk.ShortcutsSection()
    section.show()
    for group_title, shortcuts in data:
        group = Gtk.ShortcutsGroup(title=group_title)
        group.show()
        for accel, shortcut_title in shortcuts:
            short = Gtk.ShortcutsShortcut(
                title=shortcut_title, accelerator=accel)
            short.show()
            group.add(short)
        section.add(group)
    w.add(section)

    return w


def has_shortcut_window():
    """Returns if the current Gtk+ supports ShortcutsWindow. Gtk+ >= 3.20"""

    return hasattr(Gtk, "ShortcutsWindow")


def show_shortcuts(parent):
    """Either opens a window showing keyboard shortcuts or a website in the
    default browser, depending on the Gtk+ version
    """

    if has_shortcut_window():
        window = build_shortcut_window(SHORTCUTS)
        window.set_transient_for(parent)
        window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        window.set_modal(True)
        window.show()
        # XXX: The windows does some weird size changes on start which confuses
        # window placement. This fixes the jumping around and wrong position
        # with some WMs and under Windows.
        window.hide()
        window.unrealize()
        window.show()
    else:
        util.website(const.SHORTCUTS_HELP)
