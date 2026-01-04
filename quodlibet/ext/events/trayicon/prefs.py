# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#      2013,2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.util import is_windows
from quodlibet.qltk import Icons, get_children
from quodlibet.pattern import Pattern
from quodlibet.qltk.entry import UndoEntry
from .util import pconfig


def supports_scrolling():
    """If our tray icon implementation supports scrolling"""

    return not is_windows()


class Preferences(Gtk.Box):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.set_border_width(6)

        ccb = pconfig.ConfigCheckButton(
            _("Hide main window on close"), "window_hide", populate=True
        )
        self.prepend(qltk.Frame(_("Behavior"), child=ccb), False, True, 0)

        def on_scroll_changed(button, new_state):
            if button.get_active():
                pconfig.set("modifier_swap", new_state)

        modifier_swap = pconfig.getboolean("modifier_swap")

        scrollwheel_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        group = Gtk.CheckButton(
            group=None, label=_("Scroll wheel adjusts volume"), use_underline=True
        )
        group.connect("toggled", on_scroll_changed, False)
        group.set_active(not modifier_swap)
        scrollwheel_box.prepend(group)
        group = Gtk.CheckButton(
            group=group, label=_("Scroll wheel changes song"), use_underline=True
        )
        group.connect("toggled", on_scroll_changed, True)
        group.set_active(modifier_swap)
        scrollwheel_box.prepend(group)

        if supports_scrolling():
            self.prepend(
                qltk.Frame(_("Scroll _Wheel"), child=scrollwheel_box), True, True, 0
            )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        entry_box = Gtk.Box(spacing=6)

        entry = UndoEntry()
        entry_box.prepend(entry)

        def on_reverted(*args):
            pconfig.reset("tooltip")
            entry.set_text(pconfig.gettext("tooltip"))

        revert = Gtk.Button()
        revert.add(
            Gtk.Image.new_from_icon_name(Icons.DOCUMENT_REVERT, Gtk.IconSize.LARGE)
        )
        revert.connect("clicked", on_reverted)
        entry_box.prepend(revert)

        box.prepend(entry_box)

        preview = Gtk.Label()
        preview.set_line_wrap(True)
        preview_frame = Gtk.Frame(label=_("Preview"))
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=18)
        vbox.prepend(preview)
        preview_frame.add(vbox)
        box.prepend(preview_frame)

        tt_frame = qltk.Frame(_("Tooltip Display"), child=box)
        tt_frame.get_label_widget().set_mnemonic_widget(entry)
        self.prepend(tt_frame)

        entry.connect("changed", self.__changed_entry, preview, preview_frame)
        entry.set_text(pconfig.gettext("tooltip"))

        for child in get_children(self):
            child.show_all()

    def __changed_entry(self, entry, label, frame):
        text = entry.get_text()

        if app.player.info is None:
            text = _("Not playing")
        else:
            text = Pattern(text) % app.player.info

        label.set_text(text)
        frame.set_tooltip_text(text)
        pconfig.set("tooltip", entry.get_text())
